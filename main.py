"""
支票查詢系統 - 主程式進入點
"""
import sys
import os
import traceback
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    EXE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
    EXE_DIR = BASE_DIR

sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt


def is_dark_mode(app: QApplication) -> bool:
    palette = app.palette()
    bg = palette.color(QPalette.ColorRole.Window)
    return bg.lightness() < 128


def build_stylesheet(dark: bool) -> str:
    if dark:
        bg          = "#1e1e2e"
        bg_panel    = "#2a2a3d"
        bg_input    = "#2e2e42"
        bg_hover    = "#3a3a55"
        border      = "#44445a"
        text        = "#e0e0f0"
        text_sub    = "#9999bb"
        accent      = "#4e9eff"
        accent_dark = "#3a7fd4"
        success     = "#4caf6e"
        success_drk = "#3a9558"
        disabled_bg = "#3a3a4a"
        disabled_fg = "#666688"
        sel_bg      = "#2a4a7a"
        sel_fg      = "#80c4ff"
        status_bg   = "#181828"
        divider     = "#333348"
    else:
        bg          = "#f0f2f5"
        bg_panel    = "#ffffff"
        bg_input    = "#ffffff"
        bg_hover    = "#e8f4fd"
        border      = "#d0d0d8"
        text        = "#1a1a2e"
        text_sub    = "#555577"
        accent      = "#1890ff"
        accent_dark = "#096dd9"
        success     = "#52c41a"
        success_drk = "#389e0d"
        disabled_bg = "#f5f5f5"
        disabled_fg = "#aaaaaa"
        sel_bg      = "#e6f7ff"
        sel_fg      = "#1890ff"
        status_bg   = "#fafafa"
        divider     = "#e8e8e8"

    return f"""
        QMainWindow, QDialog, QWidget {{
            background-color: {bg};
            color: {text};
            font-family: "Microsoft JhengHei UI", "PingFang TC", sans-serif;
        }}
        QPushButton {{
            padding: 6px 14px;
            border-radius: 5px;
            border: 1px solid {border};
            background-color: {bg_panel};
            color: {text};
            font-size: 10pt;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
            border-color: {accent};
            color: {accent};
        }}
        QPushButton:pressed {{
            background-color: {sel_bg};
        }}
        QPushButton:disabled {{
            background-color: {disabled_bg};
            color: {disabled_fg};
            border-color: {border};
        }}
        QPushButton#btn_primary {{
            background-color: {accent};
            color: white;
            border-color: {accent};
            font-weight: bold;
        }}
        QPushButton#btn_primary:hover {{
            background-color: {accent_dark};
            border-color: {accent_dark};
            color: white;
        }}
        QPushButton#btn_print {{
            background-color: {success};
            color: white;
            border-color: {success};
            font-weight: bold;
            font-size: 11pt;
            padding: 8px 20px;
        }}
        QPushButton#btn_print:hover {{
            background-color: {success_drk};
            border-color: {success_drk};
            color: white;
        }}
        QPushButton#btn_print:disabled {{
            background-color: {disabled_bg};
            color: {disabled_fg};
            border-color: {border};
        }}
        QLineEdit {{
            padding: 6px 10px;
            border: 1px solid {border};
            border-radius: 5px;
            background-color: {bg_input};
            color: {text};
            font-size: 11pt;
        }}
        QLineEdit:focus {{
            border-color: {accent};
        }}
        QLineEdit:disabled {{
            background-color: {disabled_bg};
            color: {disabled_fg};
        }}
        QListWidget {{
            border: 1px solid {border};
            border-radius: 5px;
            background-color: {bg_panel};
            color: {text};
            font-size: 10pt;
            outline: none;
        }}
        QListWidget::item {{
            padding: 8px 6px;
            border-bottom: 1px solid {divider};
            color: {text};
        }}
        QListWidget::item:selected {{
            background-color: {sel_bg};
            color: {sel_fg};
        }}
        QListWidget::item:hover:!selected {{
            background-color: {bg_hover};
        }}
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {border};
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: {bg_panel};
            color: {text};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            color: {text};
            background-color: {bg_panel};
        }}
        QStatusBar {{
            background-color: {status_bg};
            border-top: 1px solid {divider};
            font-size: 9pt;
            color: {text_sub};
        }}
        QStatusBar QLabel {{
            color: {text_sub};
        }}
        QProgressBar {{
            border: 1px solid {border};
            border-radius: 5px;
            text-align: center;
            height: 20px;
            background-color: {bg_input};
            color: {text};
        }}
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 4px;
        }}
        QScrollBar:vertical {{
            background: {bg};
            width: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {border};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {bg};
            height: 10px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal {{
            background: {border};
            border-radius: 5px;
            min-width: 30px;
        }}
        QMenuBar {{
            background-color: {bg_panel};
            color: {text};
            border-bottom: 1px solid {divider};
        }}
        QMenuBar::item:selected {{
            background-color: {bg_hover};
            color: {accent};
        }}
        QMenu {{
            background-color: {bg_panel};
            color: {text};
            border: 1px solid {border};
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {sel_bg};
            color: {sel_fg};
        }}
        QMessageBox {{
            background-color: {bg_panel};
            color: {text};
        }}
        QMessageBox QLabel {{
            color: {text};
            background-color: transparent;
        }}
        QTabWidget::pane {{
            border: 1px solid {border};
            border-radius: 4px;
            background-color: {bg_panel};
        }}
        QTabBar::tab {{
            background-color: {bg};
            color: {text_sub};
            padding: 6px 16px;
            border: 1px solid {border};
            border-bottom: none;
            border-radius: 4px 4px 0 0;
        }}
        QTabBar::tab:selected {{
            background-color: {bg_panel};
            color: {text};
            font-weight: bold;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {bg_hover};
            color: {accent};
        }}
        QSpinBox {{
            background-color: {bg_input};
            color: {text};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QLabel {{
            color: {text};
            background-color: transparent;
        }}
        QFrame[frameShape="4"], QFrame[frameShape="5"] {{
            color: {divider};
        }}
        QScrollArea {{
            border: 1px solid {border};
            border-radius: 5px;
            background-color: {bg_panel};
        }}
    """


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("支票查詢系統")
    app.setApplicationVersion("1.5.0")
    app.setOrganizationName("Finance")

    font = QFont("Microsoft JhengHei UI", 10)
    app.setFont(font)

    dark = is_dark_mode(app)
    app.setStyleSheet(build_stylesheet(dark))

    try:
        from ui.main_window import MainWindow
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        err_detail = traceback.format_exc()
        QMessageBox.critical(
            None, "啟動錯誤",
            f"無法載入程式元件：\n{e}\n\n{err_detail}"
        )
        try:
            log_path = EXE_DIR / 'error.log'
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(err_detail)
        except Exception:
            pass
        sys.exit(1)


if __name__ == '__main__':
    main()
