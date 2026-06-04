"""
Phos Desktop App

What:
    提供原生桌面 GUI，取代 Streamlit。

Why:
    使用 Qt 能把 GUI runtime 納入 Python 依賴管理，避免系統缺少 `tkinter` 時無法交付。
"""

from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path
from typing import Any, Optional

import cv2
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from Phos import process_image
from film_models import FILM_PROFILES, PhysicsMode


class ImagePreviewLabel(QLabel):
    """
    What:
        可縮放的影像預覽元件。

    Why:
        桌面版需要在不同視窗尺寸下保持預覽可讀，而不是固定像素布局。
    """

    def __init__(self, title: str):
        super().__init__(title)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 預覽圖只應填滿可用空間，不應反向決定整個視窗大小。
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setStyleSheet(
            """
            QLabel {
                border: 1px solid #cfcfcf;
                background: #f7f7f7;
                color: #555;
            }
            """
        )
        self._pixmap: Optional[QPixmap] = None

    def set_image(self, image) -> None:
        pixmap = _numpy_to_pixmap(image)
        self._pixmap = pixmap
        self._refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._pixmap is None:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def sizeHint(self) -> QSize:  # noqa: N802
        # 預覽區大小應由外部布局決定，而不是被 pixmap 本身反推。
        return QSize(320, 240)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(160, 120)


def _numpy_to_pixmap(image) -> QPixmap:
    """
    What:
        將 NumPy/OpenCV 影像轉成 Qt Pixmap。

    Why:
        UI 預覽需要與核心處理格式解耦，避免在 GUI 層散落 BGR/RGB 轉換。
    """
    if image.ndim == 2:
        pil_image = Image.fromarray(image).convert("L").convert("RGB")
    else:
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    qt_image = ImageQt(pil_image)
    if isinstance(qt_image, QImage):
        return QPixmap.fromImage(qt_image)
    return QPixmap.fromImage(QImage(qt_image))


class PhosDesktopWindow(QMainWindow):
    """
    What:
        Phos 桌面主視窗。

    Why:
        將單張與批次處理都集中在一個本地 GUI，徹底取代 Streamlit workflow。
    """

    SPECTRAL_FILMS = ["Portra400", "Velvia50", "Cinestill800T", "HP5Plus400"]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Phos Desktop")

        self.single_file: Optional[Path] = None
        self.batch_files: list[Path] = []
        self.batch_output_dir: Optional[Path] = None
        self.last_result_image = None
        self.last_result_name = ""

        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._worker: Optional[threading.Thread] = None

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_queue)
        self.timer.start(120)

    def _build_ui(self) -> None:
        self.root_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.root_splitter.setChildrenCollapsible(False)
        self.setCentralWidget(self.root_splitter)

        controls_widget = self._build_controls_panel()
        content_widget = self._build_content_panel()

        self.root_splitter.addWidget(controls_widget)
        self.root_splitter.addWidget(content_widget)
        self.root_splitter.setStretchFactor(0, 0)
        self.root_splitter.setStretchFactor(1, 1)
        self.root_splitter.setSizes(
            [
                max(280, controls_widget.sizeHint().width()),
                max(720, content_widget.sizeHint().width()),
            ]
        )

    def _build_controls_panel(self) -> QWidget:
        container = QWidget()
        outer_layout = QVBoxLayout(container)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Phos Desktop")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        scroll_layout.addWidget(title)

        self.film_type_combo = self._combo(list(FILM_PROFILES.keys()), "Portra400")
        self.grain_style_combo = self._combo(["默認", "柔和", "較粗", "不使用"], "默認")
        self.tone_style_combo = self._combo(["filmic", "reinhard"], "filmic")

        general_group = self._form_group("General")
        general_group.layout().addRow("Film", self.film_type_combo)
        general_group.layout().addRow("Grain Style", self.grain_style_combo)
        general_group.layout().addRow("Tone", self.tone_style_combo)
        scroll_layout.addWidget(general_group)

        self.use_film_spectra_checkbox = QCheckBox("啟用光譜膠片敏感度")
        self.film_spectra_combo = self._combo(self.SPECTRAL_FILMS, "Portra400")
        self.film_illuminant_combo = self._combo(["flat", "D65"], "flat")

        spectral_group = self._form_group("Spectral")
        spectral_group.layout().addRow(self.use_film_spectra_checkbox)
        spectral_group.layout().addRow("Spectral Film", self.film_spectra_combo)
        spectral_group.layout().addRow("Illuminant", self.film_illuminant_combo)
        scroll_layout.addWidget(spectral_group)

        self.bloom_mode_combo = self._combo(["artistic", "physical"], "artistic")
        self.bloom_threshold_input = self._double_input(0.5, 0.95, 0.8, 0.01)
        self.bloom_scattering_input = self._double_input(0.01, 0.25, 0.1, 0.01)

        bloom_group = self._form_group("Bloom")
        bloom_group.layout().addRow("Mode", self.bloom_mode_combo)
        bloom_group.layout().addRow("Threshold", self.bloom_threshold_input)
        bloom_group.layout().addRow("Scattering", self.bloom_scattering_input)
        scroll_layout.addWidget(bloom_group)

        self.hd_enabled_checkbox = QCheckBox("啟用 H&D")
        self.hd_gamma_input = self._double_input(0.4, 2.0, 0.65, 0.01)
        self.hd_toe_input = self._double_input(0.1, 5.0, 2.0, 0.1)
        self.hd_shoulder_input = self._double_input(0.1, 5.0, 1.5, 0.1)

        hd_group = self._form_group("H&D Curve")
        hd_group.layout().addRow(self.hd_enabled_checkbox)
        hd_group.layout().addRow("Gamma", self.hd_gamma_input)
        hd_group.layout().addRow("Toe", self.hd_toe_input)
        hd_group.layout().addRow("Shoulder", self.hd_shoulder_input)
        scroll_layout.addWidget(hd_group)

        self.grain_mode_combo = self._combo(["artistic", "poisson"], "artistic")
        self.grain_size_input = self._double_input(0.3, 4.0, 1.5, 0.1)
        self.grain_intensity_input = self._double_input(0.01, 0.9, 0.18, 0.01)

        grain_group = self._form_group("Grain Physics")
        grain_group.layout().addRow("Mode", self.grain_mode_combo)
        grain_group.layout().addRow("Size", self.grain_size_input)
        grain_group.layout().addRow("Intensity", self.grain_intensity_input)
        scroll_layout.addWidget(grain_group)

        self.reciprocity_checkbox = QCheckBox("啟用互易律失效")
        self.exposure_time_input = self._double_input(0.1, 60.0, 1.0, 0.1)

        reciprocity_group = self._form_group("Reciprocity")
        reciprocity_group.layout().addRow(self.reciprocity_checkbox)
        reciprocity_group.layout().addRow("Exposure (s)", self.exposure_time_input)
        scroll_layout.addWidget(reciprocity_group)

        self.status_label = QLabel("=== Status ===\n等待輸入圖像")
        self.status_label.setWordWrap(True)
        status_group = self._form_group("Console")
        status_group.layout().addRow(self.status_label)
        scroll_layout.addWidget(status_group)

        scroll.setWidget(scroll_content)
        outer_layout.addWidget(scroll)
        return container

    def _build_content_panel(self) -> QWidget:
        tabs = QTabWidget()
        tabs.addTab(self._build_single_tab(), "單張處理")
        tabs.addTab(self._build_batch_tab(), "批次處理")
        return tabs

    def _build_single_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        toolbar = QHBoxLayout()
        open_button = QPushButton("開啟照片")
        open_button.clicked.connect(self._choose_single_file)
        toolbar.addWidget(open_button)

        process_button = QPushButton("開始處理")
        process_button.clicked.connect(self._start_single_processing)
        toolbar.addWidget(process_button)

        save_button = QPushButton("儲存結果")
        save_button.clicked.connect(self._save_single_result)
        toolbar.addWidget(save_button)

        self.single_file_label = QLabel("尚未選擇檔案")
        toolbar.addWidget(self.single_file_label, 1)
        layout.addLayout(toolbar)

        preview_row = QHBoxLayout()
        preview_row.setSpacing(8)

        self.original_preview = ImagePreviewLabel("Original")
        self.result_preview = ImagePreviewLabel("Result")

        preview_row.addWidget(self._build_preview_panel(self.original_preview), 1)
        preview_row.addWidget(self._build_preview_panel(self.result_preview), 1)
        layout.addLayout(preview_row, 1)

        return tab

    def _build_batch_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        toolbar = QHBoxLayout()
        add_button = QPushButton("加入照片")
        add_button.clicked.connect(self._add_batch_files)
        toolbar.addWidget(add_button)

        clear_button = QPushButton("清空")
        clear_button.clicked.connect(self._clear_batch_files)
        toolbar.addWidget(clear_button)

        output_button = QPushButton("選擇輸出資料夾")
        output_button.clicked.connect(self._choose_batch_output_dir)
        toolbar.addWidget(output_button)

        start_button = QPushButton("開始批次處理")
        start_button.clicked.connect(self._start_batch_processing)
        toolbar.addWidget(start_button)

        self.batch_output_label = QLabel("未設定輸出資料夾")
        self.batch_output_label.setWordWrap(True)
        toolbar.addWidget(self.batch_output_label, 1)
        layout.addLayout(toolbar)

        body_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.batch_list = QListWidget()
        body_splitter.addWidget(self.batch_list)

        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        self.batch_progress = QProgressBar()
        self.batch_status_label = QLabel("=== Batch ===\n尚未加入檔案")
        self.batch_status_label.setWordWrap(True)
        progress_layout.addWidget(self.batch_progress)
        progress_layout.addWidget(self.batch_status_label)
        progress_layout.addStretch(1)
        body_splitter.addWidget(progress_widget)

        body_splitter.setStretchFactor(0, 2)
        body_splitter.setStretchFactor(1, 1)
        layout.addWidget(body_splitter, 1)

        return tab

    def _form_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setLayout(QFormLayout())
        return group

    def _build_preview_panel(self, preview_label: ImagePreviewLabel) -> QFrame:
        """
        What:
            建立左右一致的預覽畫布容器。

        Why:
            讓畫布尺寸只受父布局控制，不受載入圖片的像素尺寸影響。
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(preview_label, 1)
        return frame

    def _combo(self, values: list[str], default: str) -> QComboBox:
        combo = QComboBox()
        combo.addItems(values)
        if default in values:
            combo.setCurrentText(default)
        return combo

    def _double_input(self, minimum: float, maximum: float, value: float, step: float) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setValue(value)
        widget.setSingleStep(step)
        widget.setDecimals(4 if step < 0.1 else 2)
        return widget

    def _collect_physics_params(self) -> dict[str, Any]:
        return {
            "physics_mode": PhysicsMode.PHYSICAL,
            "bloom_mode": self.bloom_mode_combo.currentText(),
            "bloom_threshold": self.bloom_threshold_input.value(),
            "bloom_scattering_ratio": self.bloom_scattering_input.value(),
            "hd_enabled": self.hd_enabled_checkbox.isChecked(),
            "hd_gamma": self.hd_gamma_input.value(),
            "hd_toe_strength": self.hd_toe_input.value(),
            "hd_shoulder_strength": self.hd_shoulder_input.value(),
            "grain_mode": self.grain_mode_combo.currentText(),
            "grain_size": self.grain_size_input.value(),
            "grain_intensity": self.grain_intensity_input.value(),
            "reciprocity_enabled": self.reciprocity_checkbox.isChecked(),
            "exposure_time": self.exposure_time_input.value(),
        }

    def _choose_single_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇照片",
            "",
            "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp)",
        )
        if not file_path:
            return

        self.single_file = Path(file_path)
        self.single_file_label.setText(self.single_file.name)
        self.status_label.setText(f"=== Status ===\n已載入: {self.single_file.name}")
        image = cv2.imread(str(self.single_file), cv2.IMREAD_COLOR)
        if image is not None:
            self.original_preview.set_image(image)

    def _start_single_processing(self) -> None:
        if self._is_busy():
            return
        if self.single_file is None:
            QMessageBox.critical(self, "Phos Desktop", "請先選擇照片")
            return

        self.status_label.setText(f"=== Status ===\n處理中: {self.single_file.name}")

        def worker() -> None:
            try:
                result = process_image(
                    self.single_file,
                    self.film_type_combo.currentText(),
                    self.grain_style_combo.currentText(),
                    self.tone_style_combo.currentText(),
                    physics_params=self._collect_physics_params(),
                    use_film_spectra=self.use_film_spectra_checkbox.isChecked(),
                    film_spectra_name=self.film_spectra_combo.currentText(),
                    film_illuminant=self.film_illuminant_combo.currentText(),
                )
                self._queue.put({"type": "single_done", "result": result})
            except Exception as exc:
                self._queue.put({"type": "error", "message": str(exc)})

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _save_single_result(self) -> None:
        if self.last_result_image is None:
            QMessageBox.information(self, "Phos Desktop", "目前沒有可儲存的結果")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存結果",
            self.last_result_name or "phos_output.jpg",
            "JPEG (*.jpg);;PNG (*.png)",
        )
        if not file_path:
            return

        self._write_image(Path(file_path), self.last_result_image)
        self.status_label.setText(f"=== Status ===\n已儲存: {Path(file_path).name}")

    def _add_batch_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "加入批次照片",
            "",
            "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp)",
        )
        if not files:
            return

        for raw_path in files:
            path = Path(raw_path)
            if path not in self.batch_files:
                self.batch_files.append(path)
                self.batch_list.addItem(path.name)

        self.batch_status_label.setText(f"=== Batch ===\n已加入 {len(self.batch_files)} 張照片")

    def _clear_batch_files(self) -> None:
        self.batch_files.clear()
        self.batch_list.clear()
        self.batch_progress.setValue(0)
        self.batch_status_label.setText("=== Batch ===\n尚未加入檔案")

    def _choose_batch_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if not directory:
            return

        self.batch_output_dir = Path(directory)
        self.batch_output_label.setText(str(self.batch_output_dir))

    def _start_batch_processing(self) -> None:
        if self._is_busy():
            return
        if not self.batch_files:
            QMessageBox.critical(self, "Phos Desktop", "請先加入批次照片")
            return
        if self.batch_output_dir is None:
            QMessageBox.critical(self, "Phos Desktop", "請先選擇輸出資料夾")
            return

        self.batch_progress.setMaximum(len(self.batch_files))
        self.batch_progress.setValue(0)
        self.batch_status_label.setText(f"=== Batch ===\n開始處理 {len(self.batch_files)} 張照片")

        def worker() -> None:
            success_count = 0
            for index, path in enumerate(self.batch_files, start=1):
                try:
                    final_image, _, output_name, _ = process_image(
                        path,
                        self.film_type_combo.currentText(),
                        self.grain_style_combo.currentText(),
                        self.tone_style_combo.currentText(),
                        physics_params=self._collect_physics_params(),
                        use_film_spectra=self.use_film_spectra_checkbox.isChecked(),
                        film_spectra_name=self.film_spectra_combo.currentText(),
                        film_illuminant=self.film_illuminant_combo.currentText(),
                    )
                    output_path = self.batch_output_dir / f"{path.stem}_{output_name}"
                    self._write_image(output_path, final_image)
                    success_count += 1
                    self._queue.put(
                        {
                            "type": "batch_progress",
                            "index": index,
                            "total": len(self.batch_files),
                            "name": path.name,
                        }
                    )
                except Exception as exc:
                    self._queue.put(
                        {
                            "type": "batch_error",
                            "index": index,
                            "total": len(self.batch_files),
                            "name": path.name,
                            "message": str(exc),
                        }
                    )

            self._queue.put(
                {
                    "type": "batch_done",
                    "success_count": success_count,
                    "total": len(self.batch_files),
                }
            )

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _write_image(self, output_path: Path, image) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if image.ndim == 2:
            pil_image = Image.fromarray(image)
        else:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if output_path.suffix.lower() == ".png":
            pil_image.save(output_path, format="PNG")
        else:
            pil_image.save(output_path, format="JPEG", quality=95)

    def _poll_queue(self) -> None:
        try:
            while True:
                message = self._queue.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            return

    def _handle_message(self, message: dict[str, Any]) -> None:
        message_type = message["type"]

        if message_type == "single_done":
            final_image, process_time, output_name, original_image = message["result"]
            self.last_result_image = final_image
            self.last_result_name = output_name
            self.original_preview.set_image(original_image)
            self.result_preview.set_image(final_image)
            current_name = self.single_file.name if self.single_file else output_name
            self.status_label.setText(
                "=== Status ===\n"
                f"完成: {current_name}\n"
                f"耗時: {process_time:.2f}s\n"
                f"輸出: {output_name}"
            )
            self._worker = None
            return

        if message_type == "batch_progress":
            self.batch_progress.setValue(message["index"])
            self.batch_status_label.setText(
                "=== Batch ===\n"
                f"[{message['index']}/{message['total']}] {message['name']}"
            )
            return

        if message_type == "batch_error":
            self.batch_progress.setValue(message["index"])
            self.batch_status_label.setText(
                "=== Batch ===\n"
                f"[{message['index']}/{message['total']}] 失敗: {message['name']}\n"
                f"{message['message']}"
            )
            return

        if message_type == "batch_done":
            self.batch_progress.setValue(message["total"])
            self.batch_status_label.setText(
                "=== Batch ===\n"
                f"完成: {message['success_count']}/{message['total']} 成功"
            )
            self._worker = None
            return

        if message_type == "error":
            self.status_label.setText(f"=== Status ===\n錯誤: {message['message']}")
            QMessageBox.critical(self, "Phos Desktop", message["message"])
            self._worker = None

    def _is_busy(self) -> bool:
        if self._worker is not None and self._worker.is_alive():
            QMessageBox.information(self, "Phos Desktop", "目前仍有處理作業進行中")
            return True
        return False


def main() -> None:
    """
    What:
        啟動桌面應用。

    Why:
        提供命令列與打包器共用的標準入口點。
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Phos Desktop")
    window = PhosDesktopWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
