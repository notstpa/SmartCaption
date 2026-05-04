import os
import sys
import shutil
import stat

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from huggingface_hub.utils import disable_progress_bars
import qdarktheme

APP_NAME = "SmartCaption"
MODEL_REPO_PREFIX = "Systran/faster-whisper-"
SUPPORTED_MEDIA_EXTENSIONS = (
    ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".wma",
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".mpeg", ".mpg", ".m4v"
)
SUPPORTED_LANGUAGE_NAMES = {
    "af": "Afrikaans",
    "am": "Amharic",
    "ar": "Arabic",
    "as": "Assamese",
    "az": "Azerbaijani",
    "ba": "Bashkir",
    "be": "Belarusian",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "bo": "Tibetan",
    "br": "Breton",
    "bs": "Bosnian",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "fi": "Finnish",
    "fo": "Faroese",
    "fr": "French",
    "gl": "Galician",
    "gu": "Gujarati",
    "ha": "Hausa",
    "haw": "Hawaiian",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "ht": "Haitian Creole",
    "hu": "Hungarian",
    "hy": "Armenian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "jw": "Javanese",
    "ka": "Georgian",
    "kk": "Kazakh",
    "km": "Khmer",
    "kn": "Kannada",
    "ko": "Korean",
    "la": "Latin",
    "lb": "Luxembourgish",
    "ln": "Lingala",
    "lo": "Lao",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mg": "Malagasy",
    "mi": "Maori",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mn": "Mongolian",
    "mr": "Marathi",
    "ms": "Malay",
    "mt": "Maltese",
    "my": "Myanmar",
    "ne": "Nepali",
    "nl": "Dutch",
    "nn": "Nynorsk",
    "no": "Norwegian",
    "oc": "Occitan",
    "pa": "Punjabi",
    "pl": "Polish",
    "ps": "Pashto",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sa": "Sanskrit",
    "sd": "Sindhi",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sn": "Shona",
    "so": "Somali",
    "sq": "Albanian",
    "sr": "Serbian",
    "su": "Sundanese",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "tg": "Tajik",
    "th": "Thai",
    "tk": "Turkmen",
    "tl": "Tagalog",
    "tr": "Turkish",
    "tt": "Tatar",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "zh": "Chinese",
    "yue": "Cantonese",
}


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(filename):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def get_user_data_dir():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return os.path.join(local_appdata, APP_NAME)

    return os.path.join(os.path.expanduser("~"), APP_NAME)


def ensure_writable_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe_path = os.path.join(path, ".smartcaption_write_test")
        with open(probe_path, "w", encoding="utf-8") as probe_file:
            probe_file.write("ok")
        os.remove(probe_path)
        return True
    except OSError:
        return False


def resolve_model_dir(app_dir):
    preferred_dir = os.path.join(app_dir, "models")
    if ensure_writable_dir(preferred_dir):
        return preferred_dir, "local"

    fallback_dir = os.path.join(get_user_data_dir(), "models")
    if ensure_writable_dir(fallback_dir):
        return fallback_dir, "user"

    raise OSError("Unable to create a writable models folder.")


APP_DIR = get_app_dir()
MODEL_DIR, MODEL_DIR_MODE = resolve_model_dir(APP_DIR)
APP_ICON_PATH = get_resource_path("icon.ico")

WINDOW_BG = "#171717"
PANEL_BG = "#202020"
INPUT_BG = "#2A2A2A"
INACTIVE_TAB_BG = "#1C1C1C"
BORDER = "#3A3A3A"
SOFT_BORDER = "#303030"
TEXT = "#F2F2F2"
MUTED_TEXT = "#B8B8B8"
DISABLED_TEXT = "#7A7A7A"
BUTTON_BG = "#333333"
BUTTON_HOVER_BG = "#404040"
BUTTON_PRESSED_BG = "#292929"
ACCENT = "#8E8E8E"
SELECTION_BG = "#555555"
PROGRESS_BG = "#A5A5A5"


def build_theme_stylesheet():
    return f"""
        * {{
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 13px;
            color: {TEXT};
            selection-background-color: {SELECTION_BG};
            selection-color: {TEXT};
        }}
        QMainWindow, QDialog, QWidget#centralWidget {{
            background: {WINDOW_BG};
            color: {TEXT};
        }}
        QWidget {{
            background: {WINDOW_BG};
            color: {TEXT};
        }}
        QFrame {{
            background: {PANEL_BG};
            border: 1px solid {SOFT_BORDER};
            border-radius: 8px;
        }}
        QFrame#card {{
            background: {PANEL_BG};
            border: 1px solid {BORDER};
            border-radius: 8px;
        }}
        QFrame#innerCard {{
            background: {INPUT_BG};
            border: 1px solid {SOFT_BORDER};
            border-radius: 8px;
        }}
        QLabel {{
            background: transparent;
            border: none;
            color: {TEXT};
        }}
        QLabel#title {{
            font-size: 18px;
            font-weight: 700;
            color: {TEXT};
        }}
        QLabel#sectionLabel, QLabel#bold {{
            font-weight: 700;
            color: {TEXT};
        }}
        QLabel#muted {{
            color: {MUTED_TEXT};
        }}
        QLabel#statusLabel {{
            color: {MUTED_TEXT};
            background: {PANEL_BG};
            border: 1px solid {SOFT_BORDER};
            border-radius: 6px;
            padding: 6px 8px;
        }}
        QMenuBar {{
            background: {PANEL_BG};
            color: {TEXT};
            border-bottom: 1px solid {SOFT_BORDER};
            padding: 2px;
            min-height: 24px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 5px 10px;
            border-radius: 4px;
        }}
        QMenuBar::item:selected, QMenuBar::item:pressed {{
            background: {BUTTON_HOVER_BG};
            color: {TEXT};
        }}
        QMenu {{
            background: {PANEL_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            background: transparent;
            color: {TEXT};
            padding: 6px 30px 6px 14px;
            min-height: 20px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background: {SELECTION_BG};
            color: {TEXT};
        }}
        QMenu::item:disabled {{
            color: {DISABLED_TEXT};
        }}
        QMenu::separator {{
            height: 1px;
            background: {SOFT_BORDER};
            margin: 4px 6px;
        }}
        QToolTip {{
            background: {PANEL_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 6px 8px;
        }}
        QPushButton {{
            background: {BUTTON_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 7px 12px;
            min-height: 18px;
        }}
        QPushButton:hover {{
            background: {BUTTON_HOVER_BG};
            border: 1px solid {ACCENT};
        }}
        QPushButton:pressed {{
            background: {BUTTON_PRESSED_BG};
            border: 1px solid {SOFT_BORDER};
        }}
        QPushButton:disabled {{
            background: {BUTTON_PRESSED_BG};
            color: {DISABLED_TEXT};
            border: 1px solid {SOFT_BORDER};
        }}
        QPushButton#helpButton {{
            background: {BUTTON_BG};
            color: {MUTED_TEXT};
            border: 1px solid {BORDER};
            border-radius: 11px;
            padding: 0;
            min-height: 0;
            font-weight: 700;
        }}
        QPushButton#helpButton:hover {{
            background: {BUTTON_HOVER_BG};
            color: {TEXT};
        }}
        QPushButton#helpButton:pressed {{
            background: {BUTTON_PRESSED_BG};
        }}
        QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
            background: {INPUT_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: {SELECTION_BG};
            selection-color: {TEXT};
        }}
        QLineEdit:hover, QComboBox:hover, QTextEdit:hover, QPlainTextEdit:hover,
        QSpinBox:hover, QDoubleSpinBox:hover {{
            border: 1px solid {ACCENT};
        }}
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {ACCENT};
            background: {INPUT_BG};
        }}
        QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled,
        QSpinBox:disabled, QDoubleSpinBox:disabled {{
            background: {PANEL_BG};
            color: {DISABLED_TEXT};
            border: 1px solid {SOFT_BORDER};
        }}
        QLineEdit, QComboBox {{
            min-height: 20px;
        }}
        QTextEdit:read-only, QPlainTextEdit:read-only {{
            background: {INPUT_BG};
            color: {TEXT};
        }}
        QComboBox {{
            padding: 6px 34px 6px 8px;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid {BORDER};
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
            background: {BUTTON_BG};
        }}
        QComboBox::drop-down:hover {{
            background: {BUTTON_HOVER_BG};
        }}
        QComboBox QAbstractItemView, QListView, QListWidget, QTreeView, QTreeWidget, QTableView, QTableWidget {{
            background: {INPUT_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            selection-background-color: {SELECTION_BG};
            selection-color: {TEXT};
            outline: 0;
            padding: 4px;
        }}
        QAbstractItemView::item {{
            min-height: 22px;
            padding: 4px 8px;
            color: {TEXT};
        }}
        QAbstractItemView::item:selected {{
            background: {SELECTION_BG};
            color: {TEXT};
        }}
        QAbstractItemView::item:disabled {{
            color: {DISABLED_TEXT};
        }}
        QHeaderView::section {{
            background: {PANEL_BG};
            color: {TEXT};
            border: 1px solid {SOFT_BORDER};
            padding: 5px 8px;
        }}
        QCheckBox, QRadioButton {{
            background: transparent;
            color: {TEXT};
            spacing: 8px;
            padding: 4px 0;
            min-height: 20px;
            border: none;
        }}
        QCheckBox:disabled, QRadioButton:disabled {{
            color: {DISABLED_TEXT};
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {BORDER};
            background: {INPUT_BG};
        }}
        QCheckBox::indicator {{
            border-radius: 4px;
        }}
        QRadioButton::indicator {{
            border-radius: 8px;
        }}
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border: 1px solid {ACCENT};
            background: {BUTTON_HOVER_BG};
        }}
        QCheckBox::indicator:checked {{
            background: {SELECTION_BG};
            border: 1px solid {ACCENT};
        }}
        QRadioButton::indicator:checked {{
            background: {SELECTION_BG};
            border: 4px solid {INPUT_BG};
        }}
        QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
            background: {PANEL_BG};
            border: 1px solid {SOFT_BORDER};
        }}
        QTabWidget::pane {{
            background: {PANEL_BG};
            border: 1px solid {BORDER};
            border-radius: 6px;
            top: -1px;
        }}
        QTabBar::tab {{
            background: {INACTIVE_TAB_BG};
            color: {MUTED_TEXT};
            border: 1px solid {SOFT_BORDER};
            padding: 7px 12px;
            min-width: 80px;
        }}
        QTabBar::tab:selected {{
            background: {PANEL_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
        }}
        QTabBar::tab:hover:!selected {{
            background: {BUTTON_HOVER_BG};
            color: {TEXT};
        }}
        QProgressBar {{
            background: {INPUT_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            text-align: center;
            min-height: 14px;
        }}
        QProgressBar::chunk {{
            background: {PROGRESS_BG};
            border-radius: 5px;
        }}
        QScrollBar:vertical {{
            background: {PANEL_BG};
            width: 12px;
            margin: 0;
            border: none;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background: {BUTTON_BG};
            min-height: 24px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {BUTTON_HOVER_BG};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            border: none;
            background: transparent;
        }}
        QScrollBar:horizontal {{
            background: {PANEL_BG};
            height: 12px;
            margin: 0;
            border: none;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background: {BUTTON_BG};
            min-width: 24px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {BUTTON_HOVER_BG};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
            border: none;
            background: transparent;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {INPUT_BG};
            border: 1px solid {SOFT_BORDER};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {PROGRESS_BG};
            border-radius: 3px;
        }}
        QSlider::add-page:horizontal {{
            background: {INPUT_BG};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {ACCENT};
            border: 1px solid {TEXT};
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {PROGRESS_BG};
        }}
        QSlider::groove:vertical {{
            width: 6px;
            background: {INPUT_BG};
            border: 1px solid {SOFT_BORDER};
            border-radius: 3px;
        }}
        QSlider::sub-page:vertical {{
            background: {INPUT_BG};
            border-radius: 3px;
        }}
        QSlider::add-page:vertical {{
            background: {PROGRESS_BG};
            border-radius: 3px;
        }}
        QSlider::handle:vertical {{
            background: {ACCENT};
            border: 1px solid {TEXT};
            width: 16px;
            height: 16px;
            margin: 0 -6px;
            border-radius: 8px;
        }}
        QSlider::handle:vertical:hover {{
            background: {PROGRESS_BG};
        }}
        QGroupBox {{
            background: {PANEL_BG};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            margin-top: 12px;
            padding: 8px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            color: {MUTED_TEXT};
            background: {PANEL_BG};
        }}
        QStatusBar {{
            background: {PANEL_BG};
            color: {MUTED_TEXT};
            border-top: 1px solid {SOFT_BORDER};
        }}
    """


def apply_app_theme(app):
    qdarktheme.setup_theme("dark")
    base_stylesheet = app.styleSheet()

    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(WINDOW_BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(INPUT_BG))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(PANEL_BG))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(PANEL_BG))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(BUTTON_BG))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTED_TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(SELECTION_BG))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(TEXT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(DISABLED_TEXT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(DISABLED_TEXT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(DISABLED_TEXT))
    app.setPalette(palette)
    app.setStyleSheet(f"{base_stylesheet}\n{build_theme_stylesheet()}")

os.environ["HF_HOME"] = MODEL_DIR
os.environ["HF_HUB_CACHE"] = MODEL_DIR
os.environ["TRANSFORMERS_CACHE"] = MODEL_DIR
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

disable_progress_bars()


class StateValue:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def set_window_icon(window):
    if os.path.exists(APP_ICON_PATH):
        window.setWindowIcon(QIcon(APP_ICON_PATH))


class FunctionWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    def run(self):
        try:
            self.function()
        except Exception as err:
            self.error.emit(f"Error: {err}")
        finally:
            self.finished.emit()


class DropLineEdit(QLineEdit):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()


class DropWidget(QWidget):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.file_dropped.emit(urls[0].toLocalFile())
            event.acceptProposedAction()


class OutputConflictDialog(QDialog):
    def __init__(self, parent, file_path):
        super().__init__(parent)
        self.choice = None
        self.file_path = file_path

        self.setWindowTitle("Output File Exists")
        set_window_icon(self)
        self.setFixedSize(520, 220)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        prompt = QLabel(
            "The output file already exists.\n\n"
            f"{os.path.basename(file_path)}\n\n"
            "Do you want to overwrite it, create a renamed copy, or cancel?"
        )
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

        button_row = QHBoxLayout()
        overwrite_btn = QPushButton("Overwrite")
        rename_btn = QPushButton("Rename")
        cancel_btn = QPushButton("Cancel")
        overwrite_btn.clicked.connect(lambda: self.finish("overwrite"))
        rename_btn.clicked.connect(lambda: self.finish("rename"))
        cancel_btn.clicked.connect(lambda: self.finish("cancel"))
        button_row.addWidget(overwrite_btn)
        button_row.addWidget(rename_btn)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)

    def finish(self, choice):
        self.choice = choice
        self.accept()

    def reject(self):
        self.choice = "cancel"
        super().reject()


class InfoDialog(QDialog):
    """A themed info dialog that matches the app's dark theme."""

    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.setWindowTitle(title)
        set_window_icon(self)
        self.setModal(True)
        self.resize(*self.get_dialog_size(text, parent))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        shell = QFrame()
        shell.setObjectName("card")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(10)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(text)
        shell_layout.addWidget(body, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        shell_layout.addLayout(close_row)

        layout.addWidget(shell)

    def get_dialog_size(self, text, parent):
        line_count = text.count("\n") + 1
        width = 560
        screen_height = parent.screen().availableGeometry().height()
        height = min(max(260, 150 + (line_count * 18)), int(screen_height * 0.75))
        return width, height


class AdvancedOptionsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setWindowTitle("Advanced Options")
        set_window_icon(self)
        self.setFixedSize(640, 340)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(0)

        shell = QFrame()
        shell.setObjectName("card")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(18, 16, 18, 16)
        shell_layout.setSpacing(10)

        title = QLabel("Advanced Options")
        title.setObjectName("title")
        shell_layout.addWidget(title)

        info_label = QLabel("A few expert controls for troubleshooting accuracy and pacing.")
        info_label.setObjectName("muted")
        shell_layout.addWidget(info_label)

        container = QFrame()
        container.setObjectName("innerCard")
        container_layout = QGridLayout(container)
        container_layout.setContentsMargins(18, 14, 18, 14)
        container_layout.setHorizontalSpacing(12)
        container_layout.setVerticalSpacing(10)

        self.beam_size_menu = self.add_option_row(
            container_layout,
            row=0,
            title="Beam Size",
            help_text="Beam size controls how many candidate transcriptions Whisper explores. Higher values usually help difficult audio, but increase processing time.",
            values=["1", "3", "5", "8", "10"],
            variable=parent.beam_size,
        )
        self.no_speech_menu = self.add_option_row(
            container_layout,
            row=1,
            title="No Speech Threshold",
            help_text="Higher values make Whisper more likely to skip quiet or uncertain sections. Lower values keep more borderline speech, which can help with soft voices but may add junk captions.",
            values=["0.3", "0.6", "0.8", "1.0"],
            variable=parent.no_speech_threshold,
        )
        self.add_switch_row(
            container_layout,
            row=2,
            title="Condition On Previous Text",
            help_text="When enabled, the model uses previous text as context for the next chunk. This can improve continuity, but sometimes carries mistakes forward.",
            variable=parent.condition_on_previous_text,
        )
        shell_layout.addWidget(container)

        footer_note = QLabel("Defaults are usually the best choice for normal subtitle generation.")
        footer_note.setObjectName("muted")
        shell_layout.addWidget(footer_note)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        reset_button = QPushButton("Reset Defaults")
        close_button = QPushButton("Close")
        reset_button.clicked.connect(self.reset_defaults)
        close_button.clicked.connect(self.accept)
        button_row.addWidget(reset_button)
        button_row.addWidget(close_button)
        shell_layout.addLayout(button_row)

        layout.addWidget(shell)

    def add_option_row(self, layout, row, title, help_text, values, variable):
        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)
        label_row.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("bold")
        help_button = QPushButton("?")
        help_button.setObjectName("helpButton")
        help_button.setToolTip(help_text)
        help_button.setFixedSize(22, 22)
        label_row.addWidget(title_label)
        label_row.addWidget(help_button)
        label_row.addStretch(1)
        layout.addLayout(label_row, row, 0)

        option_menu = QComboBox()
        option_menu.addItems(values)
        option_menu.setCurrentText(self.format_option_value(variable.get()))
        option_menu.currentTextChanged.connect(lambda selected, var=variable: self.on_option_change(var, selected))
        option_menu.setFixedWidth(120)
        layout.addWidget(option_menu, row, 1, alignment=Qt.AlignmentFlag.AlignVCenter)
        return option_menu

    def add_switch_row(self, layout, row, title, help_text, variable):
        label_row = QHBoxLayout()
        label_row.setContentsMargins(0, 0, 0, 0)
        label_row.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("bold")
        help_button = QPushButton("?")
        help_button.setObjectName("helpButton")
        help_button.setToolTip(help_text)
        help_button.setFixedSize(22, 22)
        label_row.addWidget(title_label)
        label_row.addWidget(help_button)
        label_row.addStretch(1)
        layout.addLayout(label_row, row, 0)

        toggle = QCheckBox()
        toggle.setChecked(bool(variable.get()))
        toggle.toggled.connect(variable.set)
        layout.addWidget(toggle, row, 1, alignment=Qt.AlignmentFlag.AlignRight)

    def format_option_value(self, value):
        if isinstance(value, float):
            return f"{value:.1f}"
        return str(value)

    def on_option_change(self, variable, selected_value):
        current_value = variable.get()
        if isinstance(current_value, float):
            variable.set(float(selected_value))
        else:
            variable.set(int(selected_value))

    def reset_defaults(self):
        defaults = self.parent.get_default_advanced_settings()
        self.parent.beam_size.set(defaults["beam_size"])
        self.parent.no_speech_threshold.set(defaults["no_speech_threshold"])
        self.parent.condition_on_previous_text.set(defaults["condition_on_previous_text"])
        self.accept()
        self.parent.open_advanced_options()


class WhisperApp(QMainWindow):
    log_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        set_window_icon(self)
        self.setWindowTitle(APP_NAME)
        self.resize(900, 600)
        self.setMinimumSize(900, 600)

        self.input_path = StateValue("")
        self.output_path = StateValue("")
        self.model_name = StateValue("small")
        self.model_display = StateValue("")
        self.use_word_timestamps = StateValue(True)
        self.remove_punctuation = StateValue(False)
        self.text_case = StateValue("Normal")
        self.language_display = StateValue("")
        self.max_words_per_subtitle = StateValue("8")
        self.max_chars_per_line = StateValue("42")
        self.beam_size = StateValue(5)
        self.no_speech_threshold = StateValue(0.8)
        self.condition_on_previous_text = StateValue(False)
        self.preset = StateValue("Normal")
        self.pause_threshold = StateValue(0.5)
        self.max_subtitle_duration = StateValue(3.2)
        self.vad_silence_ms = StateValue(700)
        self.break_on_punctuation_immediate = StateValue(False)

        self.available_models = ["tiny", "base", "small", "medium", "large-v3"]
        self.model_display_map = {}
        self.installed_models = set()
        self.spinner_frames = ["|", "/", "-", "\\"]
        self.spinner_index = 0
        self.spinner_message = "Idle"
        self.advanced_dialog = None
        self.worker_threads = []
        self.language_display_map = {
            f"{SUPPORTED_LANGUAGE_NAMES[code]} ({code})": code for code in sorted(
                SUPPORTED_LANGUAGE_NAMES,
                key=lambda code: SUPPORTED_LANGUAGE_NAMES[code].lower()
            )
        }

        self.is_downloading = False
        self.is_transcribing = False

        self.spinner_timer = QTimer(self)
        self.spinner_timer.setInterval(120)
        self.spinner_timer.timeout.connect(self.schedule_spinner)
        self.log_requested.connect(self._append_log)

        self.build_menu_bar()
        self.build_ui()

    def build_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        options_menu = menu_bar.addMenu("Options")
        advanced_action = QAction("Advanced Options", self)
        advanced_action.triggered.connect(self.open_advanced_options)
        options_menu.addAction(advanced_action)

        help_menu = menu_bar.addMenu("Help")
        best_accuracy_action = QAction("Best Accuracy Settings", self)
        best_accuracy_action.triggered.connect(self.show_best_accuracy_info)
        accuracy_tips_action = QAction("Accuracy Tips", self)
        accuracy_tips_action.triggered.connect(self.show_accuracy_tips)
        supported_formats_action = QAction("Supported Formats", self)
        supported_formats_action.triggered.connect(self.show_supported_formats)
        credits_action = QAction("Credits", self)
        credits_action.triggered.connect(self.show_credits_info)
        help_menu.addAction(best_accuracy_action)
        help_menu.addAction(accuracy_tips_action)
        help_menu.addSeparator()
        help_menu.addAction(supported_formats_action)
        help_menu.addAction(credits_action)

    def show_best_accuracy_info(self):
        InfoDialog(
            self,
            "Best Accuracy Settings",
            (
                "Best overall setup:\n"
                "Model: large-v3\n"
                "Beam Size: 5 (default)\n"
                "No Speech Threshold: 0.8 (default)\n"
                "Condition On Previous Text: Off (default)\n"
                "\n"
                "For difficult audio (accents, background noise):\n"
                "- Raise Beam Size to 8-10 (slower but more thorough)\n"
                "- Lower No Speech Threshold to 0.6 (keeps more speech)\n"
                "- Turn Context On (helps continuity)\n"
                "\n"
                "Note: There's no single 'best' setting - it depends on your audio.\n"
                "The defaults work well for most clean recordings."
            )
        ).exec()

    def show_accuracy_tips(self):
        InfoDialog(
            self,
            "Accuracy Tips",
            (
                "Common issues and what to try:\n"
                "\n"
                "- Missing words or quiet speech:\n"
                "  Lower No Speech Threshold to 0.6 (keeps more audio)\n"
                "\n"
                "- Jumbled or hallucinated words:\n"
                "  Raise No Speech Threshold to 1.0 (stricter filtering)\n"
                "\n"
                "- Repetitive or stuck phrases:\n"
                "  Turn Context Off if it's on\n"
                "\n"
                "- Heavy accents or noisy audio:\n"
                "  Raise Beam Size to 8-10\n"
                "\n"
                "Tradeoffs:\n"
                "- large-v3 is the most accurate model overall.\n"
                "- Higher Beam Size is significantly slower on CPU.\n"
                "- Lower No Speech Threshold keeps more speech but may add junk.\n"
                "- Context helps continuity but can carry mistakes forward."
            )
        ).exec()

    def show_supported_formats(self):
        InfoDialog(
            self,
            "Supported Formats",
            (
                "Audio: mp3, wav, m4a, flac, aac, ogg, wma\n"
                "Video: mp4, mkv, mov, avi, webm, mpeg, mpg, m4v\n"
                "\n"
                "You can also drag and drop supported files.\n"
                "Actual support depends on the decoding libraries included in the build."
            )
        ).exec()

    def show_credits_info(self):
        InfoDialog(
            self,
            "Credits",
            (
                "This app uses open-source software, including:\n"
                "- PyQt6\n"
                "- faster-whisper\n"
                "- CTranslate2\n"
                "- huggingface_hub\n"
                "- PyAV\n"
                "- NumPy\n"
                "- tokenizers\n"
                "- tqdm\n"
                "\n"
                "For redistribution, include THIRD_PARTY_NOTICES.md with the app."
            )
        ).exec()

    def build_ui(self):
        central = DropWidget()
        central.setObjectName("centralWidget")
        central.file_dropped.connect(self.handle_file_drop)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(10)

        file_frame = QFrame()
        file_layout = QGridLayout(file_frame)
        file_layout.setContentsMargins(12, 10, 12, 10)
        file_layout.setHorizontalSpacing(10)
        file_layout.setVerticalSpacing(8)

        self.input_btn = QPushButton("Input")
        self.input_btn.clicked.connect(self.pick_input)
        file_layout.addWidget(self.input_btn, 0, 0)

        self.input_entry = DropLineEdit()
        self.input_entry.setText(self.input_path.get())
        self.input_entry.textChanged.connect(self.input_path.set)
        self.input_entry.file_dropped.connect(self.handle_file_drop)
        file_layout.addWidget(self.input_entry, 0, 1)

        self.output_btn = QPushButton("Output")
        self.output_btn.clicked.connect(self.pick_output)
        file_layout.addWidget(self.output_btn, 1, 0)

        self.output_entry = QLineEdit()
        self.output_entry.setText(self.output_path.get())
        self.output_entry.textChanged.connect(self.output_path.set)
        file_layout.addWidget(self.output_entry, 1, 1)
        file_layout.setColumnStretch(1, 1)
        root.addWidget(file_frame)

        preset_frame = QFrame()
        preset_layout = QHBoxLayout(preset_frame)
        preset_layout.setContentsMargins(16, 8, 16, 8)
        preset_layout.setSpacing(10)
        preset_label = QLabel("Preset")
        preset_label.setObjectName("bold")
        preset_layout.addWidget(preset_label)
        self.preset_menu = QComboBox()
        self.preset_menu.addItems(["Normal", "TikTok"])
        self.preset_menu.setCurrentText(self.preset.get())
        self.preset_menu.currentTextChanged.connect(self.on_preset_changed)
        self.preset_menu.setFixedWidth(120)
        preset_layout.addWidget(self.preset_menu)
        preset_layout.addStretch(1)
        root.addWidget(preset_frame)

        options_frame = QFrame()
        options_layout = QGridLayout(options_frame)
        options_layout.setContentsMargins(12, 12, 12, 12)
        options_layout.setHorizontalSpacing(10)
        options_layout.setVerticalSpacing(10)

        model_frame = QFrame()
        model_layout = QVBoxLayout(model_frame)
        model_layout.setContentsMargins(12, 12, 12, 12)
        model_layout.setSpacing(8)
        self.model_section_label = QLabel("Model")
        self.model_section_label.setObjectName("sectionLabel")
        model_layout.addWidget(self.model_section_label)
        self.model_menu = QComboBox()
        self.model_menu.currentTextChanged.connect(self.on_model_selected)
        model_layout.addWidget(self.model_menu)
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download_model)
        model_layout.addWidget(self.download_btn)
        self.delete_btn = QPushButton("Delete Model")
        self.delete_btn.clicked.connect(self.delete_model)
        model_layout.addWidget(self.delete_btn)
        model_layout.addStretch(1)
        options_layout.addWidget(model_frame, 0, 0)

        timing_frame = QFrame()
        timing_layout = QGridLayout(timing_frame)
        timing_layout.setContentsMargins(12, 12, 12, 12)
        timing_layout.setHorizontalSpacing(10)
        timing_layout.setVerticalSpacing(8)
        self.timing_section_label = QLabel("Timing")
        self.timing_section_label.setObjectName("sectionLabel")
        timing_layout.addWidget(self.timing_section_label, 0, 0, 1, 2)
        self.word_timestamps_checkbox = QCheckBox("Word-level subtitle timing")
        self.word_timestamps_checkbox.setChecked(self.use_word_timestamps.get())
        self.word_timestamps_checkbox.toggled.connect(self.use_word_timestamps.set)
        timing_layout.addWidget(self.word_timestamps_checkbox, 1, 0, 1, 2)
        self.max_words_label = QLabel("Max words")
        timing_layout.addWidget(self.max_words_label, 2, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.max_words_entry = QLineEdit(self.max_words_per_subtitle.get())
        self.max_words_entry.textChanged.connect(self.max_words_per_subtitle.set)
        timing_layout.addWidget(self.max_words_entry, 2, 1)
        self.max_chars_label = QLabel("Max chars/line")
        timing_layout.addWidget(self.max_chars_label, 3, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.max_chars_entry = QLineEdit(self.max_chars_per_line.get())
        self.max_chars_entry.textChanged.connect(self.max_chars_per_line.set)
        timing_layout.addWidget(self.max_chars_entry, 3, 1)
        timing_layout.setColumnStretch(1, 1)
        options_layout.addWidget(timing_frame, 0, 1)

        text_frame = QFrame()
        text_layout = QGridLayout(text_frame)
        text_layout.setContentsMargins(12, 12, 12, 12)
        text_layout.setHorizontalSpacing(10)
        text_layout.setVerticalSpacing(8)
        self.text_section_label = QLabel("Text")
        self.text_section_label.setObjectName("sectionLabel")
        text_layout.addWidget(self.text_section_label, 0, 0, 1, 2)
        self.remove_punctuation_checkbox = QCheckBox("Remove punctuation")
        self.remove_punctuation_checkbox.setChecked(self.remove_punctuation.get())
        self.remove_punctuation_checkbox.toggled.connect(self.remove_punctuation.set)
        text_layout.addWidget(self.remove_punctuation_checkbox, 1, 0, 1, 2)
        self.text_case_label = QLabel("Text case")
        text_layout.addWidget(self.text_case_label, 2, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.text_case_menu = QComboBox()
        self.text_case_menu.addItems(["Normal", "lowercase", "UPPERCASE"])
        self.text_case_menu.setCurrentText(self.text_case.get())
        self.text_case_menu.currentTextChanged.connect(self.text_case.set)
        text_layout.addWidget(self.text_case_menu, 2, 1)
        self.language_label = QLabel("Language")
        text_layout.addWidget(self.language_label, 3, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        language_values = list(self.language_display_map.keys())
        english_display = next(display for display, code in self.language_display_map.items() if code == "en")
        self.language_display.set(english_display)
        self.language_menu = QComboBox()
        self.language_menu.addItems(language_values)
        self.language_menu.setCurrentText(english_display)
        self.language_menu.currentTextChanged.connect(self.language_display.set)
        text_layout.addWidget(self.language_menu, 3, 1)
        text_layout.setColumnStretch(1, 1)
        options_layout.addWidget(text_frame, 0, 2)

        options_layout.setColumnStretch(0, 1)
        options_layout.setColumnStretch(1, 1)
        options_layout.setColumnStretch(2, 1)
        root.addWidget(options_frame)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self.download_status_label = QLabel("Idle")
        self.download_status_label.setObjectName("statusLabel")
        self.download_status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        status_row.addWidget(self.download_status_label)
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setFixedWidth(120)
        self.generate_btn.clicked.connect(self.start_transcription)
        status_row.addWidget(self.generate_btn)
        root.addLayout(status_row)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        root.addWidget(self.log_box, 1)

        self.refresh_model_menu()

    def _append_log(self, text):
        self.log_box.append(text)
        self.log_box.moveCursor(self.log_box.textCursor().MoveOperation.End)

    def log(self, text):
        self.log_requested.emit(text)

    def run_in_worker(self, function, finished_callback=None):
        thread = QThread(self)
        worker = FunctionWorker(function)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.error.connect(self.log)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        def cleanup():
            self.worker_threads = [item for item in self.worker_threads if item[0] is not thread]
            if finished_callback:
                finished_callback()

        thread.finished.connect(cleanup)
        self.worker_threads.append((thread, worker))
        thread.start()

    def on_preset_changed(self, choice):
        self.preset.set(choice)
        if choice == "Normal":
            self.pause_threshold.set(0.5)
            self.max_subtitle_duration.set(3.2)
            self.vad_silence_ms.set(700)
            self.break_on_punctuation_immediate.set(False)
            self.log("Preset: Normal - balanced subtitle pacing.")
        elif choice == "TikTok":
            self.pause_threshold.set(0.5)
            self.max_subtitle_duration.set(2.0)
            self.vad_silence_ms.set(500)
            self.break_on_punctuation_immediate.set(True)
            self.log("Preset: TikTok - faster subtitle pacing for short-form video.")

    def handle_file_drop(self, path):
        if not path or not os.path.isfile(path):
            self.log("Drop a file onto the input field or app window.")
            return

        self.set_input_file(path)

    def set_busy_controls_disabled(self, disabled):
        for widget in (
            self.input_btn,
            self.input_entry,
            self.output_btn,
            self.output_entry,
            self.preset_menu,
            self.download_btn,
            self.generate_btn,
            self.delete_btn,
            self.model_menu,
            self.word_timestamps_checkbox,
            self.remove_punctuation_checkbox,
            self.text_case_menu,
            self.language_menu,
            self.max_words_entry,
            self.max_chars_entry,
        ):
            widget.setDisabled(disabled)
        self.menuBar().setDisabled(disabled)
        if self.advanced_dialog is not None and self.advanced_dialog.isVisible():
            self.advanced_dialog.setDisabled(disabled)

    def set_download_state(self, active, model_name=None):
        if active:
            self.start_status_spinner(f"Downloading {model_name}...")
        else:
            self.stop_status_spinner()

        self.set_busy_controls_disabled(bool(active))

    def start_status_spinner(self, message):
        self.spinner_message = message
        self.spinner_index = 0
        self.download_status_label.setText(f"{self.spinner_frames[self.spinner_index]} {self.spinner_message}")
        self.spinner_timer.start()

    def stop_status_spinner(self):
        self.spinner_timer.stop()
        self.spinner_message = "Idle"
        self.download_status_label.setText("Idle")

    def schedule_spinner(self):
        if not self.is_downloading and not self.is_transcribing:
            self.spinner_timer.stop()
            return

        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        self.download_status_label.setText(f"{self.spinner_frames[self.spinner_index]} {self.spinner_message}")

    def set_transcription_state(self, active):
        self.is_transcribing = active
        if active:
            self.start_status_spinner("Transcribing...")
        else:
            self.stop_status_spinner()

        self.set_busy_controls_disabled(bool(active))

    def get_default_advanced_settings(self):
        return {
            "beam_size": 5,
            "no_speech_threshold": 0.8,
            "condition_on_previous_text": False,
        }

    def open_advanced_options(self):
        if self.advanced_dialog is not None and self.advanced_dialog.isVisible():
            self.advanced_dialog.raise_()
            self.advanced_dialog.activateWindow()
            return

        self.advanced_dialog = AdvancedOptionsDialog(self)
        self.advanced_dialog.finished.connect(self.on_advanced_dialog_destroy)
        self.advanced_dialog.show()

    def on_advanced_dialog_destroy(self):
        self.advanced_dialog = None

    def get_repo_id(self, model_name):
        return f"{MODEL_REPO_PREFIX}{model_name}"

    def get_model_dir(self, model_name):
        return os.path.join(MODEL_DIR, model_name)

    def get_model_cache_path(self, model_name):
        safe_repo_name = self.get_repo_id(model_name).replace("/", "--")
        return os.path.join(MODEL_DIR, f"models--{safe_repo_name}")

    def has_model_files(self, model_path):
        return os.path.isfile(os.path.join(model_path, "model.bin"))

    def get_legacy_snapshot_path(self, model_name):
        repo_cache_path = self.get_model_cache_path(model_name)
        snapshots_path = os.path.join(repo_cache_path, "snapshots")
        if not os.path.isdir(snapshots_path):
            return None

        try:
            for entry in os.scandir(snapshots_path):
                if entry.is_dir() and self.has_model_files(entry.path):
                    return entry.path
        except OSError:
            return None

        return None

    def get_model_load_path(self, model_name):
        model_dir = self.get_model_dir(model_name)
        if self.has_model_files(model_dir):
            return model_dir

        legacy_snapshot_path = self.get_legacy_snapshot_path(model_name)
        if legacy_snapshot_path:
            return legacy_snapshot_path

        return None

    def detect_installed_models(self):
        installed_models = set()

        for model_name in self.available_models:
            if self.get_model_load_path(model_name):
                installed_models.add(model_name)

        self.installed_models = installed_models

    def get_model_display_name(self, model_name):
        marker = "✓" if model_name in self.installed_models else "x"
        return f"{marker} {model_name}"

    def refresh_model_menu(self):
        self.detect_installed_models()
        current_model = self.model_name.get()
        display_values = [self.get_model_display_name(model) for model in self.available_models]
        self.model_display_map = dict(zip(display_values, self.available_models))

        self.model_menu.blockSignals(True)
        self.model_menu.clear()
        self.model_menu.addItems(display_values)
        selected_display = next(
            (display for display, model in self.model_display_map.items() if model == current_model),
            display_values[0]
        )
        self.model_menu.setCurrentText(selected_display)
        self.model_menu.blockSignals(False)

        self.model_display.set(selected_display)
        self.model_name.set(self.model_display_map[selected_display])

    def on_model_selected(self, selected_display):
        model_name = self.model_display_map.get(selected_display)
        if model_name:
            self.model_display.set(selected_display)
            self.model_name.set(model_name)

    def set_input_file(self, path):
        self.input_path.set(path)
        self.output_path.set(os.path.dirname(path))
        self.input_entry.setText(path)
        self.output_entry.setText(self.output_path.get())
        self.log(f"Selected input file: {os.path.basename(path)}")
        self.log(f"Output folder set to: {self.output_path.get()}")

    def pick_input(self):
        filter_text = (
            "Supported media (" + " ".join(f"*{ext}" for ext in SUPPORTED_MEDIA_EXTENSIONS) + ");;"
            "Audio files (*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma);;"
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.mpeg *.mpg *.m4v);;"
            "All files (*.*)"
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input File",
            "",
            filter_text,
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self.set_input_file(path)

    def pick_output(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self.output_path.set(path)
            self.output_entry.setText(path)

    # REAL DETECTION (load test)
    def model_exists(self, model_name):
        if not self.installed_models:
            self.detect_installed_models()
        return model_name in self.installed_models

    # DOWNLOAD
    def download_model(self):
        if self.is_downloading:
            self.log("Download already in progress ⏳")
            return

        model_name = self.model_name.get()

        if self.model_exists(model_name):
            self.log(f"{model_name} already installed ✅")
            return

        self.is_downloading = True
        self.set_download_state(True, model_name)

        self.log(f"Downloading {model_name}...")
        self.run_in_worker(lambda: self._download_worker(model_name), self.finish_download)

    def _download_worker(self, model_name):
        try:
            model_dir = self.get_model_dir(model_name)
            snapshot_download(
                repo_id=self.get_repo_id(model_name),
                local_dir=model_dir,
                max_workers=1,
                tqdm_class=None,
            )

            self.log(f"{model_name} installed ✅")
            self.log(f"Downloaded to: {model_dir}")

        except Exception as err:
            self.log(f"Error: {err}")

    def finish_download(self):
        self.refresh_model_menu()
        self.is_downloading = False
        self.set_download_state(False)

    # SAFE DELETE
    def force_delete(self, path):
        def onerror(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        shutil.rmtree(path, onerror=onerror)

    def delete_model(self):
        if self.is_downloading:
            self.log("Cannot delete while downloading ❌")
            return

        model_name = self.model_name.get()
        model_dir = self.get_model_dir(model_name)
        repo_cache_path = self.get_model_cache_path(model_name)
        deleted = False

        if os.path.isdir(model_dir):
            self.force_delete(model_dir)
            deleted = True

        if os.path.isdir(repo_cache_path):
            self.force_delete(repo_cache_path)
            deleted = True

        # Clean up older flat-file downloads created by previous versions.
        legacy_files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
        legacy_deleted = False
        for file_name in legacy_files:
            file_path = os.path.join(MODEL_DIR, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                legacy_deleted = True

        deleted = deleted or legacy_deleted

        if deleted:
            self.refresh_model_menu()
            self.log(f"{model_name} deleted ❌")
        else:
            self.log("Model not found")

    def start_transcription(self):
        input_path = self.input_path.get().strip()
        output_path = self.output_path.get().strip()
        model_name = self.model_name.get()
        subtitle_settings = self.get_subtitle_settings()

        if subtitle_settings is None:
            return

        if not input_path or not os.path.isfile(input_path):
            self.log("Pick a valid input audio/video file.")
            return

        if not output_path or not os.path.isdir(output_path):
            self.log("Pick a valid output folder.")
            return

        if not self.model_exists(model_name):
            self.log(f"{model_name} is not installed. Download it first.")
            return

        output_file = self.resolve_output_file_path(output_path)
        if output_file is None:
            self.log("Transcription cancelled.")
            return

        model_path = self.get_model_load_path(model_name)
        if not model_path:
            self.log(f"{model_name} is not installed. Download it first.")
            return

        subtitle_settings["output_file"] = output_file
        subtitle_settings["model_name"] = model_name
        subtitle_settings["model_path"] = model_path
        subtitle_settings["input_path"] = input_path
        subtitle_settings["pause_threshold"] = self.pause_threshold.get()
        subtitle_settings["max_subtitle_duration"] = self.max_subtitle_duration.get()
        subtitle_settings["vad_silence_ms"] = self.vad_silence_ms.get()
        subtitle_settings["break_on_punctuation_immediate"] = self.break_on_punctuation_immediate.get()

        self.set_transcription_state(True)
        self.log(f"Starting transcription with {model_name}...")
        self.log(f"Input: {os.path.basename(input_path)}")
        self.log(
            f"Options: word timing={'on' if subtitle_settings['use_word_timestamps'] else 'off'}, "
            f"max words={subtitle_settings['max_words']}, max chars={subtitle_settings['max_chars']}, "
            f"punctuation={'off' if subtitle_settings['remove_punctuation'] else 'on'}, "
            f"language={subtitle_settings['language_code']}, "
            f"case={subtitle_settings['text_case']}, beam={subtitle_settings['beam_size']}, "
            f"no-speech={subtitle_settings['no_speech_threshold']:.1f}, "
            f"context={'on' if subtitle_settings['condition_on_previous_text'] else 'off'}"
        )
        self.log(f"Output: {output_file}")
        self.run_in_worker(lambda: self.run_whisper(subtitle_settings), lambda: self.set_transcription_state(False))

    def run_whisper(self, subtitle_settings):
        try:
            model_name = subtitle_settings["model_name"]
            model_path = subtitle_settings["model_path"]
            if not model_path:
                self.log(f"{model_name} is not installed. Download it first.")
                return

            model = WhisperModel(
                model_path,
                compute_type="int8",
                device="cpu",
                local_files_only=True,
            )
            self.log("Model loaded. Processing audio...")

            use_word_timestamps = subtitle_settings["use_word_timestamps"]
            segments, _ = model.transcribe(
                subtitle_settings["input_path"],
                language=subtitle_settings["language_code"],
                beam_size=subtitle_settings["beam_size"],
                best_of=5,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=subtitle_settings["no_speech_threshold"],
                condition_on_previous_text=subtitle_settings["condition_on_previous_text"],
                word_timestamps=use_word_timestamps,
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": subtitle_settings["vad_silence_ms"],
                    "speech_pad_ms": 200,
                },
            )

            subtitle_segments = self.build_subtitle_segments(segments, subtitle_settings)
            subtitle_segments = self.normalize_subtitle_timings(subtitle_segments)
            self.log(f"Created {len(subtitle_segments)} subtitle segments.")

            output_file = subtitle_settings["output_file"]
            self.write_srt_file(output_file, subtitle_segments)
            self.log(f"Done! Saved {len(subtitle_segments)} subtitles.")

        except Exception as err:
            self.log(f"Error: {err}")

    def resolve_output_file_path(self, output_dir):
        input_name = os.path.splitext(os.path.basename(self.input_path.get().strip()))[0] or "output"
        output_file = os.path.join(output_dir, f"{input_name}.srt")
        if not os.path.exists(output_file):
            return output_file

        choice = self.ask_output_conflict(output_file)
        if choice == "overwrite":
            return output_file
        if choice == "rename":
            return self.get_renamed_output_path(output_file)
        return None

    def ask_output_conflict(self, output_file):
        dialog = OutputConflictDialog(self, output_file)
        dialog.exec()
        return dialog.choice

    def get_renamed_output_path(self, output_file):
        base_name, extension = os.path.splitext(output_file)
        counter = 2
        candidate = f"{base_name}_{counter}{extension}"
        while os.path.exists(candidate):
            counter += 1
            candidate = f"{base_name}_{counter}{extension}"
        return candidate

    def format(self, s):
        ms = int(s * 1000)
        h = ms // 3600000
        ms %= 3600000
        m = ms // 60000
        ms %= 60000
        sec = ms // 1000
        ms %= 1000
        return f"{h:02}:{m:02}:{sec:02},{ms:03}"

    def get_subtitle_settings(self):
        try:
            max_words = int(self.max_words_per_subtitle.get().strip())
            max_chars = int(self.max_chars_per_line.get().strip())
        except ValueError:
            self.log("Max words and max chars/line must be whole numbers.")
            return None

        if max_words <= 0:
            self.log("Max words must be greater than 0.")
            return None

        if max_chars <= 0:
            self.log("Max chars/line must be greater than 0.")
            return None

        beam_size = self.beam_size.get()
        no_speech_threshold = round(float(self.no_speech_threshold.get()), 1)
        language_code = self.language_display_map.get(self.language_display.get())

        if beam_size <= 0:
            self.log("Beam size must be greater than 0.")
            return None

        if not 0.0 <= no_speech_threshold <= 1.0:
            self.log("No speech threshold must be between 0.0 and 1.0.")
            return None

        if not language_code:
            self.log("Pick a valid language.")
            return None

        return {
            "use_word_timestamps": self.use_word_timestamps.get(),
            "remove_punctuation": self.remove_punctuation.get(),
            "text_case": self.text_case.get(),
            "language_code": language_code,
            "max_words": max_words,
            "max_chars": max_chars,
            "beam_size": beam_size,
            "no_speech_threshold": no_speech_threshold,
            "condition_on_previous_text": self.condition_on_previous_text.get(),
        }

    def write_srt_file(self, output_file, subtitle_segments):
        self.log(f"Writing subtitles to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            for i, seg in enumerate(subtitle_segments, start=1):
                f.write(f"{i}\n")
                f.write(f"{self.format(seg['start'])} --> {self.format(seg['end'])}\n")
                f.write(f"{seg['text']}\n\n")
                if i % 25 == 0:
                    self.log(f"Wrote {i} subtitle entries...")

    def build_subtitle_segments(self, segments, subtitle_settings):
        subtitle_segments = []
        for index, segment in enumerate(segments, start=1):
            if subtitle_settings["use_word_timestamps"]:
                word_segments = self.build_word_timed_segments(segment, subtitle_settings)
                if word_segments:
                    subtitle_segments.extend(word_segments)
                    if index % 10 == 0:
                        self.log(
                            f"Processed {index} transcription segments, {len(subtitle_segments)} subtitles so far..."
                        )
                    continue

            text = segment.text.strip()
            text = self.format_subtitle_text(text, subtitle_settings)
            if text:
                subtitle_segments.append(
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": text,
                    }
                )
            if index % 10 == 0:
                self.log(f"Processed {index} transcription segments, {len(subtitle_segments)} subtitles so far...")

        return subtitle_segments

    def normalize_subtitle_timings(self, subtitle_segments):
        if not subtitle_segments:
            return []

        normalized_segments = []
        previous_end = 0.0

        for segment in sorted(subtitle_segments, key=lambda item: (item["start"], item["end"])):
            start = max(float(segment["start"]), previous_end)
            end = max(float(segment["end"]), start + 0.25)
            text = segment["text"]

            if normalized_segments:
                gap = start - previous_end
                if gap > 8.0:
                    self.log(
                        f"Large silent gap detected before subtitle {len(normalized_segments) + 1}; re-aligning timing."
                    )

            normalized_segments.append(
                {
                    "start": start,
                    "end": end,
                    "text": text,
                }
            )
            previous_end = end

        return normalized_segments

    def build_word_timed_segments(self, segment, subtitle_settings):
        words = getattr(segment, "words", None) or []
        if not words:
            return []

        subtitle_segments = []
        current_words = []

        for word in words:
            word_text = getattr(word, "word", "").strip()
            word_start = getattr(word, "start", None)
            word_end = getattr(word, "end", None)
            if not word_text or word_start is None or word_end is None:
                continue

            if current_words:
                previous_word_end = getattr(current_words[-1], "end", None)
                if previous_word_end is not None and word_start - previous_word_end >= subtitle_settings["pause_threshold"]:
                    subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                    current_words = []

            current_words.append(word)
            if self.should_break_subtitle(current_words, subtitle_settings):
                subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                current_words = []

        if current_words:
            subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))

        return [segment for segment in subtitle_segments if segment is not None]

    def should_break_subtitle(self, words, subtitle_settings):
        if not words:
            return False

        text = self.join_words(words)
        wrapped_lines = self.wrap_subtitle_lines(text, subtitle_settings)
        duration = words[-1].end - words[0].start
        last_word = words[-1].word.strip()

        if len(words) >= subtitle_settings["max_words"]:
            return True
        if len(wrapped_lines) > 2:
            return True
        if duration >= subtitle_settings["max_subtitle_duration"]:
            return True
        if subtitle_settings["break_on_punctuation_immediate"]:
            if last_word.endswith((".", "!", "?")):
                return True
        elif len(words) >= 3 and last_word.endswith((".", "!", "?", ",")):
            return True

        return False

    def create_subtitle_from_words(self, words, subtitle_settings):
        text = self.join_words(words)
        if not text:
            return None

        text = self.format_subtitle_text(text, subtitle_settings)
        if not text:
            return None

        return {
            "start": words[0].start,
            "end": words[-1].end,
            "text": text,
        }

    def join_words(self, words):
        return "".join(word.word for word in words).strip()

    def format_subtitle_text(self, text, subtitle_settings):
        lines = self.wrap_subtitle_lines(text, subtitle_settings)
        return "\n".join(lines)

    def normalize_subtitle_text(self, text, subtitle_settings):
        if not text:
            return ""

        if subtitle_settings["remove_punctuation"]:
            text = text.translate(str.maketrans("", "", ".,'?!"))

        if subtitle_settings["text_case"] == "lowercase":
            text = text.lower()
        elif subtitle_settings["text_case"] == "UPPERCASE":
            text = text.upper()

        return " ".join(text.split())

    def wrap_subtitle_lines(self, text, subtitle_settings):
        normalized_text = self.normalize_subtitle_text(text, subtitle_settings)
        if not normalized_text:
            return []

        max_chars = subtitle_settings["max_chars"]
        words = normalized_text.split()
        lines = []
        current_line = ""

        for word in words:
            if not current_line:
                current_line = word
                continue

            candidate_line = f"{current_line} {word}"
            if len(candidate_line) <= max_chars:
                current_line = candidate_line
            else:
                lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_app_theme(app)
    window = WhisperApp()
    window.show()
    sys.exit(app.exec())
