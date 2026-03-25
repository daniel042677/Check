"""
主視窗
整合所有功能的主要 UI 介面
"""
import logging
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QSplitter, QStatusBar, QMessageBox, QProgressDialog,
    QGroupBox, QScrollArea, QApplication, QFrame
)
from PyQt6.QtGui import QPixmap, QKeySequence, QAction, QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSlot

from config import get_config
from core.ocr_engine import OCREngine
from core.indexer import Indexer
from core.searcher import Searcher, SearchResult
from core.printer import PrintManager, pil_to_qpixmap
from ui.workers import IndexWorker
from ui.settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)

class PreviewWidget(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(400)
        self._lbl = QLabel("請在左側搜尋並選擇支票")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet("color: #bbb; font-size: 14pt;")
        self.setWidget(self._lbl)
        self.setWidgetResizable(True)
        self._original_pixmap = None

    def set_image(self, pixmap: QPixmap):
        self._original_pixmap = pixmap
        self._lbl.setStyleSheet("")
        self._update_display()

    def clear(self):
        self._original_pixmap = None
        self._lbl.setPixmap(QPixmap())
        self._lbl.setText("請在左側搜尋並選擇支票")
        self._lbl.setStyleSheet("color: #bbb; font-size: 14pt;")

    def _update_display(self):
        if self._original_pixmap is None: return
        available = self.viewport().size()
        scaled = self._original_pixmap.scaled(available, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._lbl.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._config = get_config()
        self._ocr = OCREngine()
        self._indexer = Indexer(self._config)
        self._searcher = Searcher(self._indexer)
        self._printer = PrintManager(self)
        self._worker = None
        self._current_results = []
        self._current_check_image = None

        self.setWindowTitle("支票查詢系統 v1.0")
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._build_menu()
        self._restore_geometry()
        QTimer.singleShot(100, self._on_startup)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([360, 600])

        self._statusbar = self.statusBar()
        self._lbl_status_checks = QLabel("索引尚未載入")
        self._statusbar.addWidget(self._lbl_status_checks)
        self._lbl_status_folder = QLabel("")
        self._statusbar.addWidget(self._lbl_status_folder, 1)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMaximumWidth(400)
        layout = QVBoxLayout(panel)
        
        search_group = QGroupBox("搜尋支票")
        search_layout = QVBoxLayout(search_group)
        search_row = QHBoxLayout()
        self._txt_search = QLineEdit()
        self._txt_search.returnPressed.connect(self._do_search)
        self._btn_search = QPushButton("搜尋")
        self._btn_search.clicked.connect(self._do_search)
        search_row.addWidget(self._txt_search)
        search_row.addWidget(self._btn_search)
        search_layout.addLayout(search_row)
        layout.addWidget(search_group)

        result_group = QGroupBox("搜尋結果")
        result_layout = QVBoxLayout(result_group)
        self._lbl_result_count = QLabel("尚未搜尋")
        result_layout.addWidget(self._lbl_result_count)
        self._list_results = QListWidget()
        self._list_results.itemSelectionChanged.connect(self._on_result_selected)
        result_layout.addWidget(self._list_results)
        layout.addWidget(result_group)

        btn_layout = QHBoxLayout()
        self._btn_print = QPushButton("🖨 列印支票")
        self._btn_print.setEnabled(False)
        self._btn_print.clicked.connect(self._do_print)
        btn_layout.addWidget(self._btn_print)
        layout.addLayout(btn_layout)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self._lbl_check_number = QLabel("")
        layout.addWidget(self._lbl_check_number)
        self._preview = PreviewWidget()
        layout.addWidget(self._preview, 1)
        return panel

    def _build_menu(self):
        menubar = self.menuBar()
        menu_file = menubar.addMenu("功能(&F)")
        act_rebuild = QAction("🔄 重建全量索引", self)
        act_rebuild.triggered.connect(lambda: self._start_indexing('full'))
        menu_file.addAction(act_rebuild)
        act_settings = QAction("⚙ 設定", self)
        act_settings.triggered.connect(self._open_settings)
        menu_file.addAction(act_settings)

    def _restore_geometry(self):
        geo = self._config.get('window_geometry')
        if geo:
            try:
                from PyQt6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromHex(geo.encode()))
            except: pass

    def _on_startup(self):
        if not self._config.shared_folder:
            self._open_settings()
        self._indexer.load()
        self._update_status()

    def _start_indexing(self, mode):
        if not self._config.shared_folder: return
        self._progress_dialog = QProgressDialog("處理中...", "取消", 0, 100, self)
        self._progress_dialog.show()
        self._worker = IndexWorker(self._indexer, self._ocr, self._config, mode)
        self._worker.progress.connect(lambda c, t, m: self._progress_dialog.setValue(int(c/t*100) if t else 0))
        self._worker.finished.connect(self._on_index_finished)
        self._worker.start()

    def _on_index_finished(self, new_checks, pdf_count, errors):
        self._progress_dialog.close()
        self._update_status()
        QMessageBox.information(self, "完成", f"掃描完畢。新增 {new_checks} 筆支票。")

    def _do_search(self):
        query = self._txt_search.text()
        self._current_results = self._searcher.search(query)
        self._list_results.clear()
        self._lbl_result_count.setText(f"找到 {len(self._current_results)} 筆")
        for i, res in enumerate(self._current_results):
            item = QListWidgetItem(f"{res.check_number} - {res.entry.file}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self._list_results.addItem(item)

    def _on_result_selected(self):
        items = self._list_results.selectedItems()
        if not items: return
        idx = items[0].data(Qt.ItemDataRole.UserRole)
        result = self._current_results[idx]
        self._lbl_check_number.setText(result.check_number)
        img = self._indexer.render_check_image(result.entry, 200)
        if img:
            self._current_check_image = img
            self._preview.set_image(pil_to_qpixmap(img))
            self._btn_print.setEnabled(True)

    def _do_print(self):
        if self._current_check_image:
            self._printer.print_check(self._current_check_image, self._lbl_check_number.text())

    def _open_settings(self):
        SettingsDialog(self._config, self).exec()
        self._update_status()

    def _update_status(self):
        self._lbl_status_checks.setText(f"已索引 {self._indexer.total_checks} 張支票")
        self._lbl_status_folder.setText(str(self._config.shared_folder))

    def closeEvent(self, event):
        self._config.set('window_geometry', self.saveGeometry().toHex().data().decode())
        event.accept()