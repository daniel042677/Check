"""
設定對話框
允許使用者設定：
- 共用資料夾路徑
- PDF 子資料夾名稱
- 支票號碼正規表達式（進階）
- OCR 解析度（進階）
"""
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox,
    QSpinBox, QCheckBox, QFileDialog, QMessageBox,
    QTabWidget, QWidget, QDialogButtonBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SettingsDialog(QDialog):

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("設定")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tabs = QTabWidget()

        # ── 分頁 1：基本設定 ──
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setSpacing(12)

        # 共用資料夾
        folder_group = QGroupBox("共用資料夾設定")
        folder_form = QFormLayout(folder_group)

        shared_row = QHBoxLayout()
        self._txt_shared = QLineEdit()
        self._txt_shared.setPlaceholderText("例：Z:\\支票掃描  或  \\\\server\\share\\支票")
        shared_row.addWidget(self._txt_shared)
        btn_browse = QPushButton("瀏覽...")
        btn_browse.setFixedWidth(70)
        btn_browse.clicked.connect(self._browse_shared)
        shared_row.addWidget(btn_browse)
        folder_form.addRow("共用資料夾路徑：", shared_row)

        self._txt_pdf_sub = QLineEdit()
        self._txt_pdf_sub.setPlaceholderText("若 PDF 直接放在共用資料夾根目錄，留空即可")
        folder_form.addRow("PDF 子資料夾：", self._txt_pdf_sub)

        lbl_note = QLabel(
            "💡 索引檔案會自動儲存在共用資料夾的 index 子資料夾中\n"
            "   請確認 AD 網域帳號有該資料夾的讀寫權限"
        )
        lbl_note.setStyleSheet("color: #666; font-size: 9pt;")
        folder_form.addRow("", lbl_note)

        basic_layout.addWidget(folder_group)
        basic_layout.addStretch()
        tabs.addTab(basic_tab, "基本設定")

        # ── 分頁 2：進階設定 ──
        adv_tab = QWidget()
        adv_layout = QVBoxLayout(adv_tab)
        adv_layout.setSpacing(12)

        # 支票號碼格式
        pattern_group = QGroupBox("支票號碼格式（正規表達式）")
        pattern_layout = QVBoxLayout(pattern_group)

        self._txt_pattern = QLineEdit()
        self._txt_pattern.setFont(QFont("Consolas", 10))
        pattern_layout.addWidget(self._txt_pattern)

        lbl_pattern_note = QLabel(
            "預設格式：[A-Z]{1,3}\\d{5,9}\n"
            "  意義：1-3個大寫字母 + 5-9個數字\n"
            "  範例符合：HF1377789、AB123456、A12345678\n"
            "⚠ 修改此設定後，需要重新建立索引"
        )
        lbl_pattern_note.setStyleSheet("color: #666; font-size: 9pt;")
        pattern_layout.addWidget(lbl_pattern_note)

        btn_test_pattern = QPushButton("測試格式...")
        btn_test_pattern.clicked.connect(self._test_pattern)
        pattern_layout.addWidget(btn_test_pattern)

        adv_layout.addWidget(pattern_group)

        # OCR 設定
        ocr_group = QGroupBox("OCR 掃描設定")
        ocr_form = QFormLayout(ocr_group)

        self._spin_index_dpi = QSpinBox()
        self._spin_index_dpi.setRange(72, 300)
        self._spin_index_dpi.setSuffix(" DPI")
        self._spin_index_dpi.setToolTip("建立索引時的解析度。數值越低越快，但準確度降低。建議 150。")
        ocr_form.addRow("索引掃描解析度：", self._spin_index_dpi)

        self._spin_preview_dpi = QSpinBox()
        self._spin_preview_dpi.setRange(72, 300)
        self._spin_preview_dpi.setSuffix(" DPI")
        self._spin_preview_dpi.setToolTip("預覽時的解析度。建議 200。")
        ocr_form.addRow("預覽解析度：", self._spin_preview_dpi)

        self._spin_print_dpi = QSpinBox()
        self._spin_print_dpi.setRange(150, 600)
        self._spin_print_dpi.setSuffix(" DPI")
        self._spin_print_dpi.setToolTip("列印時的解析度。建議 300。")
        ocr_form.addRow("列印解析度：", self._spin_print_dpi)

        adv_layout.addWidget(ocr_group)
        adv_layout.addStretch()
        tabs.addTab(adv_tab, "進階設定")

        layout.addWidget(tabs)

        # 按鈕列
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("確定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_values(self):
        """從設定載入目前的值"""
        self._txt_shared.setText(
            str(self._config.shared_folder) if self._config.shared_folder else ''
        )
        self._txt_pdf_sub.setText(self._config.get('pdf_subfolder', ''))
        self._txt_pattern.setText(self._config.check_pattern)
        self._spin_index_dpi.setValue(self._config.index_dpi)
        self._spin_preview_dpi.setValue(self._config.preview_dpi)
        self._spin_print_dpi.setValue(self._config.print_dpi)

    def _browse_shared(self):
        """瀏覽選擇共用資料夾"""
        current = self._txt_shared.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "選擇共用資料夾", current,
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self._txt_shared.setText(folder)

    def _test_pattern(self):
        """測試正規表達式是否有效"""
        pattern = self._txt_pattern.text().strip()
        if not pattern:
            QMessageBox.warning(self, "測試", "請先輸入格式")
            return

        try:
            compiled = re.compile(pattern)
        except re.error as e:
            QMessageBox.critical(self, "格式錯誤", f"正規表達式有誤：\n{e}")
            return

        # 顯示測試對話框
        dialog = QDialog(self)
        dialog.setWindowTitle("測試支票號碼格式")
        dialog.setMinimumWidth(350)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("輸入測試號碼（每行一個）："))
        txt = QTextEdit()
        txt.setPlainText("HF1377789\nAB123456\nHF999\nabc\n12345678")
        txt.setFixedHeight(120)
        layout.addWidget(txt)

        result_label = QLabel()
        result_label.setWordWrap(True)
        layout.addWidget(result_label)

        def run_test():
            lines = txt.toPlainText().strip().splitlines()
            results = []
            for line in lines:
                line = line.strip()
                if line:
                    m = re.fullmatch(pattern, line, re.IGNORECASE)
                    symbol = "✅" if m else "❌"
                    results.append(f"{symbol}  {line}")
            result_label.setText('\n'.join(results))

        btn_test = QPushButton("執行測試")
        btn_test.clicked.connect(run_test)
        layout.addWidget(btn_test)

        btn_ok = QPushButton("關閉")
        btn_ok.clicked.connect(dialog.accept)
        layout.addWidget(btn_ok)

        run_test()
        dialog.exec()

    def _save_and_accept(self):
        """驗證並儲存設定"""
        shared = self._txt_shared.text().strip()
        if shared:
            p = Path(shared)
            if not p.exists():
                reply = QMessageBox.question(
                    self, "路徑不存在",
                    f"資料夾 {shared} 目前無法存取。\n（可能是網路磁碟機暫時斷線）\n仍要儲存此路徑嗎？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
        else:
            QMessageBox.warning(self, "必填欄位", "請設定共用資料夾路徑")
            return

        # 驗證正規表達式
        pattern = self._txt_pattern.text().strip()
        try:
            re.compile(pattern)
        except re.error as e:
            QMessageBox.critical(self, "格式錯誤", f"支票號碼格式有誤：\n{e}")
            return

        # 儲存所有設定
        self._config.set('shared_folder', shared)
        self._config.set('pdf_subfolder', self._txt_pdf_sub.text().strip())
        self._config.set('check_number_pattern', pattern)
        self._config.set('index_dpi', self._spin_index_dpi.value())
        self._config.set('preview_dpi', self._spin_preview_dpi.value())
        self._config.set('print_dpi', self._spin_print_dpi.value())

        self.accept()
