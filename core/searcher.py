"""
搜尋模組
提供精確搜尋和模糊搜尋功能
"""
import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class SearchResult:
    def __init__(self, check_number: str, entry):
        self.check_number = check_number
        self.entry = entry

    @property
    def display_text(self) -> str:
        pos_map = {'full': '整頁', 'top': '上半頁', 'bottom': '下半頁'}
        pos_text = pos_map.get(self.entry.position, self.entry.position)
        return f"{self.check_number}  │  {self.entry.file}  │  第 {self.entry.page + 1} 頁 {pos_text}"

    @property
    def detail_text(self) -> str:
        pos_map = {'full': '整頁（一頁一張）', 'top': '上半頁（一頁兩張）', 'bottom': '下半頁（一頁兩張）'}
        pos_text = pos_map.get(self.entry.position, self.entry.position)
        return (
            f"支票號碼：{self.check_number}\n"
            f"來源檔案：{self.entry.file}\n"
            f"頁碼：第 {self.entry.page + 1} 頁\n"
            f"位置：{pos_text}\n"
            f"索引時間：{self.entry.indexed_at[:10] if self.entry.indexed_at else '不明'}"
        )

class Searcher:
    def __init__(self, indexer):
        self._indexer = indexer

    def search(self, query: str) -> List[SearchResult]:
        query = query.strip().upper()
        if not query: return []

        from config import get_config
        config = get_config()
        pattern = config.check_pattern

        try:
            full_match = re.fullmatch(pattern, query, re.IGNORECASE)
        except re.error:
            full_match = None

        if full_match:
            return self._exact_search(query)
        else:
            return self._fuzzy_search(query)

    def exact_search(self, check_number: str) -> List[SearchResult]:
        return self._exact_search(check_number.upper().strip())

    def fuzzy_search(self, query: str) -> List[SearchResult]:
        return self._fuzzy_search(query.upper().strip())

    def _exact_search(self, check_number: str) -> List[SearchResult]:
        entries = self._indexer.get_entries(check_number)
        return [SearchResult(check_number, e) for e in entries]

    def _fuzzy_search(self, query: str) -> List[SearchResult]:
        matches = self._indexer.search_fuzzy(query)
        results = []
        for check_num, entries in matches:
            for entry in entries:
                results.append(SearchResult(check_num, entry))
        return results