"""
背景工作執行緒
將耗時的 OCR 索引建立放到背景，避免 UI 凍結

Worker 設計原則：
- 使用 Qt Signal 回傳進度
- 支援中途取消
- 完成後 emit 結果
"""
import logging
from PyQt6.QtCore import QThread, pyqtSignal, QObject

logger = logging.getLogger(__name__)


class IndexWorker(QThread):
    """
    背景索引建立執行緒
    
    Signals:
        progress(current, total, message)  進度更新
        finished(new_checks, pdf_count, errors)  完成
        ocr_ready()  OCR 引擎初始化完成
        ocr_failed(error_message)  OCR 引擎初始化失敗
    """

    progress = pyqtSignal(int, int, str)   # current, total, message
    finished = pyqtSignal(int, int, list)  # new_checks, pdf_count, errors
    ocr_ready = pyqtSignal()
    ocr_failed = pyqtSignal(str)

    def __init__(self, indexer, ocr_engine, config, mode='incremental'):
        super().__init__()
        self._indexer = indexer
        self._ocr = ocr_engine
        self._config = config
        self._mode = mode  # 'full' 或 'incremental'
        self._cancel_flag = [False]

    def run(self):
        """在背景執行緒中執行"""
        try:
            # 1. 初始化 OCR 引擎（若尚未初始化）
            if not self._ocr.is_ready:
                self.progress.emit(0, 1, "正在初始化 OCR 引擎，請稍候...")

                def ocr_progress(msg):
                    self.progress.emit(0, 1, msg)

                success = self._ocr.initialize(
                    languages=self._config.get('ocr_language', ['en']),
                    gpu=self._config.get('ocr_gpu', False),
                    progress_callback=ocr_progress
                )

                if not success:
                    error_msg = self._ocr.error_message or "OCR 引擎初始化失敗"
                    self.ocr_failed.emit(error_msg)
                    return

            self.ocr_ready.emit()

            # 2. 執行索引建立
            if self._mode == 'full':
                new_checks, pdf_count, errors = self._indexer.build_all(
                    self._ocr,
                    progress_callback=self._on_progress,
                    cancel_flag=self._cancel_flag
                )
            else:
                new_checks, pdf_count, errors = self._indexer.build_incremental(
                    self._ocr,
                    progress_callback=self._on_progress,
                    cancel_flag=self._cancel_flag
                )

            self.finished.emit(new_checks, pdf_count, errors)

        except Exception as e:
            logger.exception("索引建立過程發生未預期錯誤")
            self.finished.emit(0, 0, [f"系統錯誤：{e}"])

    def _on_progress(self, current: int, total: int, message: str):
        """進度回呼（從背景執行緒呼叫）"""
        if not self._cancel_flag[0]:
            self.progress.emit(current, total, message)

    def cancel(self):
        """請求取消（設定旗標，不強制終止）"""
        self._cancel_flag[0] = True
        logger.info("索引建立已請求取消")
