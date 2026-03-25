"""
列印模組
使用 PyQt6 的列印功能，提供預覽後列印

設計重點：
- 支援裁切半頁列印（一頁兩張的情況）
- 維持原始比例，避免拉伸變形
- 居中列印
"""
import logging
from typing import Optional

from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtGui import QPainter, QPixmap, QImage
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog, QPrintPreviewDialog

from PIL.Image import Image as PILImage

logger = logging.getLogger(__name__)


def pil_to_qimage(pil_img: PILImage) -> QImage:
    """PIL Image 轉 QImage"""
    # 確保是 RGB 格式
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')

    data = pil_img.tobytes('raw', 'RGB')
    qimg = QImage(
        data,
        pil_img.width,
        pil_img.height,
        pil_img.width * 3,
        QImage.Format.Format_RGB888
    )
    return qimg.copy()  # .copy() 確保資料不會被 GC


def pil_to_qpixmap(pil_img: PILImage) -> QPixmap:
    """PIL Image 轉 QPixmap"""
    return QPixmap.fromImage(pil_to_qimage(pil_img))


class PrintManager:
    """
    列印管理器
    
    使用方式：
        pm = PrintManager(parent_widget)
        pm.print_check(check_image)   # 顯示預覽對話框後列印
    """

    def __init__(self, parent: Optional[QWidget] = None):
        self._parent = parent
        self._current_pixmap: Optional[QPixmap] = None

    def print_check(self, pil_image: PILImage, check_number: str = '') -> bool:
        """
        顯示列印預覽，使用者確認後列印
        
        Args:
            pil_image: 支票圖片（已裁切）
            check_number: 支票號碼（顯示在標題）
        
        Returns:
            True 表示使用者確認列印
        """
        if pil_image is None:
            QMessageBox.warning(self._parent, "列印錯誤", "無法取得支票圖片")
            return False

        try:
            self._current_pixmap = pil_to_qpixmap(pil_image)
        except Exception as e:
            QMessageBox.critical(self._parent, "列印錯誤", f"圖片轉換失敗：{e}")
            return False

        # 設定印表機
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageOrientation(
            # 支票通常是橫式
            Qt.Orientation.Horizontal if pil_image.width > pil_image.height
            else Qt.Orientation.Vertical
        )

        # 顯示列印預覽對話框
        preview = QPrintPreviewDialog(printer, self._parent)
        preview.setWindowTitle(
            f"列印預覽 - 支票 {check_number}" if check_number else "列印預覽"
        )
        preview.paintRequested.connect(self._paint_page)
        preview.resize(800, 600)

        result = preview.exec()
        self._current_pixmap = None
        return result == 1  # 1 = Accepted (使用者按了列印)

    def _paint_page(self, printer: QPrinter):
        """
        繪製到印表機
        - 維持原始比例
        - 居中顯示
        - 最大化利用紙張空間
        """
        if self._current_pixmap is None:
            return

        painter = QPainter(printer)
        try:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            # 可用的列印區域
            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)

            # 計算等比例縮放（不超出頁面）
            pixmap_rect = self._current_pixmap.rect()
            scaled = pixmap_rect.scaled(
                int(page_rect.width()),
                int(page_rect.height()),
                Qt.AspectRatioMode.KeepAspectRatio
            )

            # 居中
            x = (page_rect.width() - scaled.width()) / 2
            y = (page_rect.height() - scaled.height()) / 2

            target_rect = QRectF(x, y, scaled.width(), scaled.height())
            painter.drawPixmap(target_rect, self._current_pixmap,
                               QRectF(self._current_pixmap.rect()))
        finally:
            painter.end()

    def get_available_printers(self) -> list:
        """取得系統中可用的印表機清單"""
        try:
            printers = QPrinterInfo.availablePrinters()
            return [p.printerName() for p in printers]
        except Exception:
            return []
