"""
索引管理模組
負責掃描 PDF、建立支票號碼索引、快取管理
"""
import json
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

INDEX_FORMAT_VERSION = "1.1"
MAX_CHECKS_PER_PAGE = 2

class CheckEntry:
    __slots__ = ['file', 'page', 'position', 'raw_ocr', 'indexed_at']

    def __init__(self, file: str, page: int, position: str,
                 raw_ocr: str = '', indexed_at: str = ''):
        self.file = file
        self.page = page
        self.position = position
        self.raw_ocr = raw_ocr
        self.indexed_at = indexed_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            'file': self.file,
            'page': self.page,
            'position': self.position,
            'raw_ocr': self.raw_ocr,
            'indexed_at': self.indexed_at,
        }

    @staticmethod
    def from_dict(d: dict) -> 'CheckEntry':
        return CheckEntry(
            file=d['file'],
            page=d['page'],
            position=d['position'],
            raw_ocr=d.get('raw_ocr', ''),
            indexed_at=d.get('indexed_at', ''),
        )

class Indexer:
    def __init__(self, config):
        from config import Config
        self._config = config
        self._master: Dict[str, List[CheckEntry]] = {}
        self._pdf_meta: Dict[str, dict] = {}
        self._unrecognized: Dict[str, List[int]] = {}

    def load(self) -> int:
        index_dir = self._config.index_dir
        if not index_dir:
            return 0
        master_file = index_dir / 'master_index.json'
        if not master_file.exists():
            return 0
        try:
            with open(master_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._master = {}
            for check_num, entries_data in data.get('entries', {}).items():
                if isinstance(entries_data, list):
                    self._master[check_num] = [CheckEntry.from_dict(e) for e in entries_data]
                else:
                    self._master[check_num] = [CheckEntry.from_dict(entries_data)]
            self._pdf_meta = data.get('pdf_meta', {})
            self._unrecognized = data.get('unrecognized', {})
            return len(self._master)
        except Exception as e:
            logger.error(f"載入索引失敗: {e}")
            self._master = {}
            return 0

    def save(self):
        index_dir = self._config.index_dir
        if not index_dir:
            return False
        try:
            index_dir.mkdir(parents=True, exist_ok=True)
            data = {
                'version': INDEX_FORMAT_VERSION,
                'created_at': datetime.now().isoformat(),
                'total_checks': len(self._master),
                'entries': {
                    k: [e.to_dict() for e in v]
                    for k, v in self._master.items()
                },
                'pdf_meta': self._pdf_meta,
                'unrecognized': self._unrecognized,
            }
            master_file = index_dir / 'master_index.json'
            tmp_file = master_file.with_suffix('.tmp')
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_file.replace(master_file)
            return True
        except Exception as e:
            logger.error(f"儲存索引失敗: {e}")
            return False

    def get_pdf_list(self) -> List[Path]:
        pdf_dir = self._config.pdf_dir
        if not pdf_dir or not pdf_dir.exists():
            return []
        return sorted(pdf_dir.glob('*.pdf'))

    def get_new_pdfs(self) -> List[Path]:
        all_pdfs = self.get_pdf_list()
        new_pdfs = []
        for pdf_path in all_pdfs:
            name = pdf_path.name
            mtime = pdf_path.stat().st_mtime
            if name not in self._pdf_meta or self._pdf_meta[name].get('mtime', 0) != mtime:
                new_pdfs.append(pdf_path)
        return new_pdfs

    def build_all(self, ocr_engine, progress_callback=None, cancel_flag=None):
        pdf_list = self.get_pdf_list()
        if not pdf_list:
            return 0, 0, ["沒有找到 PDF"]
        new_check_count, errors = 0, []
        total = len(pdf_list)
        for i, pdf_path in enumerate(pdf_list):
            if cancel_flag and cancel_flag[0]:
                break
            if progress_callback:
                progress_callback(i, total, f"掃描：{pdf_path.name}")
            try:
                count = self._index_pdf(pdf_path, ocr_engine, progress_callback, cancel_flag, i, total)
                new_check_count += count
            except Exception as e:
                errors.append(f"{pdf_path.name}: {e}")
        if not (cancel_flag and cancel_flag[0]):
            self.save()
        return new_check_count, total, errors

    def build_incremental(self, ocr_engine, progress_callback=None, cancel_flag=None):
        new_pdfs = self.get_new_pdfs()
        if not new_pdfs:
            return 0, 0, []
        new_check_count, errors = 0, []
        total = len(new_pdfs)
        for i, pdf_path in enumerate(new_pdfs):
            if cancel_flag and cancel_flag[0]:
                break
            if progress_callback:
                progress_callback(i, total, f"掃描：{pdf_path.name}")
            try:
                self._remove_pdf_from_index(pdf_path.name)
                count = self._index_pdf(pdf_path, ocr_engine, progress_callback, cancel_flag, i, total)
                new_check_count += count
            except Exception as e:
                errors.append(f"{pdf_path.name}: {e}")
        if not (cancel_flag and cancel_flag[0]):
            self.save()
        return new_check_count, total, errors

    def get_entries(self, check_number: str) -> List[CheckEntry]:
        return self._master.get(check_number.upper().strip(), [])

    def search_fuzzy(self, query: str) -> List[Tuple[str, List[CheckEntry]]]:
        query = query.upper().strip()
        if not query:
            return []
        results = [(k, v) for k, v in self._master.items() if query in k]
        results.sort(key=lambda x: x[0])
        return results

    @property
    def total_checks(self) -> int: return len(self._master)
    @property
    def indexed_pdf_count(self) -> int: return len(self._pdf_meta)

    def get_stats(self) -> dict:
        return {
            'total_checks': len(self._master),
            'total_pdfs': len(self._pdf_meta),
            'unrecognized_pages': sum(len(v) for v in self._unrecognized.values()),
            'pdf_list': list(self._pdf_meta.keys()),
        }

    def _index_pdf(self, pdf_path: Path, ocr_engine, progress_callback, cancel_flag, base_i: int, base_total: int) -> int:
        count = 0
        pdf_name = pdf_path.name
        unrecognized_pages = []
        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise RuntimeError(f"無法開啟 PDF: {e}")
        try:
            total_pages = doc.page_count
            mtime = pdf_path.stat().st_mtime
            for page_idx in range(total_pages):
                if cancel_flag and cancel_flag[0]: return count
                if progress_callback and page_idx % 10 == 0:
                    progress_callback(base_i, base_total, f"掃描 {pdf_name} 第 {page_idx+1}/{total_pages} 頁...")
                
                page_image = self._render_page(doc, page_idx, self._config.index_dpi)
                if page_image is None:
                    unrecognized_pages.append(page_idx)
                    continue

                top_number = ocr_engine.extract_from_array(page_image, pattern=self._config.check_pattern, region=self._config.get('ocr_region_top'))
                bottom_number = ocr_engine.extract_from_array(page_image, pattern=self._config.check_pattern, region=self._config.get('ocr_region_bottom'))

                found_any = False
                if top_number:
                    pos = 'top' if bottom_number else 'full'
                    self._add_entry(top_number, CheckEntry(pdf_name, page_idx, pos, top_number))
                    count += 1
                    found_any = True
                if bottom_number and bottom_number != top_number:
                    self._add_entry(bottom_number, CheckEntry(pdf_name, page_idx, 'bottom', bottom_number))
                    count += 1
                    found_any = True
                if not found_any:
                    unrecognized_pages.append(page_idx)

            self._pdf_meta[pdf_name] = {'mtime': mtime, 'page_count': total_pages, 'indexed_at': datetime.now().isoformat(), 'check_count': count}
            self._unrecognized[pdf_name] = unrecognized_pages
        finally:
            doc.close()
        return count

    def _render_page(self, doc: fitz.Document, page_idx: int, dpi: int) -> Optional[np.ndarray]:
        try:
            page = doc[page_idx]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            return img_array
        except Exception:
            return None

    def render_check_image(self, entry: CheckEntry, dpi: int = 200) -> Optional[Image.Image]:
        pdf_dir = self._config.pdf_dir
        if not pdf_dir: return None
        pdf_path = pdf_dir / entry.file
        if not pdf_path.exists(): return None
        try:
            doc = fitz.open(str(pdf_path))
            try:
                if entry.page >= doc.page_count: return None
                page = doc[entry.page]
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
                return self._crop_by_position(img, entry.position)
            finally:
                doc.close()
        except Exception:
            return None

    def _crop_by_position(self, img: Image.Image, position: str) -> Image.Image:
        w, h = img.size
        if position == 'top': return img.crop((0, 0, w, h // 2))
        elif position == 'bottom': return img.crop((0, h // 2, w, h))
        return img

    def _add_entry(self, check_number: str, entry: CheckEntry):
        key = check_number.upper()
        if key not in self._master: self._master[key] = []
        existing = self._master[key]
        for i, e in enumerate(existing):
            if e.file == entry.file and e.page == entry.page and e.position == entry.position:
                existing[i] = entry
                return
        existing.append(entry)

    def _remove_pdf_from_index(self, pdf_name: str):
        keys_to_remove = []
        for check_num, entries in self._master.items():
            self._master[check_num] = [e for e in entries if e.file != pdf_name]
            if not self._master[check_num]: keys_to_remove.append(check_num)
        for key in keys_to_remove: del self._master[key]
        self._pdf_meta.pop(pdf_name, None)
        self._unrecognized.pop(pdf_name, None)