"""
設定管理模組
儲存於 %APPDATA%/CheckFinder/config.json（每台電腦各自設定）
"""
import json
import os
from pathlib import Path
from typing import Any, Optional

APP_NAME = "CheckFinder"
CONFIG_DIR = Path(os.environ.get('APPDATA', Path.home())) / APP_NAME
CONFIG_FILE = CONFIG_DIR / 'config.json'

# 預設設定值
DEFAULT_CONFIG = {
    'version': '1.0',

    # 共用資料夾路徑（每台電腦可能不同，例如映射磁碟代號不同）
    'shared_folder': '',

    # PDF 檔案放置的子資料夾名稱（相對於 shared_folder）
    'pdf_subfolder': '',  # 空字串表示直接放在 shared_folder 下

    # OCR 辨識區域（以頁面比例 0.0~1.0 表示）
    # 針對「上半張支票」的號碼區域（右上角）
    'ocr_region_top': {
        'y1': 0.00, 'x1': 0.50,
        'y2': 0.28, 'x2': 1.00
    },
    # 針對「下半張支票」（一頁兩張時，下半頁）的號碼區域
    'ocr_region_bottom': {
        'y1': 0.50, 'x1': 0.50,
        'y2': 0.78, 'x2': 1.00
    },

    # 支票號碼的正規表達式（預設：1-3個字母 + 5-9個數字）
    # 未來可在設定介面修改以支援不同格式
    'check_number_pattern': r'[A-Z]{1,3}\d{5,9}',

    # OCR 圖片解析度（DPI）
    'index_dpi': 150,     # 建立索引用（速度優先）
    'preview_dpi': 200,   # 預覽用
    'print_dpi': 300,     # 列印用（品質優先）

    # 搜尋設定
    'search_history': [],  # 最近搜尋紀錄（最多20筆）
    'max_history': 20,

    # 列印設定
    'default_printer': '',  # 空白表示使用系統預設印表機

    # UI 設定
    'window_geometry': None,
    'splitter_sizes': None,
    'last_tab': 0,

    # OCR 引擎設定
    'ocr_language': ['en'],
    'ocr_gpu': False,  # 財會電腦通常沒有 GPU
}


class Config:
    """
    設定管理類別
    自動處理讀取、儲存、預設值
    """

    def __init__(self):
        self._data: dict = {}
        self._load()

    def _load(self):
        """從磁碟讀取設定，失敗時使用預設值"""
        self._data = DEFAULT_CONFIG.copy()
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    # 深度合併（保留新版本增加的預設值）
                    self._deep_update(self._data, saved)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Config] 讀取設定失敗，使用預設值: {e}")

    def _deep_update(self, base: dict, update: dict):
        """遞迴更新字典，保留 base 中 update 沒有的鍵"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value

    def save(self):
        """儲存設定到磁碟"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[Config] 儲存設定失敗: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    # ─── 常用屬性的快捷方式 ─────────────────────────────

    @property
    def shared_folder(self) -> Optional[Path]:
        p = self._data.get('shared_folder', '')
        return Path(p) if p else None

    @shared_folder.setter
    def shared_folder(self, value):
        self._data['shared_folder'] = str(value) if value else ''
        self.save()

    @property
    def pdf_dir(self) -> Optional[Path]:
        """PDF 實際存放路徑"""
        if not self.shared_folder:
            return None
        sub = self._data.get('pdf_subfolder', '').strip()
        return self.shared_folder / sub if sub else self.shared_folder

    @property
    def index_dir(self) -> Optional[Path]:
        """索引檔案存放路徑"""
        if not self.shared_folder:
            return None
        return self.shared_folder / 'index'

    @property
    def check_pattern(self) -> str:
        return self._data.get('check_number_pattern', r'[A-Z]{1,3}\d{5,9}')

    @property
    def index_dpi(self) -> int:
        return int(self._data.get('index_dpi', 150))

    @property
    def preview_dpi(self) -> int:
        return int(self._data.get('preview_dpi', 200))

    @property
    def print_dpi(self) -> int:
        return int(self._data.get('print_dpi', 300))

    def add_search_history(self, query: str):
        """新增搜尋紀錄"""
        history = self._data.get('search_history', [])
        # 移除重複
        if query in history:
            history.remove(query)
        history.insert(0, query)
        # 只保留最近 N 筆
        max_n = self._data.get('max_history', 20)
        self._data['search_history'] = history[:max_n]
        self.save()

    @property
    def search_history(self) -> list:
        return self._data.get('search_history', [])


# 全域設定實例（singleton）
_config_instance = None


def get_config() -> Config:
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
