"""
OCR 引擎模組
優先使用 Windows 內建 OCR（不需要任何額外 DLL，支援所有 Python 版本）
備用：RapidOCR
"""
import re
import logging
import threading
from typing import Optional, List

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


class OCREngine:

    def __init__(self):
        self._engine = None
        self._engine_type = None
        self._initialized = False
        self._init_error: Optional[str] = None
        self._init_lock = threading.Lock()

    def initialize(self, languages: List[str] = None, gpu: bool = False,
                   progress_callback=None) -> bool:
        if self._initialized:
            return True

        with self._init_lock:
            if self._initialized:
                return True

            if progress_callback:
                progress_callback("正在初始化 OCR 引擎...")

            # 嘗試順序：Windows OCR → RapidOCR → Tesseract
            if self._try_windows_ocr(progress_callback):
                return True
            if self._try_rapidocr(progress_callback):
                return True
            if self._try_tesseract(progress_callback):
                return True

            self._init_error = (
                "無法初始化任何 OCR 引擎。\n"
                "請執行以下其中一個：\n"
                "  pip install winocr\n"
                "  pip install rapidocr-onnxruntime==1.2.3\n"
                "  安裝 Tesseract：https://github.com/UB-Mannheim/tesseract/wiki"
            )
            return False

    # ── Windows 內建 OCR（最優先，Python 3.14 完全相容）──────────

    def _try_windows_ocr(self, progress_callback=None) -> bool:
        """使用 Windows 內建 OCR API（winocr 套件）"""
        try:
            import winocr
            # 測試是否可用
            import asyncio
            import platform
            if platform.system() != 'Windows':
                return False

            self._engine = winocr
            self._engine_type = 'windows_ocr'
            self._initialized = True
            logger.info("Windows OCR 初始化成功")
            if progress_callback:
                progress_callback("OCR 引擎初始化完成（Windows 內建 OCR）")
            return True
        except ImportError:
            logger.info("winocr 未安裝，嘗試其他引擎")
            return False
        except Exception as e:
            logger.warning(f"Windows OCR 初始化失敗: {e}")
            return False

    # ── RapidOCR ──────────────────────────────────────────────────

    def _try_rapidocr(self, progress_callback=None) -> bool:
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            self._engine_type = 'rapidocr'
            self._initialized = True
            logger.info("RapidOCR 初始化成功")
            if progress_callback:
                progress_callback("OCR 引擎初始化完成（RapidOCR）")
            return True
        except ImportError:
            logger.info("RapidOCR 未安裝")
            return False
        except Exception as e:
            logger.warning(f"RapidOCR 初始化失敗: {e}")
            return False

    # ── Tesseract（最後備用）─────────────────────────────────────

    def _try_tesseract(self, progress_callback=None) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._engine = pytesseract
            self._engine_type = 'tesseract'
            self._initialized = True
            logger.info("Tesseract OCR 初始化成功")
            if progress_callback:
                progress_callback("OCR 引擎初始化完成（Tesseract）")
            return True
        except Exception:
            return False

    # ── 公開方法 ──────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._initialized and self._engine is not None

    @property
    def error_message(self) -> Optional[str]:
        return self._init_error

    def extract_check_number(self, image: Image.Image,
                              pattern: str = r'[A-Z]{1,3}\d{5,9}',
                              region: Optional[dict] = None) -> Optional[str]:
        if not self.is_ready:
            return None
        try:
            if region:
                image = self._crop_region(image, region)
            processed = self._preprocess(image)

            if self._engine_type == 'windows_ocr':
                return self._ocr_windows(processed, pattern)
            elif self._engine_type == 'rapidocr':
                return self._ocr_rapidocr(np.array(processed), pattern)
            elif self._engine_type == 'tesseract':
                return self._ocr_tesseract(processed, pattern)
        except Exception as e:
            logger.error(f"OCR 辨識失敗: {e}")
        return None

    def extract_from_array(self, image_array: np.ndarray,
                           pattern: str = r'[A-Z]{1,3}\d{5,9}',
                           region: Optional[dict] = None) -> Optional[str]:
        img = Image.fromarray(image_array)
        return self.extract_check_number(img, pattern, region)

    # ── 各引擎辨識實作 ────────────────────────────────────────────

    def _ocr_windows(self, image: Image.Image, pattern: str) -> Optional[str]:
        """Windows 內建 OCR"""
        import asyncio
        import io

        async def _recognize():
            import winocr
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            buf.seek(0)
            result = await winocr.recognize_pil(image, 'en')
            return result

        try:
            # 取得或建立 event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(_recognize())
            if not result or not result.text:
                return None

            text = result.text.replace('\n', ' ').replace('\r', ' ')
            return self._find_in_text(text, pattern)
        except Exception as e:
            logger.error(f"Windows OCR 辨識失敗: {e}")
            return None

    def _ocr_rapidocr(self, arr: np.ndarray, pattern: str) -> Optional[str]:
        result, _ = self._engine(arr)
        if not result:
            return None
        all_text = ''
        candidates = []
        compiled = re.compile(pattern, re.IGNORECASE)
        for item in result:
            text = str(item[1]) if len(item) >= 2 else ''
            score = float(item[2]) if len(item) >= 3 else 0.9
            if score < 0.3:
                continue
            normalized = self._normalize_text(text)
            all_text += normalized
            m = compiled.search(normalized)
            if m:
                candidates.append((m.group(), score))
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0].upper()
        return self._find_in_text(all_text, pattern)

    def _ocr_tesseract(self, image: Image.Image, pattern: str) -> Optional[str]:
        config = '--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = self._engine.image_to_string(image, config=config)
        return self._find_in_text(text, pattern)

    # ── 共用工具 ──────────────────────────────────────────────────

    def _find_in_text(self, text: str, pattern: str) -> Optional[str]:
        normalized = self._normalize_text(text)
        m = re.search(pattern, normalized, re.IGNORECASE)
        return m.group().upper() if m else None

    def _crop_region(self, image: Image.Image, region: dict) -> Image.Image:
        w, h = image.size
        x1 = max(0, int(region['x1'] * w))
        y1 = max(0, int(region['y1'] * h))
        x2 = min(w, int(region['x2'] * w))
        y2 = min(h, int(region['y2'] * h))
        if x2 <= x1 or y2 <= y1:
            return image
        return image.crop((x1, y1, x2, y2))

    def _preprocess(self, image: Image.Image) -> Image.Image:
        img = image.convert('L')
        w, h = img.size
        if w < 200 or h < 200:
            scale = max(200 / w, 200 / h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)
        return img.convert('RGB')

    def _normalize_text(self, text: str) -> str:
        text = text.strip().upper().replace(' ', '').replace('\n', '')
        if not text:
            return text
        digit_replacements = {
            'O': '0', 'I': '1', 'L': '1',
            'S': '5', 'B': '8', 'Z': '2',
            'G': '6', 'T': '7',
        }
        first_digit = next((i for i, c in enumerate(text) if c.isdigit()), -1)
        if first_digit == -1:
            return text
        return text[:first_digit] + ''.join(
            digit_replacements.get(c, c) for c in text[first_digit:]
        )
