"""
Match the Halves - PySide6 Desktop GUI Application.
"""

import os
import random
import sys
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QLineEdit, QFileDialog, QProgressBar, QTextEdit, QGroupBox,
    QListWidget, QListWidgetItem, QSlider, QMessageBox, QFrame,
    QSplitter
)
from PySide6.QtGui import QIcon, QFont, QColor

import engine

class RenderWorker(QThread):
    progress = Signal(float, str)
    finished_success = Signal(str)
    failed = Signal(str)

    def __init__(self, items, bg_path, symbols_dir, output_path, audio_mode, custom_audio_path, music_vol):
        super().__init__()
        self.items = items
        self.bg_path = bg_path
        self.symbols_dir = symbols_dir
        self.output_path = output_path
        self.audio_mode = audio_mode
        self.custom_audio_path = custom_audio_path
        self.music_vol = music_vol

    def run(self):
        try:
            def cb(frac, text):
                self.progress.emit(frac, text)
                
            engine.generate_video(
                items=self.items,
                background_path=self.bg_path,
                symbols_dir=self.symbols_dir,
                output_path=self.output_path,
                audio_mode=self.audio_mode,
                custom_audio_path=self.custom_audio_path,
                music_volume=self.music_vol,
                progress_callback=cb
            )
            self.finished_success.emit(self.output_path)
        except Exception as e:
            self.failed.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Match the Halves — Kids Video Generator")
        self.resize(920, 840)
        self.setMinimumSize(850, 750)
        
        self.sets_dir = os.path.abspath("sets")
        self.backgrounds_dir = os.path.abspath("backgrounds")
        self.symbols_dir = os.path.abspath("symbols")
        self.categories_data = {}
        self.backgrounds_data = []
        self.worker = None

        self.setup_ui()
        self.apply_theme()
        
        # Check FFmpeg at startup
        ffmpeg_ok, ffmpeg_msg = engine.check_ffmpeg()
        if not ffmpeg_ok:
            self.log(f"WARNING: {ffmpeg_msg}")
            QMessageBox.critical(self, "FFmpeg Missing", ffmpeg_msg)
        else:
            self.log("FFmpeg is available on PATH.")

        self.rescan_all()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title Banner
        header = QFrame()
        header.setObjectName("headerBanner")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(14, 10, 14, 10)
        title = QLabel("🎨 Match the Halves")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Generate viral 'match the halves' kids videos (9:16 vertical 1080x1920) for YouTube Shorts, Reels & TikTok")
        subtitle.setObjectName("subtitleLabel")
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        main_layout.addWidget(header)

        # 1. Folder Locations Group
        folders_group = QGroupBox("📁 Folders & Discovery")
        f_layout = QVBoxLayout(folders_group)
        
        # Sets folder row
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Sets Folder:"))
        self.sets_input = QLineEdit(self.sets_dir)
        self.sets_input.textChanged.connect(self.on_sets_dir_changed)
        r1.addWidget(self.sets_input)
        btn_sets = QPushButton("Browse...")
        btn_sets.clicked.connect(self.browse_sets)
        r1.addWidget(btn_sets)
        f_layout.addLayout(r1)

        # Backgrounds folder row
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Backgrounds:"))
        self.bg_input = QLineEdit(self.backgrounds_dir)
        self.bg_input.textChanged.connect(self.on_bg_dir_changed)
        r2.addWidget(self.bg_input)
        btn_bg = QPushButton("Browse...")
        btn_bg.clicked.connect(self.browse_backgrounds)
        r2.addWidget(btn_bg)

        # Symbols folder row
        r2.addWidget(QLabel("Symbols:"))
        self.symbols_input = QLineEdit(self.symbols_dir)
        self.symbols_input.textChanged.connect(self.on_symbols_dir_changed)
        r2.addWidget(self.symbols_input)
        btn_sym = QPushButton("Browse...")
        btn_sym.clicked.connect(self.browse_symbols)
        r2.addWidget(btn_sym)
        f_layout.addLayout(r2)

        # Rescan button + Category summary label
        r_sum = QHBoxLayout()
        self.summary_label = QLabel("Scanning folders...")
        self.summary_label.setObjectName("summaryLabel")
        r_sum.addWidget(self.summary_label, stretch=1)
        btn_rescan = QPushButton("🔄 Refresh Folders")
        btn_rescan.clicked.connect(self.rescan_all)
        r_sum.addWidget(btn_rescan)
        f_layout.addLayout(r_sum)
        main_layout.addWidget(folders_group)

        # 2. Video Options Group (Two Columns)
        options_group = QGroupBox("⚙️ Video Configuration")
        opt_layout = QHBoxLayout(options_group)
        
        # Left Column: Category, Item Count, Items Picker
        col_left = QVBoxLayout()
        
        # Category Dropdown
        row_cat = QHBoxLayout()
        row_cat.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.currentIndexChanged.connect(self.on_category_selected)
        row_cat.addWidget(self.cat_combo, stretch=1)
        col_left.addLayout(row_cat)

        # Count Radio (3 or 4)
        row_count = QHBoxLayout()
        row_count.addWidget(QLabel("Character Count:"))
        self.radio_3 = QRadioButton("3 Items")
        self.radio_4 = QRadioButton("4 Items")
        self.radio_3.setChecked(True)
        self.count_group = QButtonGroup()
        self.count_group.addButton(self.radio_3, 3)
        self.count_group.addButton(self.radio_4, 4)
        self.count_group.buttonClicked.connect(self.on_count_changed)
        row_count.addWidget(self.radio_3)
        row_count.addWidget(self.radio_4)
        row_count.addStretch()
        col_left.addLayout(row_count)

        # Item Selection mode: Random vs Checklist
        row_mode = QHBoxLayout()
        self.radio_random_items = QRadioButton("Random Items (Default)")
        self.radio_manual_items = QRadioButton("Custom Selection & Stack Order")
        self.radio_random_items.setChecked(True)
        self.item_mode_group = QButtonGroup()
        self.item_mode_group.addButton(self.radio_random_items)
        self.item_mode_group.addButton(self.radio_manual_items)
        self.item_mode_group.buttonClicked.connect(self.on_item_mode_changed)
        row_mode.addWidget(self.radio_random_items)
        row_mode.addWidget(self.radio_manual_items)
        col_left.addLayout(row_mode)

        # Manual Items ListWidget
        self.items_list_label = QLabel("Select items (top to bottom order in stack):")
        self.items_list_label.setVisible(False)
        col_left.addWidget(self.items_list_label)
        
        self.items_list = QListWidget()
        self.items_list.setMaximumHeight(140)
        self.items_list.setVisible(False)
        self.items_list.itemChanged.connect(self.update_preview_summary)
        col_left.addWidget(self.items_list)

        # Move up / down buttons for ordering
        self.order_btn_layout = QHBoxLayout()
        self.btn_move_up = QPushButton("▲ Move Up")
        self.btn_move_down = QPushButton("▼ Move Down")
        self.btn_move_up.clicked.connect(self.move_item_up)
        self.btn_move_down.clicked.connect(self.move_item_down)
        self.order_btn_layout.addWidget(self.btn_move_up)
        self.order_btn_layout.addWidget(self.btn_move_down)
        self.btn_move_up.setVisible(False)
        self.btn_move_down.setVisible(False)
        col_left.addLayout(self.order_btn_layout)

        opt_layout.addLayout(col_left, stretch=1)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Sunken)
        opt_layout.addWidget(divider)

        # Right Column: Background & Audio
        col_right = QVBoxLayout()
        
        # Background Picker
        row_bg = QHBoxLayout()
        row_bg.addWidget(QLabel("Background:"))
        self.bg_combo = QComboBox()
        self.bg_combo.currentIndexChanged.connect(self.update_preview_summary)
        row_bg.addWidget(self.bg_combo, stretch=1)
        col_right.addLayout(row_bg)

        # Audio Section
        audio_subgroup = QGroupBox("🔊 Audio Soundtrack")
        aud_layout = QVBoxLayout(audio_subgroup)
        
        self.radio_audio_builtin = QRadioButton("Built-in tune (Default gentle music-box)")
        self.radio_audio_custom = QRadioButton("My music file (.mp3 / .wav)")
        self.radio_audio_mute = QRadioButton("Mute (No audio stream)")
        self.radio_audio_builtin.setChecked(True)
        
        self.audio_group = QButtonGroup()
        self.audio_group.addButton(self.radio_audio_builtin)
        self.audio_group.addButton(self.radio_audio_custom)
        self.audio_group.addButton(self.radio_audio_mute)
        self.audio_group.buttonClicked.connect(self.on_audio_mode_changed)
        
        aud_layout.addWidget(self.radio_audio_builtin)
        aud_layout.addWidget(self.radio_audio_custom)
        
        # Custom music file picker
        self.music_file_layout = QHBoxLayout()
        self.music_file_input = QLineEdit()
        self.music_file_input.setPlaceholderText("Select .mp3 or .wav music file...")
        self.music_file_input.setEnabled(False)
        self.music_file_input.textChanged.connect(self.update_preview_summary)
        self.btn_music_browse = QPushButton("Browse...")
        self.btn_music_browse.setEnabled(False)
        self.btn_music_browse.clicked.connect(self.browse_music_file)
        self.music_file_layout.addWidget(self.music_file_input)
        self.music_file_layout.addWidget(self.btn_music_browse)
        aud_layout.addLayout(self.music_file_layout)

        # Music Volume Slider
        self.vol_layout = QHBoxLayout()
        self.vol_label = QLabel("Music Volume: 50%")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(50)
        self.vol_slider.setEnabled(False)
        self.vol_slider.valueChanged.connect(lambda v: self.vol_label.setText(f"Music Volume: {v}%"))
        self.vol_layout.addWidget(self.vol_label)
        self.vol_layout.addWidget(self.vol_slider)
        aud_layout.addLayout(self.vol_layout)

        aud_layout.addWidget(self.radio_audio_mute)
        col_right.addWidget(audio_subgroup)

        opt_layout.addLayout(col_right, stretch=1)
        main_layout.addWidget(options_group)

        # 3. Output Destination & Preview Summary Line
        out_group = QGroupBox("🎬 Output & Generation")
        out_layout = QVBoxLayout(out_group)
        
        row_out = QHBoxLayout()
        row_out.addWidget(QLabel("Output File:"))
        self.out_input = QLineEdit(os.path.abspath("match_the_halves_output.mp4"))
        row_out.addWidget(self.out_input)
        btn_out = QPushButton("Save As...")
        btn_out.clicked.connect(self.browse_output_file)
        row_out.addWidget(btn_out)
        out_layout.addLayout(row_out)

        # Preview line
        self.preview_line = QLabel("Preview: Preparing...")
        self.preview_line.setObjectName("previewLine")
        out_layout.addWidget(self.preview_line)

        # Generate Button & Progress
        row_gen = QHBoxLayout()
        self.btn_generate = QPushButton("🚀 Generate Video")
        self.btn_generate.setObjectName("generateButton")
        self.btn_generate.setFixedHeight(44)
        self.btn_generate.clicked.connect(self.start_generation)
        row_gen.addWidget(self.btn_generate)
        out_layout.addLayout(row_gen)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        out_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        out_layout.addWidget(self.status_label)

        main_layout.addWidget(out_group)

        # 4. Activity Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(130)
        main_layout.addWidget(self.log_area)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F9FA;
            }
            #headerBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4A90E2, stop:1 #50E3C2);
                border-radius: 8px;
            }
            #titleLabel {
                color: #FFFFFF;
                font-size: 20px;
                font-weight: bold;
            }
            #subtitleLabel {
                color: #F0F8FF;
                font-size: 12px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                background-color: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 4px;
                color: #2D3748;
            }
            QLineEdit, QComboBox, QListWidget {
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 5px 8px;
                background-color: #FFFFFF;
                font-size: 13px;
            }
            QPushButton {
                background-color: #E2E8F0;
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #CBD5E1;
            }
            #generateButton {
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                font-size: 15px;
                font-weight: bold;
                border-radius: 6px;
            }
            #generateButton:hover {
                background-color: #059669;
            }
            #generateButton:disabled {
                background-color: #9CA3AF;
            }
            #previewLine {
                background-color: #EFF6FF;
                border: 1px solid #BFDBFE;
                color: #1E40AF;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            #summaryLabel {
                color: #4B5563;
                font-size: 12px;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #1E293B;
                color: #F1F5F9;
                font-family: Consolas, monospace;
                font-size: 12px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
        """)

    def log(self, text):
        self.log_area.append(text)
        print(text)

    # --- Directory Browsing ---

    def browse_sets(self):
        d = QFileDialog.getExistingDirectory(self, "Select Sets Folder", self.sets_dir)
        if d:
            self.sets_input.setText(d)

    def browse_backgrounds(self):
        d = QFileDialog.getExistingDirectory(self, "Select Backgrounds Folder", self.backgrounds_dir)
        if d:
            self.bg_input.setText(d)

    def browse_symbols(self):
        d = QFileDialog.getExistingDirectory(self, "Select Symbols Folder", self.symbols_dir)
        if d:
            self.symbols_input.setText(d)

    def browse_music_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Music File", "", "Audio Files (*.mp3 *.wav *.m4a *.aac)")
        if f:
            self.music_file_input.setText(f)

    def browse_output_file(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save Video As", self.out_input.text(), "MP4 Video (*.mp4)")
        if f:
            self.out_input.setText(f)

    def on_sets_dir_changed(self, text):
        self.sets_dir = text.strip()
        self.rescan_categories()

    def on_bg_dir_changed(self, text):
        self.backgrounds_dir = text.strip()
        self.rescan_backgrounds()

    def on_symbols_dir_changed(self, text):
        self.symbols_dir = text.strip()
        self.update_preview_summary()

    # --- Discovery & Scanning ---

    def rescan_all(self):
        self.rescan_categories()
        self.rescan_backgrounds()
        self.update_preview_summary()

    def rescan_categories(self):
        self.categories_data, warnings = engine.discover_categories(self.sets_dir)
        for w in warnings:
            self.log(f"⚠️ {w}")
            
        self.cat_combo.blockSignals(True)
        self.cat_combo.clear()
        
        summary_parts = []
        for cat_name, items in sorted(self.categories_data.items()):
            count = len(items)
            self.cat_combo.addItem(f"{cat_name.title()} ({count} items)", userData=cat_name)
            summary_parts.append(f"{cat_name.title()}: {count} items")
            
        self.cat_combo.blockSignals(False)
        
        if summary_parts:
            self.summary_label.setText("Discovered: " + " | ".join(summary_parts))
        else:
            self.summary_label.setText("No categories found in sets folder.")
            
        self.on_category_selected()

    def rescan_backgrounds(self):
        self.backgrounds_data = engine.discover_backgrounds(self.backgrounds_dir)
        self.bg_combo.blockSignals(True)
        self.bg_combo.clear()
        self.bg_combo.addItem("🎲 Random Background", userData="random")
        for bg in self.backgrounds_data:
            self.bg_combo.addItem(os.path.basename(bg), userData=bg)
        self.bg_combo.blockSignals(False)
        self.update_preview_summary()

    def on_category_selected(self):
        cat_key = self.get_selected_category_key()
        items = self.categories_data.get(cat_key, []) if cat_key else []
        
        self.items_list.blockSignals(True)
        self.items_list.clear()
        for it in items:
            item_widget = QListWidgetItem(it["name"])
            item_widget.setFlags(item_widget.flags() | Qt.ItemIsUserCheckable)
            item_widget.setCheckState(Qt.Unchecked)
            item_widget.setData(Qt.UserRole, it)
            self.items_list.addItem(item_widget)
        self.items_list.blockSignals(False)
        
        self.update_preview_summary()

    def get_selected_category_key(self):
        idx = self.cat_combo.currentIndex()
        if idx >= 0:
            return self.cat_combo.itemData(idx)
        return None

    def on_count_changed(self):
        self.update_preview_summary()

    def on_item_mode_changed(self):
        is_manual = self.radio_manual_items.isChecked()
        self.items_list_label.setVisible(is_manual)
        self.items_list.setVisible(is_manual)
        self.btn_move_up.setVisible(is_manual)
        self.btn_move_down.setVisible(is_manual)
        self.update_preview_summary()

    def move_item_up(self):
        row = self.items_list.currentRow()
        if row > 0:
            item = self.items_list.takeItem(row)
            self.items_list.insertItem(row - 1, item)
            self.items_list.setCurrentRow(row - 1)
            self.update_preview_summary()

    def move_item_down(self):
        row = self.items_list.currentRow()
        if row >= 0 and row < self.items_list.count() - 1:
            item = self.items_list.takeItem(row)
            self.items_list.insertItem(row + 1, item)
            self.items_list.setCurrentRow(row + 1)
            self.update_preview_summary()

    def on_audio_mode_changed(self):
        is_custom = self.radio_audio_custom.isChecked()
        self.music_file_input.setEnabled(is_custom)
        self.btn_music_browse.setEnabled(is_custom)
        self.vol_slider.setEnabled(is_custom)
        self.update_preview_summary()

    # --- Preview Line Generation ---

    def update_preview_summary(self):
        cat_key = self.get_selected_category_key()
        count = self.count_group.checkedId()
        if count not in (3, 4):
            count = 3

        cat_items = self.categories_data.get(cat_key, []) if cat_key else []
        
        # Determine items
        if self.radio_manual_items.isChecked():
            checked_items = []
            for i in range(self.items_list.count()):
                it = self.items_list.item(i)
                if it.checkState() == Qt.Checked:
                    checked_items.append(it.text())
            items_desc = f"{len(checked_items)}/{count} selected: " + (", ".join(checked_items) if checked_items else "none")
        else:
            if len(cat_items) >= count:
                sample_names = [it["name"] for it in cat_items[:count]]
                items_desc = f"{count} {cat_key or 'items'}: " + ", ".join(sample_names)
            else:
                items_desc = f"{count} {cat_key or 'items'}: (only {len(cat_items)} available!)"

        # Background
        bg_idx = self.bg_combo.currentIndex()
        bg_data = self.bg_combo.itemData(bg_idx) if bg_idx >= 0 else None
        if bg_data == "random":
            bg_desc = "Random"
        elif bg_data:
            bg_desc = os.path.basename(bg_data)
        else:
            bg_desc = "Default built-in"

        # Audio
        if self.radio_audio_builtin.isChecked():
            audio_desc = "Built-in tune"
        elif self.radio_audio_custom.isChecked():
            mf = os.path.basename(self.music_file_input.text().strip()) or "No file selected"
            audio_desc = f"Music ({mf}, {self.vol_slider.value()}%)"
        else:
            audio_desc = "Mute"

        preview_text = f"Preview: {items_desc} — background: {bg_desc} — audio: {audio_desc}"
        self.preview_line.setText(preview_text)

    # --- Validation & Generation ---

    def validate_inputs(self):
        # 1. FFmpeg
        ffmpeg_ok, ffmpeg_msg = engine.check_ffmpeg()
        if not ffmpeg_ok:
            return False, ffmpeg_msg

        # 2. Category
        cat_key = self.get_selected_category_key()
        if not cat_key:
            return False, "Please select a category from the sets folder."
            
        cat_items = self.categories_data.get(cat_key, [])
        if not cat_items:
            return False, f"Category '{cat_key}' has no valid pairs (matching -1/-2 or -left/-right)."

        # 3. Item Count
        count = self.count_group.checkedId()
        if count not in (3, 4):
            count = 3
            
        if len(cat_items) < count:
            return False, f"Category '{cat_key}' has only {len(cat_items)} items, but {count} are required."

        # 4. Item Selection
        selected_items = []
        if self.radio_manual_items.isChecked():
            for i in range(self.items_list.count()):
                w_item = self.items_list.item(i)
                if w_item.checkState() == Qt.Checked:
                    selected_items.append(w_item.data(Qt.UserRole))
            if len(selected_items) != count:
                return False, f"Please check exactly {count} items for custom order (currently selected: {len(selected_items)})."
        else:
            # Pick random items from category
            selected_items = random.sample(cat_items, count)

        # 5. Background
        bg_idx = self.bg_combo.currentIndex()
        bg_data = self.bg_combo.itemData(bg_idx) if bg_idx >= 0 else None
        if bg_data == "random":
            if self.backgrounds_data:
                bg_path = random.choice(self.backgrounds_data)
            else:
                bg_path = None
        else:
            bg_path = bg_data

        # 6. Audio
        if self.radio_audio_builtin.isChecked():
            audio_mode = "builtin"
            custom_path = None
        elif self.radio_audio_custom.isChecked():
            audio_mode = "custom"
            custom_path = self.music_file_input.text().strip()
            if not custom_path or not os.path.exists(custom_path):
                return False, "Custom music file does not exist or was not selected."
            # Verify readability
            try:
                engine.load_user_music(custom_path, duration_sec=1.0)
            except Exception as e:
                return False, f"Music file is unreadable: {e}"
        else:
            audio_mode = "mute"
            custom_path = None

        # 7. Output Path
        out_path = self.out_input.text().strip()
        if not out_path:
            return False, "Please specify an output filename."
        out_dir = os.path.dirname(os.path.abspath(out_path))
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create output directory: {e}"

        return True, {
            "items": selected_items,
            "bg_path": bg_path,
            "symbols_dir": self.symbols_dir,
            "output_path": out_path,
            "audio_mode": audio_mode,
            "custom_audio_path": custom_path,
            "music_vol": self.vol_slider.value() / 100.0
        }

    def start_generation(self):
        valid, result = self.validate_inputs()
        if not valid:
            QMessageBox.warning(self, "Validation Error", result)
            self.log(f"Validation failed: {result}")
            return

        self.btn_generate.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting rendering...")
        
        items_str = ", ".join([it["name"] for it in result["items"]])
        self.log(f"\n==========================================")
        self.log(f"Starting Video Generation:")
        self.log(f" - Items ({len(result['items'])}): {items_str}")
        self.log(f" - Background: {result['bg_path'] or 'Built-in default'}")
        self.log(f" - Audio mode: {result['audio_mode']}")
        self.log(f" - Output file: {result['output_path']}")

        self.worker = RenderWorker(
            items=result["items"],
            bg_path=result["bg_path"],
            symbols_dir=result["symbols_dir"],
            output_path=result["output_path"],
            audio_mode=result["audio_mode"],
            custom_audio_path=result["custom_audio_path"],
            music_vol=result["music_vol"]
        )
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished_success.connect(self.on_worker_success)
        self.worker.failed.connect(self.on_worker_failed)
        self.worker.start()

    def on_worker_progress(self, frac, text):
        self.progress_bar.setValue(int(frac * 100))
        self.status_label.setText(text)
        if int(frac * 100) % 20 == 0:
            self.log(text)

    def on_worker_success(self, out_path):
        self.btn_generate.setEnabled(True)
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Done! Saved to {os.path.basename(out_path)}")
        self.log(f"SUCCESS: Video generated at {out_path}")
        QMessageBox.information(
            self,
            "Generation Complete",
            f"Video was generated successfully!\n\nFile saved to:\n{out_path}"
        )

    def on_worker_failed(self, error_msg):
        self.btn_generate.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Error during generation.")
        self.log(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Rendering Error", f"Generation failed:\n{error_msg}")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
