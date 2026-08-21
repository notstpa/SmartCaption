import os
import sys
import site
import shutil
import stat
import bisect
import gc
import io
import re
import time
import traceback

if sys.platform == "win32":
    # Best-effort: this only makes pip-installed CUDA libraries findable. It
    # runs before the crash handler is installed, so anything raised here would
    # kill the windowed exe with no window and no log -- indistinguishable from
    # "the app won't start". Losing GPU support is the acceptable failure.
    try:
        for _site_dir in site.getsitepackages():
            _nvidia_dir = os.path.join(_site_dir, "nvidia")
            if os.path.isdir(_nvidia_dir):
                for _pkg in os.listdir(_nvidia_dir):
                    _bin_dir = os.path.join(_nvidia_dir, _pkg, "bin")
                    if os.path.isdir(_bin_dir):
                        os.add_dll_directory(_bin_dir)
                        os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass
import threading
from datetime import datetime

from PyQt6.QtCore import (
    QEvent, QObject, QRect, QSettings, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal
)
from PyQt6.QtGui import QAction, QActionGroup, QColor, QFont, QIcon, QPainter, QPalette, QPen
from PyQt6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from huggingface_hub.utils import disable_progress_bars
from tqdm.auto import tqdm as base_tqdm
import qdarktheme

_ALPHA_RUN_RE = re.compile(r"[a-zA-Z]+")

APP_NAME = "SmartCaption"
APP_VERSION = "2.2.3"

# Explicit repo per model rather than a shared prefix: Systran publishes no
# turbo build, so that one comes from a different publisher.
MODEL_REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large-v3-turbo": "deepdml/faster-whisper-large-v3-turbo-ct2",
}

# Approximate on-disk size, used for the free-space check and the UI hint.
MODEL_SIZES_MB = {
    "tiny": 75,
    "base": 145,
    "small": 484,
    "medium": 1530,
    "large-v3": 3090,
    "large-v3-turbo": 1620,
}

# Decoding quality knobs. These match faster-whisper's own defaults and are
# deliberately not tightened: the thresholds only do useful work while
# temperature fallback is available to retry a failed window.
TEMPERATURE_FALLBACK = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
COMPRESSION_RATIO_THRESHOLD = 2.4
LOG_PROB_THRESHOLD = -1.0
HALLUCINATION_SILENCE_THRESHOLD = 2.0

# Subtitle timing rules, in seconds unless noted.
MIN_SUBTITLE_DURATION = 0.9
MIN_SUBTITLE_GAP = 0.04
MAX_GAP_FILL = 2.0
MAX_CHARS_PER_SECOND = 20.0
MAX_SUBTITLE_LINES = 2

AUTO_DETECT_LANGUAGE = "Auto-detect"

# How long to let a worker finish on shutdown before exiting the hard way.
WORKER_SHUTDOWN_TIMEOUT_MS = 5000
MAX_LOG_BYTES = 2 * 1024 * 1024
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
        try:
            os.remove(probe_path)
        except OSError:
            pass
        return True
    except OSError:
        return False


def resolve_log_file(app_dir):
    """Pick a writable log location, preferring one beside the app.

    Returns None only if neither location can be written, in which case the app
    still runs and simply logs to the on-screen box alone.
    """
    for candidate in (os.path.join(app_dir, "logs"),
                      os.path.join(get_user_data_dir(), "logs")):
        if ensure_writable_dir(candidate):
            log_path = os.path.join(candidate, "smartcaption.log")
            rotate_log_if_needed(log_path)
            return log_path
    return None


def rotate_log_if_needed(log_path):
    """Keep one previous log so the file cannot grow without bound."""
    try:
        if os.path.getsize(log_path) < MAX_LOG_BYTES:
            return
    except OSError:
        return

    previous = log_path + ".1"
    try:
        if os.path.exists(previous):
            os.remove(previous)
        os.replace(log_path, previous)
    except OSError:
        pass


def resolve_model_dir(app_dir):
    preferred_dir = os.path.join(app_dir, "models")
    if ensure_writable_dir(preferred_dir):
        return preferred_dir, "local"

    fallback_dir = os.path.join(get_user_data_dir(), "models")
    if ensure_writable_dir(fallback_dir):
        return fallback_dir, "user"

    raise OSError("Unable to create a writable models folder.")


APP_DIR = get_app_dir()
try:
    MODEL_DIR, _ = resolve_model_dir(APP_DIR)
except OSError as e:
    MODEL_DIR = None
    MODEL_DIR_ERROR = str(e)
else:
    MODEL_DIR_ERROR = None
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
            font-size: 13px;
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
        QTableView::item:selected, QTableWidget::item:selected {{
            border: none;
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
            border-top: 2px solid transparent;
            border-bottom: 2px solid transparent;
            border-left: none;
            border-right: none;
        }}
        QCheckBox:hover, QRadioButton:hover {{
            border-bottom: 2px solid transparent;
        }}
        QCheckBox:focus, QRadioButton:focus {{
            outline: none;
            border-top: 2px solid transparent;
            border-bottom: 2px solid transparent;
            border-left: none;
            border-right: none;
        }}
        QCheckBox:disabled, QRadioButton:disabled {{
            color: {DISABLED_TEXT};
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px;
            height: 18px;
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
            border: 1px solid transparent;
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
        QSlider {{
            background: transparent;
            border: none;
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
        QFrame#footer {{
            background: {PANEL_BG};
            border-top: 1px solid {SOFT_BORDER};
        }}
        QFrame#optionsWrapper {{
            background: transparent;
            border: none;
        }}
    """


def apply_app_theme(app):
    qdarktheme.setup_theme("dark", custom_colors={"primary": "#5294FF"})
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

if MODEL_DIR is not None:
    os.environ["HF_HOME"] = MODEL_DIR
    os.environ["HF_HUB_CACHE"] = MODEL_DIR
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

disable_progress_bars()


# ── Subtitle text and timing pipeline ──
# Deliberately free of Qt and of any app state: everything below is a pure
# function of its arguments, which is what makes it directly testable.

PROFANITY_LIST = {
    "fuck", "fucker", "fucked", "fucking", "fuckin", "fucks",
    "motherfuck", "motherfucker", "motherfuckers", "motherfucking",
    "shit", "shits", "shitting", "shitty",
    "bitch", "bitches", "bitching",
    "ass", "asses", "asshole", "assholes",
    "bastard", "bastards",
    "cunt", "cunts",
    "dick", "dicks",
    "cock", "cocks",
    "pussy", "pussies",
    "whore", "whores",
    "piss", "pissed", "pissing",
    "damn", "damned",
    "crap", "craps",
    "slut", "sluts",
    "prick", "pricks",
    "wanker", "wankers", "wank",
    "twat", "twats",
    "bollocks", "bullshit",
}


def censor_word(word):
    """Mask a profane word, leaving surrounding punctuation intact.

    Masking the raw token would eat the punctuation too, turning "damn," into
    "d****" and losing the comma.

    Each run of letters is judged on its own rather than the token's letters
    stripped of punctuation. Stripping first cannot tell "damn," from "d.a.m.n",
    so it would splice a mask over text that was never a single word -- and it
    misses compounds like "fuck-you", where the profanity is one run of several.
    """

    def mask(match):
        run = match.group()
        if run.lower() not in PROFANITY_LIST:
            return run
        return run[0] + "*" * (len(run) - 1)

    return _ALPHA_RUN_RE.sub(mask, word)


def join_words(words):
    return "".join(word.word for word in words).strip()


def format_srt_timestamp(seconds):
    # Round rather than truncate, and never go below zero: a negative value
    # would format as "-1:59:59,500", which no SRT parser accepts.
    ms = max(0, int(round(seconds * 1000)))
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def normalize_subtitle_text(text, subtitle_settings):
    if not text:
        return ""

    if subtitle_settings.get("censor_profanity"):
        text = " ".join(censor_word(w) for w in text.split())

    if subtitle_settings["remove_punctuation"]:
        text = text.translate(str.maketrans("", "", ".,'?!;:\"…"))

    if subtitle_settings["text_case"] == "lowercase":
        text = text.lower()
    elif subtitle_settings["text_case"] == "UPPERCASE":
        text = text.upper()

    return " ".join(text.split())


def wrap_text_to_lines(text, max_chars):
    """Greedy word wrap. Kept free of the case/censor/punctuation rules so
    manual edits can be re-wrapped without those being re-applied."""
    if not text:
        return []

    lines = []
    current_line = ""

    for word in text.split():
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


def wrap_subtitle_lines(text, subtitle_settings):
    normalized_text = normalize_subtitle_text(text, subtitle_settings)
    return wrap_text_to_lines(normalized_text, subtitle_settings["max_chars"])


def format_subtitle_text(text, subtitle_settings):
    return "\n".join(wrap_subtitle_lines(text, subtitle_settings))


def split_segment_text(text, start, end, subtitle_settings):
    """Break a whole-segment transcription into readable subtitles.

    Used when word timestamps are unavailable, so there are no per-word times to
    split on. A segment can be a full sentence spanning many lines; without this
    it would render as one caption tall enough to cover the video. Timings are
    interpolated by character count, which tracks speech rate closely enough for
    a fallback path.

    The same word and duration budgets the word-timed path enforces are applied
    here too. Honouring only the line count would mean a preset -- or the Max
    words box -- silently did nothing whenever this path ran, and it runs
    whenever word timing is off *or* Whisper returns no word times for a segment.
    """
    normalized_text = normalize_subtitle_text(text, subtitle_settings)
    words = normalized_text.split()
    if not words:
        return []

    max_chars = max(1, int(subtitle_settings["max_chars"]))
    max_words = subtitle_settings.get("max_words")
    max_duration = subtitle_settings.get("max_subtitle_duration")
    duration = max(float(end) - float(start), 0.0)
    total_chars = len(normalized_text) or 1

    # Grouped word by word, the same way the word-timed path builds a subtitle,
    # so both produce the same shape from the same settings. Grouping whole
    # wrapped lines instead would let a wide max_chars hide the word budget
    # entirely -- 12 words on one 60-char line would never hit a limit of 3.
    batches = []
    current = []
    for word in words:
        candidate = current + [word]
        candidate_text = " ".join(candidate)
        over_words = bool(max_words) and len(candidate) > max_words
        over_lines = len(wrap_text_to_lines(candidate_text, max_chars)) > MAX_SUBTITLE_LINES
        over_time = (
            bool(max_duration)
            and duration > 0
            and len(candidate_text) / total_chars * duration > max_duration
        )
        # Budgets are only tested against a non-empty batch, so a single word
        # that busts one on its own is still emitted rather than dropped.
        if current and (over_words or over_lines or over_time):
            batches.append(current)
            current = []
        current.append(word)
    if current:
        batches.append(current)

    chunks = [wrap_text_to_lines(" ".join(batch), max_chars) for batch in batches]
    if len(chunks) == 1:
        return [{"start": start, "end": end, "text": "\n".join(chunks[0])}]

    # Timings are apportioned by visible characters, so measure the wrapped
    # lines rather than the source text: wrapping drops the spaces at each break.
    line_chars = sum(len(line) for chunk in chunks for line in chunk) or 1

    results = []
    elapsed = 0.0
    for position, chunk in enumerate(chunks):
        chunk_chars = sum(len(line) for line in chunk)
        chunk_start = start + elapsed
        elapsed += duration * (chunk_chars / line_chars)
        # Pin the final end to the real segment end so rounding cannot drift.
        chunk_end = end if position == len(chunks) - 1 else start + elapsed
        results.append({
            "start": chunk_start,
            "end": chunk_end,
            "text": "\n".join(chunk),
        })
    return results


def apply_gap_fill(subtitle_segments):
    """Bridge short pauses so captions do not flicker between words.

    Only short gaps are bridged. Stretching a caption across a genuine silence --
    a musical break, a pause between scenes -- would leave stale text frozen on
    screen for the whole thing.
    """
    if len(subtitle_segments) < 2:
        return subtitle_segments

    result = []
    for i, seg in enumerate(subtitle_segments):
        if i < len(subtitle_segments) - 1:
            next_start = subtitle_segments[i + 1]["start"]
            gap = next_start - seg["end"]
            end = next_start if 0 < gap <= MAX_GAP_FILL else seg["end"]
            result.append({"start": seg["start"], "end": end, "text": seg["text"]})
        else:
            result.append(seg)
    return result


def normalize_subtitle_timings(subtitle_segments):
    """Enforce readable durations without ever overlapping the next subtitle.

    Whisper's raw word timings routinely produce sub-100ms subtitles for short
    words, which are unreadable. Each subtitle is extended toward whichever is
    longer -- a minimum on-screen time, or the time needed to read it at
    MAX_CHARS_PER_SECOND -- but never past the following subtitle's start.

    Returns (segments, gap_warnings) so that reporting stays in the UI layer.
    """
    if not subtitle_segments:
        return [], []

    normalized_segments = []
    gap_warnings = []
    previous_end = 0.0

    for index, segment in enumerate(subtitle_segments):
        start = max(float(segment["start"]), previous_end)
        end = max(float(segment["end"]), start)
        text = segment["text"]

        # Longest visible line drives reading time; wrapped lines are read
        # together, so total character count would overstate the need.
        char_count = max((len(line) for line in text.split("\n")), default=0)
        readable_duration = char_count / MAX_CHARS_PER_SECOND
        desired_end = start + max(MIN_SUBTITLE_DURATION, readable_duration)

        next_start = None
        if index + 1 < len(subtitle_segments):
            next_start = float(subtitle_segments[index + 1]["start"])

        if desired_end > end:
            if next_start is None:
                end = desired_end
            else:
                # Leave a frame-sized gap so the two never collide. The outer
                # max() keeps this an extension only: when the next subtitle
                # starts within MIN_SUBTITLE_GAP there is no room to grow, and
                # the clamp alone would cut the caption below its real end.
                end = max(
                    end,
                    min(desired_end, max(start, next_start - MIN_SUBTITLE_GAP)),
                )

        if normalized_segments and start - previous_end > 8.0:
            gap_warnings.append(len(normalized_segments) + 1)

        normalized_segments.append({"start": start, "end": end, "text": text})
        previous_end = end

    return normalized_segments, gap_warnings


class StateValue:
    """A mutable value container used to bridge UI widgets with application state.
    Enables direct connection of widget signals to state updates via Qt's signal/slot system."""

    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def get_free_space_mb(path):
    """Free megabytes on the volume holding path, or None if it cannot be read."""
    try:
        return shutil.disk_usage(path).free / (1024 * 1024)
    except OSError:
        return None


def format_bytes(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def make_progress_reporter(on_progress):
    """Build a tqdm subclass that forwards byte counts to a callback.

    huggingface_hub constructs the progress class itself and relies on the full
    tqdm interface, including classmethods like get_lock() for its parallel
    downloads. Subclassing the real thing inherits all of that; a hand-rolled
    stand-in does not. Rendering is already off via disable_progress_bars().
    """

    class ProgressReporter(base_tqdm):
        def __init__(self, *args, **kwargs):
            # hf_hub creates both byte bars (unit="B") and a file-count bar.
            # Only the byte bar is worth showing; reporting both would flip the
            # label between "480 MB" and a meaningless "6 B" file tally.
            self._tracks_bytes = kwargs.get("unit") == "B"
            # Must stay "enabled": tqdm's update() returns early when disabled,
            # so self.n would never advance. Silence comes from display() below.
            kwargs["disable"] = False
            kwargs["file"] = io.StringIO()
            super().__init__(*args, **kwargs)
            self._report()

        def display(self, *args, **kwargs):
            # Observed, never rendered -- the app has no console.
            return True

        def _report(self):
            if not self._tracks_bytes:
                return
            try:
                on_progress(self.n or 0, self.total or 0)
            except Exception:
                # Progress reporting must never break a download.
                pass

        def update(self, n=1):
            displayed = super().update(n)
            self._report()
            return displayed

        def close(self):
            super().close()
            self._report()

    return ProgressReporter


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
        self._parent = parent

        self.setWindowTitle("Advanced Options")
        set_window_icon(self)
        self.setMinimumSize(640, 430)
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
            help_text="How confident Whisper must be that a section is silent before skipping it. Higher values keep more borderline speech, which helps with soft voices but may add junk captions. Lower values filter more aggressively.",
            values=["0.3", "0.6", "0.8", "1.0"],
            variable=parent.no_speech_threshold,
        )
        self.condition_toggle = self.add_switch_row(
            container_layout,
            row=2,
            title="Condition On Previous Text",
            help_text="When enabled, the model uses previous text as context for the next chunk. This can improve continuity, but sometimes carries mistakes forward.",
            variable=parent.condition_on_previous_text,
        )
        self.use_gpu_toggle = self.add_switch_row(
            container_layout,
            row=3,
            title="Use GPU if Available",
            help_text="When enabled, SmartCaption will use your Nvidia GPU (CUDA) for transcription. This is significantly faster and improves accuracy for larger models. Falls back to CPU automatically if no compatible GPU is found.",
            variable=parent.use_gpu,
        )
        self.vad_filter_toggle = self.add_switch_row(
            container_layout,
            row=4,
            title="Voice Activity Filter",
            help_text="Removes non-speech audio before transcription, which keeps captions off music and background noise. It runs before Whisper, so if it mistakes quiet or distant speech for silence those words are gone before No Speech Threshold ever applies. Turn it off if whole sentences are missing from soft-spoken audio.",
            variable=parent.vad_filter,
        )
        self.pause_threshold_menu = self.add_option_row(
            container_layout,
            row=5,
            title="Pause Threshold (s)",
            help_text="How long a silence between words needs to be before a new subtitle is started. Lower values cut subtitles on very short pauses. Higher values keep more words together.",
            values=["0.1", "0.2", "0.3", "0.5", "0.8", "1.0"],
            variable=parent.pause_threshold,
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
        return toggle

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

    def sync_from_state(self):
        """Redraw the controls from the parent's current values.

        Presets write the same state this dialog edits, so an open dialog would
        otherwise keep showing stale values.
        """
        parent = self._parent
        self.beam_size_menu.setCurrentText(self.format_option_value(parent.beam_size.get()))
        self.no_speech_menu.setCurrentText(self.format_option_value(parent.no_speech_threshold.get()))
        self.condition_toggle.setChecked(bool(parent.condition_on_previous_text.get()))
        self.use_gpu_toggle.setChecked(bool(parent.use_gpu.get()))
        self.vad_filter_toggle.setChecked(bool(parent.vad_filter.get()))
        self.pause_threshold_menu.setCurrentText(self.format_option_value(parent.pause_threshold.get()))

    def reset_defaults(self):
        defaults = self._parent.get_default_advanced_settings()
        self._parent.beam_size.set(defaults["beam_size"])
        self._parent.no_speech_threshold.set(defaults["no_speech_threshold"])
        self._parent.condition_on_previous_text.set(defaults["condition_on_previous_text"])
        self._parent.use_gpu.set(defaults["use_gpu"])
        self._parent.vad_filter.set(defaults["vad_filter"])
        self._parent.pause_threshold.set(defaults["pause_threshold"])
        self.sync_from_state()


class CaptionPreviewWidget(QWidget):
    subtitle_double_clicked = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.subtitle_segments = []
        self.current_time = 0.0
        self.scale_percent = 100
        self.aspect_ratio = 9.0 / 16.0
        self.text_position_pct = 82
        self._subtitle_bg_rect = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 225)

    def sizeHint(self):
        return QSize(640, 360)

    def minimumSizeHint(self):
        return QSize(400, 225)

    def set_subtitles(self, segments):
        self.subtitle_segments = segments or []
        self.update()

    def set_current_time(self, seconds):
        self.current_time = seconds
        self.update()

    def is_active(self, seg):
        # End-exclusive: gap-filled segments are exactly back-to-back, so an
        # inclusive end would show two captions at once on every boundary.
        return seg["start"] <= self.current_time < seg["end"]

    def get_active_segments(self):
        return [seg for seg in self.subtitle_segments if self.is_active(seg)]

    def mouseDoubleClickEvent(self, event):
        if self._subtitle_bg_rect and self._subtitle_bg_rect.contains(event.position().toPoint()):
            for i, seg in enumerate(self.subtitle_segments):
                if self.is_active(seg):
                    self.subtitle_double_clicked.emit(i)
                    return
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        available_w = self.width()
        available_h = self.height()
        aspect = self.aspect_ratio

        if available_w * (1 / aspect) <= available_h:
            canvas_w = available_w
            canvas_h = int(available_w / aspect)
        else:
            canvas_h = available_h
            canvas_w = int(available_h * aspect)

        canvas_x = (available_w - canvas_w) // 2
        canvas_y = (available_h - canvas_h) // 2

        painter.fillRect(self.rect(), QColor(WINDOW_BG))

        painter.fillRect(canvas_x, canvas_y, canvas_w, canvas_h, QColor("#0A0A0A"))
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.drawRect(canvas_x, canvas_y, canvas_w, canvas_h)

        # Cleared on every early return: a stale rect would keep double-click
        # editing armed over empty video long after the caption is gone.
        self._subtitle_bg_rect = None

        if not self.subtitle_segments:
            painter.setPen(QColor(MUTED_TEXT))
            font = QFont("Segoe UI", 14)
            painter.setFont(font)
            painter.drawText(
                QRect(canvas_x, canvas_y, canvas_w, canvas_h),
                Qt.AlignmentFlag.AlignCenter,
                "No subtitles yet"
            )
            painter.end()
            return

        active = self.get_active_segments()
        if not active:
            painter.end()
            return

        margin = int(canvas_w * 0.06)
        text_area_w = canvas_w - margin * 2
        text_area_x = canvas_x + margin
        text_area_bottom = canvas_y + int(canvas_h * self.text_position_pct / 100.0)

        caption_texts = []
        for seg in active:
            caption_texts.append(seg["text"])

        all_lines = []
        for text in caption_texts:
            for line in text.split("\n"):
                all_lines.append(line)

        base_size = max(14, int(canvas_h * 0.05))
        scaled_size = max(10, int(base_size * self.scale_percent / 100.0))
        font = QFont("Segoe UI", scaled_size)
        font.setBold(True)
        painter.setFont(font)
        fm = painter.fontMetrics()

        total_text_height = sum(fm.lineSpacing() for _ in all_lines)
        text_start_y = text_area_bottom - total_text_height
        self._subtitle_bg_rect = QRect(text_area_x, text_start_y, text_area_w, total_text_height)

        painter.setPen(QColor(TEXT))
        current_y = text_area_bottom - total_text_height + fm.ascent()
        for line in all_lines:
            painter.drawText(
                QRect(text_area_x, current_y - fm.ascent(), text_area_w, fm.lineSpacing()),
                Qt.AlignmentFlag.AlignHCenter,
                line
            )
            current_y += fm.lineSpacing()

        painter.end()


class WhisperApp(QMainWindow):
    log_requested = pyqtSignal(str)
    subtitle_preview_ready = pyqtSignal(list)

    def __init__(self):
        super().__init__()

        set_window_icon(self)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1100, 720)
        self.setMinimumSize(1000, 660)

        self.input_path = StateValue("")
        self.model_name = StateValue("large-v3-turbo")
        self.use_word_timestamps = StateValue(True)
        self.remove_punctuation = StateValue(False)
        self.text_case = StateValue("Normal")
        self.language_display = StateValue("")
        self.max_words_per_subtitle = StateValue("8")
        self.max_chars_per_line = StateValue("42")
        self.beam_size = StateValue(5)
        self.no_speech_threshold = StateValue(0.8)
        self.condition_on_previous_text = StateValue(False)
        self.use_gpu = StateValue(False)
        self.preset = StateValue("Normal")
        self.pause_threshold = StateValue(0.5)
        self.max_subtitle_duration = StateValue(3.2)
        self.vad_silence_ms = StateValue(700)
        self.break_on_punctuation_immediate = StateValue(False)
        self.subtitle_scale = StateValue(100)
        self.gap_fill = StateValue(False)
        self.censor_profanity = StateValue(False)
        self.vad_filter = StateValue(True)
        self.vocabulary_hints = StateValue("")

        self.available_models = list(MODEL_REPOS)
        self.model_display_map = {}
        self.installed_models = set()
        self.spinner_frames = ["|", "/", "-", "\\"]
        self.spinner_index = 0
        self.spinner_message = "Idle"
        self.advanced_dialog = None
        self.worker_threads = []
        # Auto-detect maps to None, which is what faster-whisper expects to run
        # its own language identification pass.
        self.language_display_map = {AUTO_DETECT_LANGUAGE: None}
        self.language_display_map.update({
            f"{SUPPORTED_LANGUAGE_NAMES[code]} ({code})": code for code in sorted(
                SUPPORTED_LANGUAGE_NAMES,
                key=lambda code: SUPPORTED_LANGUAGE_NAMES[code].lower()
            )
        })

        self.is_downloading = False
        self.is_transcribing = False
        self.is_deleting = False
        self._cancelled = False
        self._cancel_event = threading.Event()
        self._setup_file_logging()
        self._cached_model = None
        self._cached_model_name = None
        self._cached_model_device = None
        self._cached_model_compute_type = None

        self.subtitle_segments = StateValue([])
        self._segment_ends = []
        self.is_preview_playing = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(50)
        self._preview_timer.timeout.connect(self.advance_preview_playback)
        self._preview_clock_start = 0.0
        self._preview_clock_base_ms = 0

        self._media_player = None
        self._audio_output = None
        self._selected_audio_device = None
        self._audio_menu = None
        self._audio_action_group = None
        self._suppress_slider_update = False
        self._resize_dragging = False
        self._resize_start_y = 0
        self._resize_start_height = 0

        self.spinner_timer = QTimer(self)
        self.spinner_timer.setInterval(120)
        self.spinner_timer.timeout.connect(self.schedule_spinner)
        self.log_requested.connect(self._append_log)
        self.subtitle_preview_ready.connect(self.update_preview_subtitles)

        self._settings = QSettings(APP_NAME, APP_NAME)
        self._saved_audio_device_desc = ""
        self.load_settings()

        self.build_menu_bar()
        self._refresh_audio_devices()
        self.build_ui()

    # Persisted preferences, keyed by StateValue attribute name. Transcription
    # inputs are intentionally excluded -- the input file should not come back.
    PERSISTED_SETTINGS = (
        ("model_name", str),
        ("language_display", str),
        ("vocabulary_hints", str),
        ("preset", str),
        ("text_case", str),
        ("max_words_per_subtitle", str),
        ("max_chars_per_line", str),
        ("use_word_timestamps", bool),
        ("remove_punctuation", bool),
        ("censor_profanity", bool),
        ("gap_fill", bool),
        ("use_gpu", bool),
        ("condition_on_previous_text", bool),
        # Preset-derived, and easy to miss: leaving it out restores a preset
        # by name while silently reverting the behaviour it stands for.
        ("break_on_punctuation_immediate", bool),
        ("vad_filter", bool),
        ("beam_size", int),
        ("subtitle_scale", int),
        ("vad_silence_ms", int),
        ("no_speech_threshold", float),
        ("pause_threshold", float),
        ("max_subtitle_duration", float),
    )

    def load_settings(self):
        for name, value_type in self.PERSISTED_SETTINGS:
            stored = self._settings.value(name)
            if stored is None:
                continue
            try:
                if value_type is bool:
                    # QSettings round-trips bools as the strings "true"/"false".
                    value = stored if isinstance(stored, bool) else str(stored).lower() == "true"
                else:
                    value = value_type(stored)
            except (TypeError, ValueError):
                continue
            getattr(self, name).set(value)

        self._saved_audio_device_desc = str(self._settings.value("audio_device", "") or "")

    def save_settings(self):
        for name, _ in self.PERSISTED_SETTINGS:
            self._settings.setValue(name, getattr(self, name).get())
        self._settings.setValue("audio_device", self._saved_audio_device_desc)
        self._settings.sync()

    def build_menu_bar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        options_menu = menu_bar.addMenu("Options")
        advanced_action = QAction("Advanced Options", self)
        advanced_action.triggered.connect(self.open_advanced_options)
        options_menu.addAction(advanced_action)
        self._audio_menu = options_menu.addMenu("Audio Output")

        help_menu = menu_bar.addMenu("Help")
        model_guide_action = QAction("Model Guide", self)
        model_guide_action.triggered.connect(self.show_model_guide)
        accuracy_tips_action = QAction("Accuracy Tips", self)
        accuracy_tips_action.triggered.connect(self.show_accuracy_tips)
        supported_formats_action = QAction("Supported Formats", self)
        supported_formats_action.triggered.connect(self.show_supported_formats)
        credits_action = QAction("Credits", self)
        credits_action.triggered.connect(self.show_credits_info)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_info)
        help_menu.addAction(model_guide_action)
        help_menu.addAction(accuracy_tips_action)
        help_menu.addSeparator()
        help_menu.addAction(supported_formats_action)
        help_menu.addAction(credits_action)
        help_menu.addAction(about_action)

    def show_about_info(self):
        log_location = self._log_file_path or "unavailable"
        InfoDialog(
            self,
            "About",
            (
                f"{APP_NAME} v{APP_VERSION}\n"
                "\n"
                "Offline subtitle generation powered by Whisper.\n"
                "Audio never leaves your machine.\n"
                "\n"
                f"Models folder:\n{MODEL_DIR}\n"
                "\n"
                f"Log file:\n{log_location}"
            )
        ).exec()

    def show_model_guide(self):
        InfoDialog(
            self,
            "Model Guide",
            (
                "large-v3-turbo (Recommended)  (~1.6 GB)\n"
                "  The best balance by a wide margin. Roughly the speed of\n"
                "  medium, close to large-v3 for accuracy.\n"
                "  Published by deepdml rather than Systran.\n"
                "\n"
                "small  (~484 MB)\n"
                "  Fine for clean, close-mic speech. On noisy audio —\n"
                "  gameplay, music in the background, more than one person —\n"
                "  it drops a lot of words. Measured against hand-made\n"
                "  captions on a gameplay clip, small got about half the\n"
                "  words wrong where turbo got around one in eight.\n"
                "  Pick it only if turbo is too slow on your machine, and\n"
                "  turn the Voice Activity Filter off if words go missing.\n"
                "\n"
                "tiny / base  (~75-145 MB)\n"
                "  Fast, but misses a lot of words.\n"
                "  Not great for most content.\n"
                "\n"
                "medium  (~1.5 GB)\n"
                "  Bigger and slower than turbo without being more accurate.\n"
                "  Turbo is the better pick at this size.\n"
                "\n"
                "large-v3  (~3.1 GB)\n"
                "  Marginally better than turbo at understanding speech,\n"
                "  but far slower and subtitle timing is often off —\n"
                "  words can appear too early or too late."
            )
        ).exec()

    def show_accuracy_tips(self):
        InfoDialog(
            self,
            "Accuracy Tips",
            (
                "Common issues and what to try:\n"
                "\n"
                "- Whole lines missing, especially in noisy or game audio:\n"
                "  1. Use large-v3-turbo. This is by far the biggest factor --\n"
                "     smaller models drop a lot of speech once the Voice\n"
                "     Activity Filter has cut the audio into pieces.\n"
                "  2. If you must use small, turn the Voice Activity Filter\n"
                "     off. That recovers most of it, at the cost of the odd\n"
                "     caption over music.\n"
                "  Raising No Speech Threshold does not help here.\n"
                "\n"
                "- Names, jargon, or game terms coming out wrong:\n"
                "  Type them into the Vocabulary box on the Generate tab.\n"
                "  List the actual words, comma separated -- a vague\n"
                "  description of the video does nothing.\n"
                "\n"
                "- Junk captions during silence or background noise:\n"
                "  Keep the Voice Activity Filter on -- it is what suppresses\n"
                "  captions over music and sound effects.\n"
                "\n"
                "- Repetitive or stuck phrases:\n"
                "  Turn Context Off if it's on\n"
                "\n"
                "- Heavy accents or noisy audio:\n"
                "  Raise Beam Size to 8-10\n"
                "\n"
                "- Wrong language or gibberish output:\n"
                "  Check the Language dropdown, or set it to Auto-detect\n"
                "\n"
                "Tradeoffs:\n"
                "- small is the recommended model — fast and accurate for most content.\n"
                "- large-v3-turbo is the most accurate, at roughly the speed of medium.\n"
                "- Higher Beam Size is significantly slower on CPU.\n"
                "- Higher No Speech Threshold keeps more speech but may add junk.\n"
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
                "- pyqtdarktheme\n"
                "- faster-whisper\n"
                "- CTranslate2\n"
                "- huggingface_hub\n"
                "- PyAV\n"
                "- NumPy\n"
                "- tokenizers\n"
                "- tqdm\n"
                "\n"
                "Speech models:\n"
                "- tiny, base, small, medium, large-v3 by Systran\n"
                "- large-v3-turbo by deepdml\n"
                "All are CTranslate2 conversions of OpenAI's Whisper.\n"
                "\n"
                "For redistribution, include THIRD_PARTY_NOTICES.md with the app."
            )
        ).exec()

    def build_ui(self):
        central = DropWidget()
        central.setObjectName("centralWidget")
        central.file_dropped.connect(self.handle_file_drop)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        root_layout.addWidget(self.tab_widget)

        generate_tab = QWidget()
        generate_layout = QVBoxLayout(generate_tab)
        generate_layout.setContentsMargins(20, 12, 20, 12)
        generate_layout.setSpacing(10)

        self.setCentralWidget(central)
        self.build_generate_tab(generate_layout)
        self.build_preview_tab()

        self.tab_widget.addTab(generate_tab, "Generate")
        self.tab_widget.addTab(self._preview_tab, "Output")
        self.tab_widget.setTabEnabled(1, False)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def build_generate_tab(self, root):

        file_frame = QFrame()
        file_layout = QGridLayout(file_frame)
        file_layout.setContentsMargins(12, 10, 12, 10)
        file_layout.setHorizontalSpacing(10)
        file_layout.setVerticalSpacing(8)

        self.input_btn = QPushButton("Input")
        self.input_btn.clicked.connect(self.pick_input)
        file_layout.addWidget(self.input_btn, 0, 0)

        self.input_entry = DropLineEdit()
        self.input_entry.setPlaceholderText("Drop a media file here or click Input to browse...")
        self.input_entry.setText(self.input_path.get())
        self.input_entry.textChanged.connect(self.input_path.set)
        self.input_entry.file_dropped.connect(self.handle_file_drop)
        file_layout.addWidget(self.input_entry, 0, 1)

        self.vocabulary_label = QLabel("Vocabulary")
        file_layout.addWidget(self.vocabulary_label, 1, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.vocabulary_entry = QLineEdit(self.vocabulary_hints.get())
        self.vocabulary_entry.setPlaceholderText(
            "Optional: names, jargon, or game terms in this video — improves accuracy"
        )
        self.vocabulary_entry.setToolTip(
            "Words Whisper is unlikely to know: player names, game terms, brand names.\n"
            "Measured on real gameplay audio, listing the right terms cut the error\n"
            "rate from 15% to 13%. A vague description does not help — use actual words."
        )
        self.vocabulary_entry.textChanged.connect(self.vocabulary_hints.set)
        file_layout.addWidget(self.vocabulary_entry, 1, 1)

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
        preset_layout.addWidget(self.preset_menu, 1)
        preset_layout.addSpacing(20)
        language_label = QLabel("Language")
        language_label.setObjectName("bold")
        preset_layout.addWidget(language_label)
        language_values = list(self.language_display_map.keys())
        current_language = self.language_display.get() or AUTO_DETECT_LANGUAGE
        self.language_menu = QComboBox()
        self.language_menu.addItems(language_values)
        self.language_menu.currentTextChanged.connect(self.language_display.set)
        self.language_menu.setCurrentText(current_language)
        # setCurrentText emits nothing when the combo already shows that value,
        # which is the case for the default, so seed the state directly.
        self.language_display.set(self.language_menu.currentText())
        preset_layout.addWidget(self.language_menu, 1)
        root.addWidget(preset_frame)

        options_frame = QFrame()
        options_frame.setObjectName("optionsWrapper")
        options_layout = QGridLayout(options_frame)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setHorizontalSpacing(10)
        options_layout.setVerticalSpacing(10)

        model_frame = QFrame()
        model_frame.setObjectName("card")
        model_layout = QVBoxLayout(model_frame)
        model_layout.setContentsMargins(12, 12, 12, 12)
        model_layout.setSpacing(8)
        self.model_section_label = QLabel("Transcription")
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
        self.delete_btn.setEnabled(False)
        model_layout.addWidget(self.delete_btn)
        model_layout.addStretch(1)
        options_layout.addWidget(model_frame, 0, 0)

        timing_frame = QFrame()
        timing_frame.setObjectName("card")
        timing_layout = QGridLayout(timing_frame)
        timing_layout.setContentsMargins(12, 12, 12, 12)
        timing_layout.setHorizontalSpacing(10)
        timing_layout.setVerticalSpacing(8)
        self.timing_section_label = QLabel("Subtitle Timing")
        self.timing_section_label.setObjectName("sectionLabel")
        timing_layout.addWidget(self.timing_section_label, 0, 0, 1, 2)
        self.gap_fill_checkbox = QCheckBox("Gap fill")
        self.gap_fill_checkbox.setChecked(self.gap_fill.get())
        self.gap_fill_checkbox.toggled.connect(self.gap_fill.set)
        timing_layout.addWidget(self.gap_fill_checkbox, 1, 0, 1, 2)
        self.word_timestamps_checkbox = QCheckBox("Word-level subtitle timing")
        self.word_timestamps_checkbox.setChecked(self.use_word_timestamps.get())
        self.word_timestamps_checkbox.toggled.connect(self.use_word_timestamps.set)
        timing_layout.addWidget(self.word_timestamps_checkbox, 2, 0, 1, 2)
        self.max_words_label = QLabel("Max words/subtitle")
        timing_layout.addWidget(self.max_words_label, 3, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.max_words_entry = QLineEdit(self.max_words_per_subtitle.get())
        self.max_words_entry.textChanged.connect(self.max_words_per_subtitle.set)
        self.max_words_entry.textChanged.connect(self._validate_numeric_inputs)
        timing_layout.addWidget(self.max_words_entry, 3, 1)
        self.max_chars_label = QLabel("Max chars/line")
        timing_layout.addWidget(self.max_chars_label, 4, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.max_chars_entry = QLineEdit(self.max_chars_per_line.get())
        self.max_chars_entry.textChanged.connect(self.max_chars_per_line.set)
        self.max_chars_entry.textChanged.connect(self._validate_numeric_inputs)
        timing_layout.addWidget(self.max_chars_entry, 4, 1)
        timing_layout.setColumnStretch(1, 1)
        timing_layout.setRowStretch(5, 1)
        options_layout.addWidget(timing_frame, 0, 1)

        text_frame = QFrame()
        text_frame.setObjectName("card")
        text_layout = QGridLayout(text_frame)
        text_layout.setContentsMargins(12, 12, 12, 12)
        text_layout.setHorizontalSpacing(10)
        text_layout.setVerticalSpacing(8)
        self.text_section_label = QLabel("Formatting")
        self.text_section_label.setObjectName("sectionLabel")
        text_layout.addWidget(self.text_section_label, 0, 0, 1, 2)
        self.remove_punctuation_checkbox = QCheckBox("Remove punctuation")
        self.remove_punctuation_checkbox.setChecked(self.remove_punctuation.get())
        self.remove_punctuation_checkbox.toggled.connect(self.remove_punctuation.set)
        text_layout.addWidget(self.remove_punctuation_checkbox, 1, 0, 1, 2)
        self.censor_profanity_checkbox = QCheckBox("Censor profanity")
        self.censor_profanity_checkbox.setChecked(self.censor_profanity.get())
        self.censor_profanity_checkbox.toggled.connect(self.censor_profanity.set)
        text_layout.addWidget(self.censor_profanity_checkbox, 2, 0, 1, 2)
        self.text_case_label = QLabel("Text case")
        text_layout.addWidget(self.text_case_label, 3, 0, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.text_case_menu = QComboBox()
        self.text_case_menu.addItems(["Normal", "lowercase", "UPPERCASE"])
        self.text_case_menu.setCurrentText(self.text_case.get())
        self.text_case_menu.currentTextChanged.connect(self.text_case.set)
        text_layout.addWidget(self.text_case_menu, 3, 1)
        text_layout.setColumnStretch(1, 1)
        text_layout.setRowStretch(4, 1)
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
        self.generate_btn.setToolTip("Select a media file, download a model, then click Generate to create subtitles.")
        self.generate_btn.clicked.connect(self.start_transcription)
        status_row.addWidget(self.generate_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.clicked.connect(self.cancel_operation)
        self.cancel_btn.hide()
        status_row.addWidget(self.cancel_btn)
        root.addLayout(status_row)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Progress and messages will appear here...")
        self.log_box.setFont(QFont("Segoe UI", 11))
        self.log_box.setStyleSheet("QTextEdit { color: #D8D8D8; font-size: 11px; }")
        root.addWidget(self.log_box, 1)

        self.refresh_model_menu()

    def _append_log(self, text):
        self.log_box.append(text)
        self.log_box.moveCursor(self.log_box.textCursor().MoveOperation.End)

    def log(self, text):
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        if self._log_file_path:
            try:
                with open(self._log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"{timestamp} {text}\n")
            except OSError:
                pass
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

    PRESETS = {
        "Normal": {
            "pause_threshold": 0.5,
            "max_subtitle_duration": 3.2,
            "vad_silence_ms": 700,
            "break_on_punctuation_immediate": False,
            "max_words_per_subtitle": "8",
            "max_chars_per_line": "42",
            "gap_fill": False,
            "description": "balanced subtitle pacing.",
        },
        "TikTok": {
            "pause_threshold": 0.5,
            "max_subtitle_duration": 2.0,
            "vad_silence_ms": 500,
            "break_on_punctuation_immediate": True,
            "max_words_per_subtitle": "2",
            "max_chars_per_line": "20",
            "gap_fill": True,
            "description": "1-2 words per subtitle, gap-filled for continuous display.",
        },
    }

    def on_preset_changed(self, choice):
        preset = self.PRESETS.get(choice)
        if preset is None:
            return

        # Pause threshold is also editable in Advanced Options, so say plainly
        # when a preset is about to overwrite a hand-tuned value.
        if self.pause_threshold.get() != preset["pause_threshold"]:
            self.log(
                f"Preset overrides Pause Threshold: "
                f"{self.pause_threshold.get()} -> {preset['pause_threshold']}"
            )

        self.preset.set(choice)
        self.pause_threshold.set(preset["pause_threshold"])
        self.max_subtitle_duration.set(preset["max_subtitle_duration"])
        self.vad_silence_ms.set(preset["vad_silence_ms"])
        self.break_on_punctuation_immediate.set(preset["break_on_punctuation_immediate"])
        self.max_words_per_subtitle.set(preset["max_words_per_subtitle"])
        self.max_chars_per_line.set(preset["max_chars_per_line"])
        self.gap_fill.set(preset["gap_fill"])

        self.max_words_entry.setText(preset["max_words_per_subtitle"])
        self.max_chars_entry.setText(preset["max_chars_per_line"])
        self.gap_fill_checkbox.setChecked(preset["gap_fill"])

        # Keep an open Advanced Options dialog in sync with the new values.
        if self.advanced_dialog is not None and self.advanced_dialog.isVisible():
            self.advanced_dialog.sync_from_state()

        self.log(f"Preset: {choice} - {preset['description']}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            focus_widget = QApplication.focusWidget()
            if isinstance(focus_widget, (QLineEdit, QTextEdit)):
                super().keyPressEvent(event)
                return
            if self.tab_widget.currentIndex() == 1 and self.tab_widget.isTabEnabled(1):
                self.toggle_preview_playback()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # Signal any running worker to stop. Transcription checks this between
        # segments; a download in progress cannot be interrupted, so we wait.
        self._cancelled = True
        self._cancel_event.set()
        self._preview_timer.stop()
        self.spinner_timer.stop()
        if self._media_player is not None:
            self._media_player.stop()

        # Saved before the shutdown wait, so preferences survive the hard exit
        # below when a worker refuses to stop.
        try:
            self.save_settings()
        except Exception:
            pass

        stubborn = False
        for thread_ref, _ in self.worker_threads:
            if thread_ref.isRunning():
                # quit() only unwinds a Qt event loop; it cannot interrupt the
                # blocking call inside the worker's run().
                thread_ref.quit()
                if not thread_ref.wait(WORKER_SHUTDOWN_TIMEOUT_MS):
                    stubborn = True

        if stubborn:
            # A worker is still inside CTranslate2 or a download. Returning from
            # closeEvent would tear down the interpreter underneath live native
            # code and crash on exit, so leave by a path that skips cleanup.
            # log() writes to disk synchronously, so the message survives.
            self.log("Closing while work is still running; exiting now.")
            os._exit(0)

        event.accept()

    def cancel_operation(self):
        # Request cancellation but keep controls disabled until the worker
        # thread actually finishes. The finish callback re-enables the UI.
        # This prevents a second operation starting alongside the live worker.
        self._cancel_event.set()
        self._cancelled = True
        self.cancel_btn.setEnabled(False)
        if self.is_downloading:
            self.log("Downloads can't be interrupted; finishing in the background...")
            self.spinner_message = "Finishing download..."
        elif self.is_transcribing:
            self.log("Cancelling transcription...")
            self.spinner_message = "Cancelling..."

    def _setup_file_logging(self):
        # Same local-then-user-data fallback the model directory uses: an app
        # installed under Program Files cannot write beside its own exe, and
        # that is exactly when logs matter most.
        self._log_file_path = resolve_log_file(APP_DIR)

    def eventFilter(self, obj, event):
        if isinstance(obj, QComboBox):
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Space:
                if self.tab_widget.currentIndex() == 1 and self.tab_widget.isTabEnabled(1):
                    self.toggle_preview_playback()
                    return True
        if isinstance(obj, QFrame) and obj.property("is_resize_handle"):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._resize_dragging = True
                self._resize_start_y = event.globalPosition().y()
                self._resize_start_height = self._preview_frame.height()
                obj.grabMouse()
                obj.setStyleSheet("QFrame { background: transparent; border-top: 2px solid " + ACCENT + "; }")
                return True
            elif event.type() == QEvent.Type.MouseMove and self._resize_dragging:
                delta = int(event.globalPosition().y() - self._resize_start_y)
                new_height = max(60, min(500, self._resize_start_height + delta))
                self._preview_frame.setFixedHeight(new_height)
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease and self._resize_dragging:
                self._resize_dragging = False
                obj.releaseMouse()
                obj.setStyleSheet("QFrame { background: transparent; border-top: 2px solid " + SOFT_BORDER + "; }")
                return True
        return super().eventFilter(obj, event)

    def on_preview_subtitle_double_clicked(self, segment_idx):
        item = self._timeline_table.item(segment_idx, 3)
        if item:
            self._timeline_table.scrollToItem(item, QTableWidget.ScrollHint.PositionAtCenter)
            self._timeline_table.editItem(item)

    def handle_file_drop(self, path):
        if not path or not os.path.isfile(path):
            self.log("Drop a file onto the input field or app window.")
            return

        self.set_input_file(path)

    def set_busy_controls_disabled(self, disabled):
        for widget in (
            self.input_btn,
            self.input_entry,
            self.preset_menu,
            self.download_btn,
            self.delete_btn,
            self.generate_btn,
            self.model_menu,
            self.word_timestamps_checkbox,
            self.remove_punctuation_checkbox,
            self.text_case_menu,
            self.language_menu,
            self.max_words_entry,
            self.max_chars_entry,
            self.gap_fill_checkbox,
            self.censor_profanity_checkbox,
            self.vocabulary_entry,
        ):
            widget.setDisabled(disabled)
        self.menuBar().setDisabled(disabled)
        if self.advanced_dialog is not None and self.advanced_dialog.isVisible():
            self.advanced_dialog.setDisabled(disabled)
        if not disabled:
            # Restore download/delete enablement based on install state.
            self._update_model_action_buttons(self.model_name.get())

    def set_download_state(self, active, model_name=None):
        if active:
            self._cancel_event.clear()
            self.cancel_btn.setEnabled(True)
            self.cancel_btn.show()
            self.start_status_spinner(f"Downloading {model_name}...")
        else:
            self.cancel_btn.hide()
            self.stop_status_spinner()

        self.set_busy_controls_disabled(bool(active))

    def set_delete_state(self, active, model_name=None):
        # No cancel button: interrupting a half-finished rmtree would leave a
        # model directory that looks installed but cannot load.
        if active:
            self.start_status_spinner(f"Deleting {model_name}...")
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
        if not self.is_downloading and not self.is_transcribing and not self.is_deleting:
            self.spinner_timer.stop()
            return

        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        self.download_status_label.setText(f"{self.spinner_frames[self.spinner_index]} {self.spinner_message}")

    def clear_preview_tab(self):
        self.subtitle_segments.set([])
        self._segment_ends = []
        self._preview_widget.set_subtitles([])
        self._preview_widget.update()
        self._preview_play_btn.setText("▶ Play")
        self._preview_slider.setValue(0)
        self._preview_slider.setMaximum(1000)
        self._preview_time_label.setText("00:00")
        self._preview_duration_label.setText("00:00")
        self._export_btn.setEnabled(False)
        if self._media_player and self._media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self._media_player.stop()
        if self._media_player:
            self._media_player.setSource(QUrl())
        self.is_preview_playing = False
        self._preview_timer.stop()
        self._timeline_table.setRowCount(0)

    def set_transcription_state(self, active):
        self.is_transcribing = active
        if active:
            self._cancel_event.clear()
            self.cancel_btn.setEnabled(True)
            self.cancel_btn.show()
            self.tab_widget.setTabEnabled(1, False)
            self.clear_preview_tab()
            self.start_status_spinner("Transcribing...")
        else:
            self.cancel_btn.hide()
            self.stop_status_spinner()

        self.set_busy_controls_disabled(bool(active))

    def finish_transcription(self, subtitle_settings):
        self.set_transcription_state(False)
        if self._cancelled:
            return
        segments = self.subtitle_segments.get()
        if segments:
            self.tab_widget.setTabEnabled(1, True)
            self.setup_audio_player(subtitle_settings["input_path"])
            self.tab_widget.setCurrentIndex(1)
        else:
            self.log("No subtitles were generated.")

    def build_preview_tab(self):
        self._preview_tab = QWidget()
        outer = QVBoxLayout(self._preview_tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── middle zone: sidebar + content ──
        middle = QHBoxLayout()
        middle.setContentsMargins(12, 8, 12, 8)
        middle.setSpacing(12)

        # sidebar
        sidebar = QFrame()
        sidebar.setObjectName("card")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_layout.setSpacing(10)

        display_label = QLabel("Display")
        display_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(display_label)

        resolution_label = QLabel("Resolution")
        resolution_label.setObjectName("bold")
        sidebar_layout.addWidget(resolution_label)
        self._resolution_combo = QComboBox()
        self._resolution_combo.addItems(["9:16 (Portrait)", "16:9 (Landscape)"])
        self._resolution_combo.setCurrentIndex(0)
        self._resolution_combo.currentIndexChanged.connect(self.on_resolution_changed)
        self._resolution_combo.installEventFilter(self)
        sidebar_layout.addWidget(self._resolution_combo)

        sidebar_layout.addSpacing(6)

        scale_label = QLabel("Subtitle size")
        scale_label.setObjectName("bold")
        sidebar_layout.addWidget(scale_label)
        scale_slider_row = QHBoxLayout()
        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setMinimum(50)
        self._scale_slider.setMaximum(200)
        self._scale_slider.setValue(self.subtitle_scale.get())
        self._scale_slider.valueChanged.connect(self.on_scale_changed)
        scale_slider_row.addWidget(self._scale_slider, 1)
        self._scale_value_label = QLabel(f"{self.subtitle_scale.get()}%")
        self._scale_value_label.setObjectName("muted")
        self._scale_value_label.setFixedWidth(36)
        scale_slider_row.addWidget(self._scale_value_label)
        sidebar_layout.addLayout(scale_slider_row)

        sidebar_layout.addSpacing(6)

        position_label = QLabel("Text position")
        position_label.setObjectName("bold")
        sidebar_layout.addWidget(position_label)
        position_slider_row = QHBoxLayout()
        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setMinimum(5)
        self._position_slider.setMaximum(95)
        self._position_slider.setValue(82)
        self._position_slider.valueChanged.connect(self.on_position_changed)
        position_slider_row.addWidget(self._position_slider, 1)
        self._position_value_label = QLabel("82%")
        self._position_value_label.setObjectName("muted")
        self._position_value_label.setFixedWidth(36)
        position_slider_row.addWidget(self._position_value_label)
        sidebar_layout.addLayout(position_slider_row)

        sidebar_layout.addStretch(1)

        preview_note = QLabel("Scale and position are\npreview-only — they do not\naffect exported SRT.")
        preview_note.setObjectName("previewNote")
        preview_note.setWordWrap(True)
        preview_note.setStyleSheet(
            "QLabel#previewNote {"
            "  color: " + MUTED_TEXT + ";"
            "  background: rgba(58, 175, 255, 0.06);"
            "  border-left: 3px solid rgba(58, 175, 255, 0.35);"
            "  padding: 6px 10px;"
            "  border-radius: 0px 4px 4px 0px;"
            "  font-size: 12px;"
            "}"
        )
        sidebar_layout.addWidget(preview_note)

        middle.addWidget(sidebar)

        # right content column
        content = QVBoxLayout()
        content.setSpacing(8)

        preview_frame = QFrame()
        preview_frame.setObjectName("card")
        preview_frame.setFixedHeight(240)
        self._preview_frame = preview_frame
        preview_frame_layout = QVBoxLayout(preview_frame)
        preview_frame_layout.setContentsMargins(0, 0, 0, 0)
        preview_frame_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_widget = CaptionPreviewWidget()
        self._preview_widget.subtitle_double_clicked.connect(self.on_preview_subtitle_double_clicked)
        preview_frame_layout.addWidget(self._preview_widget)
        content.addWidget(preview_frame, 0)

        # drag handle
        self._preview_resize_handle = QFrame()
        self._preview_resize_handle.setFixedHeight(6)
        self._preview_resize_handle.setCursor(Qt.CursorShape.SizeVerCursor)
        self._preview_resize_handle.setStyleSheet("QFrame { background: transparent; border-top: 2px solid " + SOFT_BORDER + "; }")
        self._preview_resize_handle.installEventFilter(self)
        self._preview_resize_handle.setProperty("is_resize_handle", True)
        content.addWidget(self._preview_resize_handle, 0)

        # playback bar
        playback_row = QHBoxLayout()
        playback_row.setSpacing(10)
        self._preview_time_label = QLabel("00:00")
        self._preview_time_label.setObjectName("muted")
        self._preview_time_label.setFixedWidth(45)
        playback_row.addWidget(self._preview_time_label)

        self._preview_slider = QSlider(Qt.Orientation.Horizontal)
        self._preview_slider.setMinimum(0)
        self._preview_slider.setMaximum(1000)
        self._preview_slider.setValue(0)
        self._preview_slider.sliderPressed.connect(self.on_preview_slider_pressed)
        self._preview_slider.sliderReleased.connect(self.on_preview_slider_released)
        self._preview_slider.valueChanged.connect(self.on_preview_slider_changed)
        playback_row.addWidget(self._preview_slider, 1)

        self._preview_duration_label = QLabel("00:00")
        self._preview_duration_label.setObjectName("muted")
        self._preview_duration_label.setFixedWidth(45)
        playback_row.addWidget(self._preview_duration_label)

        self._preview_play_btn = QPushButton("▶ Play")
        self._preview_play_btn.setFixedWidth(100)
        self._preview_play_btn.clicked.connect(self.toggle_preview_playback)
        playback_row.addWidget(self._preview_play_btn)
        content.addLayout(playback_row)

        # subtitle table
        self._timeline_table = QTableWidget(0, 4)
        self._timeline_table.verticalHeader().setVisible(False)
        self._timeline_table.verticalHeader().setDefaultSectionSize(28)
        self._timeline_table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        self._timeline_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._timeline_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._timeline_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._timeline_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._timeline_table.setColumnWidth(0, 40)
        self._timeline_table.setColumnWidth(1, 115)
        self._timeline_table.setColumnWidth(2, 115)
        self._timeline_table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self._timeline_table.cellChanged.connect(self.on_timeline_cell_changed)
        self._timeline_table.cellDoubleClicked.connect(self.on_timeline_double_clicked)
        content.addWidget(self._timeline_table, 1)

        middle.addLayout(content, 1)
        outer.addLayout(middle, 1)

        # ── footer: sync + export ──
        footer = QFrame()
        footer.setObjectName("footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 8, 14, 8)

        self._sync_checkbox = QCheckBox("Sync")
        self._sync_checkbox.setChecked(True)
        footer_layout.addWidget(self._sync_checkbox)
        footer_layout.addStretch(1)
        self._export_btn = QPushButton("Export SRT")
        self._export_btn.setFixedWidth(120)
        self._export_btn.clicked.connect(self.export_srt_from_preview)
        self._export_btn.setEnabled(False)
        footer_layout.addWidget(self._export_btn)

        outer.addWidget(footer)

        # The slider was populated from the saved value before its valueChanged
        # signal was connected, so nothing has pushed that value into the widget
        # that actually paints. Run the handler once now that all three of the
        # slider, the label, and the preview widget exist.
        self.on_scale_changed(self.subtitle_scale.get())

    def update_preview_subtitles(self, segments):
        self.subtitle_segments.set(segments)
        self._segment_ends = [seg.get("end", 0) for seg in segments]
        self._preview_widget.set_subtitles(segments)
        total = segments[-1]["end"] if segments else 0.0
        total_ms = int(total * 1000)
        self._preview_slider.setMaximum(max(1, total_ms))
        self._preview_slider.setValue(0)
        self._preview_widget.set_current_time(0.0)
        self._preview_time_label.setText("00:00")
        self._preview_duration_label.setText(self.format_time(total))
        self._preview_play_btn.setText("▶ Play")
        self.is_preview_playing = False
        self._preview_timer.stop()
        self.populate_timeline(segments)
        self._export_btn.setEnabled(bool(segments))

    def setup_audio_player(self, file_path):
        if not file_path or not os.path.isfile(file_path):
            return
        if self._media_player is not None:
            self._media_player.stop()
            self._media_player.deleteLater()
        if self._audio_output is not None:
            self._audio_output.deleteLater()

        self._refresh_audio_devices()

        self._audio_output = QAudioOutput(self._selected_audio_device if self._selected_audio_device else QMediaDevices.defaultAudioOutput())
        self._media_player = QMediaPlayer()
        self._media_player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)
        self._media_player.setSource(QUrl.fromLocalFile(file_path))
        self._media_player.positionChanged.connect(self.sync_media_slider)
        self._media_player.durationChanged.connect(self.on_media_duration_changed)
        self._media_player.playbackStateChanged.connect(self.on_media_state_changed)
        self._media_player.errorOccurred.connect(self.on_media_error)

    def sync_media_slider(self, position_ms):
        if not self._suppress_slider_update:
            self._preview_slider.blockSignals(True)
            self._preview_slider.setValue(position_ms)
            self._preview_slider.blockSignals(False)
            seconds = position_ms / 1000.0
            self._preview_widget.set_current_time(seconds)
            self._preview_time_label.setText(self.format_time(seconds))
            self.scroll_timeline_to_time(seconds)

    def on_media_duration_changed(self, duration_ms):
        if duration_ms > 0:
            self._preview_slider.setMaximum(duration_ms)
            self._preview_duration_label.setText(self.format_time(duration_ms / 1000.0))

    def on_media_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.is_preview_playing = False
            self._preview_play_btn.setText("▶ Play")
            self._preview_timer.stop()
        elif state == QMediaPlayer.PlaybackState.PlayingState:
            self.is_preview_playing = True
            self._preview_play_btn.setText("⏸ Pause")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.is_preview_playing = False
            self._preview_play_btn.setText("▶ Play")

    def on_media_error(self, error, error_string):
        self.log(f"Audio playback error: {error_string}")

    def on_audio_device_changed(self, device):
        if device and self._media_player:
            was_playing = self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
            pos = self._media_player.position()
            self._media_player.stop()
            if self._audio_output is not None:
                self._audio_output.deleteLater()
            self._audio_output = QAudioOutput(device)
            self._audio_output.setVolume(1.0)
            self._media_player.setAudioOutput(self._audio_output)
            self._media_player.setPosition(pos)
            if was_playing:
                self._media_player.play()

    def _refresh_audio_devices(self):
        self._audio_menu.clear()
        audio_devices = QMediaDevices.audioOutputs()
        default_device = QMediaDevices.defaultAudioOutput()

        if not audio_devices:
            action = self._audio_menu.addAction("No devices found")
            action.setEnabled(False)
            self._audio_menu.setEnabled(False)
            return

        selected = default_device
        # An action group makes selection exclusive in Qt rather than by hand.
        self._audio_action_group = QActionGroup(self._audio_menu)
        self._audio_action_group.setExclusive(True)
        for device in audio_devices:
            action = self._audio_menu.addAction(device.description())
            action.setCheckable(True)
            self._audio_action_group.addAction(action)
            if self._saved_audio_device_desc and device.description() == self._saved_audio_device_desc:
                action.setChecked(True)
                selected = device
            # The action is captured explicitly: these are connected to a bare
            # lambda, so self.sender() would not resolve back to this window.
            action.triggered.connect(
                lambda checked, d=device, a=action: self._on_audio_menu_selected(d, a)
            )

        if not self._saved_audio_device_desc:
            for action in self._audio_menu.actions():
                if action.text() == default_device.description():
                    action.setChecked(True)
                    break

        self._selected_audio_device = selected
        self._audio_menu.setEnabled(True)

    def _on_audio_menu_selected(self, device, action):
        action.setChecked(True)
        self._selected_audio_device = device
        self._saved_audio_device_desc = device.description()
        if self._media_player and self._media_player.source().isValid():
            self.on_audio_device_changed(device)

    def on_scale_changed(self, value):
        self.subtitle_scale.set(value)
        self._scale_value_label.setText(f"{value}%")
        self._preview_widget.scale_percent = value
        self._preview_widget.update()

    def on_resolution_changed(self, index):
        aspect_map = {0: 9.0 / 16.0, 1: 16.0 / 9.0}
        self._preview_widget.aspect_ratio = aspect_map.get(index, 9.0 / 16.0)
        self._preview_widget.update()

    def on_position_changed(self, value):
        self._position_value_label.setText(f"{value}%")
        self._preview_widget.text_position_pct = value
        self._preview_widget.update()

    def on_preview_slider_pressed(self):
        self._suppress_slider_update = True
        if self._media_player and self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()

    def on_preview_slider_released(self):
        self._suppress_slider_update = False
        ms = self._preview_slider.value()
        seconds = ms / 1000.0
        self._preview_widget.set_current_time(seconds)
        self._preview_time_label.setText(self.format_time(seconds))
        if self._media_player:
            self._media_player.setPosition(ms)
        if self.is_preview_playing:
            if self._media_player:
                self._media_player.play()

    def on_preview_slider_changed(self, value):
        seconds = value / 1000.0
        self._preview_widget.set_current_time(seconds)
        self._preview_time_label.setText(self.format_time(seconds))

    def _on_tab_changed(self, index):
        if index != 1 and self.is_preview_playing:
            self._pause_preview()

    def _pause_preview(self):
        self.is_preview_playing = False
        self._preview_timer.stop()
        if self._media_player and self._media_player.source().isValid():
            self._media_player.pause()
        self._preview_play_btn.setText("▶ Play")

    def toggle_preview_playback(self):
        if self._media_player and self._media_player.source().isValid():
            if self.is_preview_playing:
                self._media_player.pause()
                self.is_preview_playing = False
                self._preview_play_btn.setText("▶ Play")
            else:
                current_ms = self._preview_slider.value()
                total_ms = self._preview_slider.maximum()
                if current_ms >= total_ms:
                    self._media_player.setPosition(0)
                self._media_player.play()
                self.is_preview_playing = True
                self._preview_play_btn.setText("⏸ Pause")
            return

        segments = self.subtitle_segments.get()
        if not segments:
            return

        if self.is_preview_playing:
            self.is_preview_playing = False
            self._preview_timer.stop()
            self._preview_play_btn.setText("▶ Play")
        else:
            current_ms = self._preview_slider.value()
            total_ms = self._preview_slider.maximum()
            if current_ms >= total_ms:
                self._preview_slider.setValue(0)
                current_ms = 0
            self._preview_clock_base_ms = current_ms
            self._preview_clock_start = time.monotonic()
            self.is_preview_playing = True
            self._preview_timer.start()
            self._preview_play_btn.setText("⏸ Pause")

    def scroll_timeline_to_time(self, seconds):
        if not self._sync_checkbox.isChecked():
            return
        ends = self._segment_ends
        if not ends:
            return
        i = bisect.bisect_right(ends, seconds)
        if i >= len(ends):
            i = len(ends) - 1
        item = self._timeline_table.item(i, 0)
        if item:
            self._timeline_table.scrollToItem(item, QTableWidget.ScrollHint.PositionAtCenter)
            self._timeline_table.blockSignals(True)
            self._timeline_table.selectRow(i)
            self._timeline_table.blockSignals(False)

    def advance_preview_playback(self):
        """Silent playback clock, used when the media file cannot be loaded.

        Reachable when the source was moved or deleted between transcription and
        preview, so captions can still be scrubbed without audio. Driven by the
        wall clock rather than by counting ticks, which would drift.
        """
        now = time.monotonic()
        elapsed_ms = int((now - self._preview_clock_start) * 1000)
        new_ms = self._preview_clock_base_ms + elapsed_ms

        total_ms = self._preview_slider.maximum()
        if new_ms >= total_ms:
            new_ms = total_ms
            self.is_preview_playing = False
            self._preview_timer.stop()
            self._preview_play_btn.setText("▶ Play")

        self._preview_slider.setValue(new_ms)
        self.scroll_timeline_to_time(new_ms / 1000.0)

    def populate_timeline(self, segments):
        self._timeline_table.blockSignals(True)
        self._timeline_table.setRowCount(0)
        self._timeline_table.setRowCount(len(segments))
        for row, seg in enumerate(segments):
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setFlags(idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            idx_item.setForeground(QColor(MUTED_TEXT))
            self._timeline_table.setItem(row, 0, idx_item)

            start_item = QTableWidgetItem(self.format_srt_time(seg["start"]))
            start_item.setFlags(start_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._timeline_table.setItem(row, 1, start_item)

            end_item = QTableWidgetItem(self.format_srt_time(seg["end"]))
            end_item.setFlags(end_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._timeline_table.setItem(row, 2, end_item)

            # Line breaks are shown as " | " but the real text is carried in
            # UserRole; parsing the display string back would corrupt any
            # caption that legitimately contains a pipe.
            text_item = QTableWidgetItem(seg["text"].replace("\n", " | "))
            text_item.setData(Qt.ItemDataRole.UserRole, seg["text"])
            self._timeline_table.setItem(row, 3, text_item)
        self._timeline_table.blockSignals(False)

    def on_timeline_double_clicked(self, row, col):
        if col == 3:
            self._timeline_table.editItem(self._timeline_table.item(row, col))

    def on_timeline_cell_changed(self, row, col):
        if col != 3:
            return
        segments = self.subtitle_segments.get()
        if not segments or row >= len(segments):
            return
        item = self._timeline_table.item(row, col)
        if item is None:
            return

        # Re-wrap the edit so it still obeys the line-width limit. Case and
        # censoring rules are deliberately not re-applied, and the two-line cap
        # is not enforced here either -- the user's typed text is taken as final,
        # and trimming it to fit would delete words they just typed. The cap
        # still governs everything the generator produces.
        try:
            max_chars = int(self.max_chars_per_line.get().strip())
        except (ValueError, AttributeError):
            max_chars = 42
        max_chars = max(1, max_chars)

        edited = item.text().replace(" | ", " ")
        new_text = "\n".join(wrap_text_to_lines(edited, max_chars))

        segments[row]["text"] = new_text
        self.subtitle_segments.set(segments)

        # Write the canonical text back without re-entering this handler.
        self._timeline_table.blockSignals(True)
        item.setData(Qt.ItemDataRole.UserRole, new_text)
        item.setText(new_text.replace("\n", " | "))
        self._timeline_table.blockSignals(False)

        self._preview_widget.set_subtitles(segments)
        self._preview_widget.update()

    def format_srt_time(self, seconds):
        return format_srt_timestamp(seconds)

    def export_srt_from_preview(self):
        segments = self.subtitle_segments.get()
        if not segments:
            self.log("No subtitles to export.")
            return

        input_name = os.path.splitext(os.path.basename(self.input_path.get().strip()))[0] or "output"
        default_dir = os.path.dirname(self.input_path.get().strip()) if self.input_path.get().strip() else ""
        default_path = os.path.join(default_dir, f"{input_name}.srt") if default_dir else f"{input_name}.srt"

        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Export Subtitles",
            default_path,
            "SRT Files (*.srt)",
        )
        if not output_file:
            return

        # Not every platform's save dialog appends the filter's extension.
        if not output_file.lower().endswith(".srt"):
            output_file += ".srt"

        self.write_srt_file(output_file, segments)
        self.log(f"Exported {len(segments)} subtitles to {output_file}")

    @staticmethod
    def format_time(seconds):
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02}:{s:02}"

    def get_default_advanced_settings(self):
        return {
            "beam_size": 5,
            "no_speech_threshold": 0.8,
            "condition_on_previous_text": False,
            "use_gpu": False,
            "vad_filter": True,
            "pause_threshold": 0.5,
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
        return MODEL_REPOS[model_name]

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
        marker = "✓" if model_name in self.installed_models else "✗"
        name = f"{model_name}"
        if model_name == "large-v3-turbo":
            name += " (Recommended)"
        return f"{marker} {name}"

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

        self.model_name.set(self.model_display_map[selected_display])
        self._update_model_action_buttons(self.model_display_map[selected_display])

    def on_model_selected(self, selected_display):
        model_name = self.model_display_map.get(selected_display)
        if model_name:
            self.model_name.set(model_name)
            self._update_model_action_buttons(model_name)

    def _update_model_action_buttons(self, model_name):
        installed = self.model_exists(model_name)
        busy = self.is_downloading or self.is_transcribing or self.is_deleting
        can_download = not installed and not busy
        self.download_btn.setEnabled(can_download)
        if installed:
            self.download_btn.setToolTip("Model already downloaded")
        elif busy:
            self.download_btn.setToolTip("Please wait for the current operation to finish")
        else:
            self.download_btn.setToolTip("Download the selected model")
        self.delete_btn.setEnabled(installed and not busy)

    def _validate_numeric_inputs(self):
        invalid_style = (
            "QLineEdit, QLineEdit:hover, QLineEdit:focus { border: 1px solid #CC5555; }"
        )
        try:
            val = int(self.max_words_per_subtitle.get().strip())
            if val < 1:
                raise ValueError
            self.max_words_entry.setStyleSheet("")
        except (ValueError, AttributeError):
            self.max_words_entry.setStyleSheet(invalid_style)
        try:
            val = int(self.max_chars_per_line.get().strip())
            if val < 1:
                raise ValueError
            self.max_chars_entry.setStyleSheet("")
        except (ValueError, AttributeError):
            self.max_chars_entry.setStyleSheet(invalid_style)

    def _is_supported_media(self, path):
        return bool(path) and path.lower().endswith(SUPPORTED_MEDIA_EXTENSIONS)

    def set_input_file(self, path):
        if not self._is_supported_media(path):
            self.log(
                f"Unsupported file type: {os.path.basename(path)}. "
                "Pick a supported audio or video file."
            )
            return
        self.input_path.set(path)
        self.input_entry.setText(path)
        self.log(f"Selected input file: {os.path.basename(path)}")

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
        )
        if path:
            self.set_input_file(path)

    # REAL DETECTION (load test)
    def model_exists(self, model_name):
        self.detect_installed_models()
        return model_name in self.installed_models

    # DOWNLOAD
    def download_model(self):
        if self.is_downloading or self.is_transcribing or self.is_deleting:
            self.log("Please wait for the current operation to finish.")
            return

        model_name = self.model_name.get()

        if self.model_exists(model_name):
            self.log(f"{model_name} already installed ✅")
            return

        required_mb = MODEL_SIZES_MB.get(model_name, 0)
        free_mb = get_free_space_mb(MODEL_DIR)
        if free_mb is not None and required_mb and free_mb < required_mb * 1.15:
            self.log(
                f"Not enough free disk space for {model_name}: needs about "
                f"{required_mb} MB, {int(free_mb)} MB available."
            )
            return

        self._cancelled = False
        self.is_downloading = True
        self.set_download_state(True, model_name)

        self.log(f"Downloading {model_name} (about {required_mb} MB) from {self.get_repo_id(model_name)}...")
        self.run_in_worker(lambda: self._download_worker(model_name), self.finish_download)

    def _download_worker(self, model_name):
        try:
            model_dir = self.get_model_dir(model_name)
            snapshot_download(
                repo_id=self.get_repo_id(model_name),
                local_dir=model_dir,
                max_workers=1,
                tqdm_class=make_progress_reporter(self._on_download_progress),
            )

            self.log(f"{model_name} installed ✅")
            self.log(f"Downloaded to: {model_dir}")

        except Exception as err:
            self.log(f"Error: {err}")

    def _on_download_progress(self, downloaded_bytes, total_bytes):
        # Called from the download thread; only touches a plain string that the
        # spinner timer picks up on the UI thread.
        if total_bytes:
            # hf_hub's aggregate bar starts at total=0 and grows as it fetches
            # metadata, so downloaded can briefly exceed the known total.
            downloaded_bytes = min(downloaded_bytes, total_bytes)
            percent = downloaded_bytes * 100 // total_bytes
            self.spinner_message = (
                f"Downloading {self.model_name.get()}... "
                f"{percent}% ({format_bytes(downloaded_bytes)} / {format_bytes(total_bytes)})"
            )
        else:
            self.spinner_message = (
                f"Downloading {self.model_name.get()}... {format_bytes(downloaded_bytes)}"
            )

    def finish_download(self):
        self.is_downloading = False
        self.refresh_model_menu()
        self.set_download_state(False)

    # SAFE DELETE
    def force_delete(self, path):
        def handler(func, target, _exc):
            try:
                os.chmod(target, stat.S_IWRITE)
                func(target)
            except Exception:
                pass

        # shutil deprecated `onerror` in favour of `onexc` in Python 3.12.
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=handler)
        else:
            shutil.rmtree(path, onerror=handler)

    def delete_model(self):
        if self.is_downloading or self.is_transcribing or self.is_deleting:
            self.log("Cannot delete while a model is in use ❌")
            return

        model_name = self.model_name.get()
        model_dir = self.get_model_dir(model_name)
        repo_cache_path = self.get_model_cache_path(model_name)

        if not os.path.isdir(model_dir) and not os.path.isdir(repo_cache_path):
            self.log("Model not found")
            return

        size_mb = MODEL_SIZES_MB.get(model_name)
        size_note = f" (about {size_mb} MB)" if size_mb else ""
        confirmed = QMessageBox.question(
            self,
            "Delete Model",
            f"Delete {model_name}{size_note}?\n\n"
            "It will have to be downloaded again before you can use it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        # Release the in-memory model first. On Windows CTranslate2 keeps
        # model.bin memory-mapped, which blocks deletion while it's loaded.
        if self._cached_model is not None and self._cached_model_name == model_name:
            self._cached_model = None
            self._cached_model_name = None
            self._cached_model_device = None
            self._cached_model_compute_type = None
            gc.collect()

        # Off the UI thread: removing large-v3 is several gigabytes of rmtree,
        # long enough for Windows to paint the window as "Not Responding".
        self.is_deleting = True
        self.set_delete_state(True, model_name)
        self.run_in_worker(
            lambda: self._delete_worker(model_name, model_dir, repo_cache_path),
            self.finish_delete,
        )

    def _delete_worker(self, model_name, model_dir, repo_cache_path):
        for path in (model_dir, repo_cache_path):
            if os.path.isdir(path):
                self.force_delete(path)

        # force_delete swallows per-file errors, so confirm rather than assume.
        if os.path.isdir(model_dir) or os.path.isdir(repo_cache_path):
            self.log(f"Could not fully delete {model_name}; some files are in use.")
        else:
            self.log(f"{model_name} deleted ❌")

        self._purge_download_cache_if_unused()

    def finish_delete(self):
        self.is_deleting = False
        self.refresh_model_menu()
        self.set_delete_state(False)

    def _purge_download_cache_if_unused(self):
        """Reclaim the Hugging Face Xet chunk cache once no models are left.

        Xet keeps deduplicated chunks that repos share, so this can only go when
        nothing remains that might still be relying on them. Left alone it
        survives every delete, so the app frees less space than it just said it
        would. Runs on the delete worker: the cache has its own multi-gigabyte
        ceiling, and clearing it is exactly as slow as the delete it follows.
        """
        if MODEL_DIR is None:
            return
        # Read the disk rather than self.installed_models: that is refreshed on
        # the UI thread after this worker finishes, so it is still stale here.
        if any(self.get_model_load_path(name) for name in self.available_models):
            return

        xet_cache = os.path.join(MODEL_DIR, "xet")
        if not os.path.isdir(xet_cache):
            return
        try:
            self.force_delete(xet_cache)
        except OSError:
            pass

    def start_transcription(self):
        if self.is_transcribing or self.is_downloading or self.is_deleting:
            self.log("Please wait for the current operation to finish.")
            return

        input_path = self.input_path.get().strip()
        model_name = self.model_name.get()
        subtitle_settings = self.get_subtitle_settings()

        if subtitle_settings is None:
            return

        if not input_path or not os.path.isfile(input_path):
            self.log("Pick a valid input audio/video file.")
            return

        if not self.model_exists(model_name):
            self.log(f"{model_name} is not installed. Download it first.")
            return

        model_path = self.get_model_load_path(model_name)
        if not model_path:
            self.log(f"{model_name} is not installed. Download it first.")
            return

        self._cancelled = False

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
            f"language={subtitle_settings['language_code'] or 'auto'}, "
            f"case={subtitle_settings['text_case']}, beam={subtitle_settings['beam_size']}, "
            f"no-speech={subtitle_settings['no_speech_threshold']:.1f}, "
            f"context={'on' if subtitle_settings['condition_on_previous_text'] else 'off'}, "
            f"vad={'on' if subtitle_settings['vad_filter'] else 'off'}"
        )
        self.run_in_worker(lambda: self.run_whisper(subtitle_settings), lambda: self.finish_transcription(subtitle_settings))

    def run_whisper(self, subtitle_settings):
        try:
            model_name = subtitle_settings["model_name"]
            model_path = subtitle_settings["model_path"]
            if not model_path:
                self.log(f"{model_name} is not installed. Download it first.")
                return

            use_gpu = subtitle_settings.get("use_gpu", False)
            desired_device = "cuda" if use_gpu else "cpu"
            desired_compute_type = "float16" if use_gpu else "int8"

            if (self._cached_model is None
                    or self._cached_model_name != model_name
                    or self._cached_model_device != desired_device
                    or self._cached_model_compute_type != desired_compute_type):
                if use_gpu:
                    try:
                        self._cached_model = WhisperModel(
                            model_path,
                            compute_type="float16",
                            device="cuda",
                            local_files_only=True,
                        )
                        self._cached_model_device = "cuda"
                        self._cached_model_compute_type = "float16"
                        self.log("Using GPU (CUDA) for transcription.")
                    except Exception:
                        self.log("GPU runtime not found, using CPU instead.")
                        self._cached_model = WhisperModel(
                            model_path,
                            compute_type="int8",
                            device="cpu",
                            local_files_only=True,
                        )
                        self._cached_model_device = "cpu"
                        self._cached_model_compute_type = "int8"
                else:
                    self._cached_model = WhisperModel(
                        model_path,
                        compute_type="int8",
                        device="cpu",
                        local_files_only=True,
                    )
                    self._cached_model_device = "cpu"
                    self._cached_model_compute_type = "int8"
                self._cached_model_name = model_name
            model = self._cached_model
            self.log(f"Model loaded. Processing audio... (device: {self._cached_model_device})")

            if self._cancel_event.is_set():
                self.log("Transcription cancelled before processing.")
                return

            use_word_timestamps = subtitle_settings["use_word_timestamps"]

            def _get_segments(m):
                gen, info = m.transcribe(
                    subtitle_settings["input_path"],
                    language=subtitle_settings["language_code"],
                    beam_size=subtitle_settings["beam_size"],
                    # Temperature fallback is Whisper's main defence against
                    # repetition loops: a window that trips the sanity checks
                    # below gets re-decoded at a higher temperature. Passing a
                    # single temperature disables the retry entirely, which
                    # makes the two thresholds below inert.
                    temperature=TEMPERATURE_FALLBACK,
                    compression_ratio_threshold=COMPRESSION_RATIO_THRESHOLD,
                    log_prob_threshold=LOG_PROB_THRESHOLD,
                    no_speech_threshold=subtitle_settings["no_speech_threshold"],
                    condition_on_previous_text=subtitle_settings["condition_on_previous_text"],
                    word_timestamps=use_word_timestamps,
                    # Only honoured when word timestamps are on.
                    hallucination_silence_threshold=(
                        HALLUCINATION_SILENCE_THRESHOLD if use_word_timestamps else None
                    ),
                    # Primes the decoder with words it would not otherwise
                    # predict. Benchmarking against hand-made captions showed
                    # it moving results by only a word or two either way on a
                    # 126-word clip, so it is offered as an opt-in tool rather
                    # than promised as a win. A generic description of the
                    # video measurably does not help; actual terms may.
                    initial_prompt=subtitle_settings.get("initial_prompt"),
                    vad_filter=subtitle_settings["vad_filter"],
                    vad_parameters={
                        "min_silence_duration_ms": subtitle_settings["vad_silence_ms"],
                        "min_speech_duration_ms": 100,
                        "speech_pad_ms": 400,
                    },
                )
                if subtitle_settings["language_code"] is None:
                    language_name = SUPPORTED_LANGUAGE_NAMES.get(info.language, info.language)
                    self.log(
                        f"Detected language: {language_name} "
                        f"({info.language}, {info.language_probability:.0%} confidence)"
                    )
                return gen

            def _run(m):
                return self.build_subtitle_segments(_get_segments(m), subtitle_settings)

            if self._cached_model_device == "cuda":
                try:
                    subtitle_segments = _run(model)
                except Exception as err:
                    # This guard covers transcription *and* subtitle building,
                    # so the cause is not necessarily CUDA. Report what actually
                    # failed rather than blaming the GPU runtime every time.
                    self.log(f"GPU transcription failed ({err}); retrying on CPU.")
                    self._cached_model = WhisperModel(
                        model_path,
                        compute_type="int8",
                        device="cpu",
                        local_files_only=True,
                    )
                    self._cached_model_device = "cpu"
                    self._cached_model_compute_type = "int8"
                    self._cached_model_name = model_name
                    model = self._cached_model
                    if self._cancel_event.is_set():
                        return
                    subtitle_segments = _run(model)
            else:
                subtitle_segments = _run(model)

            if self._cancel_event.is_set():
                self.log("Transcription cancelled during subtitle building.")
                return
            subtitle_segments, gap_warnings = normalize_subtitle_timings(subtitle_segments)
            for subtitle_number in gap_warnings:
                self.log(f"Large silent gap detected before subtitle {subtitle_number}.")
            if subtitle_settings.get("gap_fill"):
                subtitle_segments = apply_gap_fill(subtitle_segments)
            self.subtitle_preview_ready.emit(subtitle_segments)
            self.log(f"Created {len(subtitle_segments)} subtitle segments.")
            self.log("Edit subtitles in the Output tab, then click Export to save.")

        except Exception as err:
            self.log(f"Error: {err}")

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
        language_display = self.language_display.get()

        if beam_size <= 0:
            self.log("Beam size must be greater than 0.")
            return None

        if not 0.0 <= no_speech_threshold <= 1.0:
            self.log("No speech threshold must be between 0.0 and 1.0.")
            return None

        # Auto-detect is a valid choice and maps to None, so check membership
        # rather than truthiness.
        if language_display not in self.language_display_map:
            self.log("Pick a valid language.")
            return None

        language_code = self.language_display_map[language_display]

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
            "use_gpu": self.use_gpu.get(),
            "vad_filter": self.vad_filter.get(),
            "initial_prompt": self.vocabulary_hints.get().strip() or None,
            "gap_fill": self.gap_fill.get(),
            "censor_profanity": self.censor_profanity.get(),
        }

    def write_srt_file(self, output_file, subtitle_segments):
        self.log(f"Writing subtitles to {output_file}...")
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                entry_num = 0
                for seg in subtitle_segments:
                    text = seg["text"].strip()
                    if not text:
                        continue
                    entry_num += 1
                    f.write(f"{entry_num}\n")
                    f.write(f"{self.format_srt_time(seg['start'])} --> {self.format_srt_time(seg['end'])}\n")
                    f.write(f"{text}\n\n")
                    if entry_num % 25 == 0:
                        self.log(f"Wrote {entry_num} subtitle entries...")
        except OSError as err:
            self.log(f"Failed to write file: {err}")

    def build_subtitle_segments(self, segments, subtitle_settings):
        subtitle_segments = []
        for index, segment in enumerate(segments, start=1):
            if self._cancel_event.is_set():
                self.log("Transcription cancelled during subtitle building.")
                return subtitle_segments
            if subtitle_settings["use_word_timestamps"]:
                word_segments = self.build_word_timed_segments(segment, subtitle_settings)
                if word_segments:
                    subtitle_segments.extend(word_segments)
                    if index % 10 == 0:
                        self.log(
                            f"Processed {index} transcription segments, {len(subtitle_segments)} subtitles so far..."
                        )
                    continue

            subtitle_segments.extend(
                split_segment_text(
                    segment.text.strip(), segment.start, segment.end, subtitle_settings
                )
            )
            if index % 10 == 0:
                self.log(f"Processed {index} transcription segments, {len(subtitle_segments)} subtitles so far...")

        return subtitle_segments

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

            # Pause-based split: flush on long silence between words.
            if current_words:
                previous_word_end = getattr(current_words[-1], "end", None)
                if previous_word_end is not None and word_start - previous_word_end >= subtitle_settings["pause_threshold"]:
                    subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                    current_words = []

            # Line-overflow pre-check: if adding this word would exceed the line
            # budget, commit the current batch first so the overflowing word
            # starts the next subtitle rather than spilling into an extra line.
            if current_words:
                test_text = join_words(current_words + [word])
                if len(wrap_subtitle_lines(test_text, subtitle_settings)) > MAX_SUBTITLE_LINES:
                    subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                    current_words = []

            current_words.append(word)

            # Hard limits (post-add): the subtitle being built includes this word.
            last_word_text = current_words[-1].word.strip()

            if len(current_words) >= subtitle_settings["max_words"]:
                subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                current_words = []
            elif current_words[-1].end - current_words[0].start >= subtitle_settings["max_subtitle_duration"]:
                subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                current_words = []
            elif subtitle_settings["break_on_punctuation_immediate"] and last_word_text.endswith((".", "!", "?")):
                subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                current_words = []
            elif not subtitle_settings["break_on_punctuation_immediate"] and len(current_words) >= 3 and last_word_text.endswith((".", "!", "?", ",")):
                subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))
                current_words = []

        if current_words:
            subtitle_segments.append(self.create_subtitle_from_words(current_words, subtitle_settings))

        return [seg for seg in subtitle_segments if seg is not None]

    def create_subtitle_from_words(self, words, subtitle_settings):
        text = join_words(words)
        if not text:
            return None

        text = format_subtitle_text(text, subtitle_settings)
        if not text:
            return None

        return {
            "start": words[0].start,
            "end": words[-1].end,
            "text": text,
        }


def install_crash_handler():
    """Surface unhandled exceptions instead of losing them.

    The app ships windowed (console=False), so anything escaping a Qt slot would
    otherwise vanish to a stderr nobody can see, leaving a frozen-looking window.
    """
    log_path = resolve_log_file(APP_DIR)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        if log_path:
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    stamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
                    f.write(f"{stamp} UNHANDLED EXCEPTION\n{details}\n")
            except OSError:
                pass

        location = f"\n\nDetails were written to:\n{log_path}" if log_path else ""
        try:
            QMessageBox.critical(
                None,
                f"{APP_NAME} - Unexpected Error",
                f"{exc_type.__name__}: {exc_value}{location}",
            )
        except Exception:
            # A dialog may be impossible if Qt itself is the thing that broke.
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_exception


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    install_crash_handler()
    if MODEL_DIR is None:
        QMessageBox.critical(
            None,
            f"{APP_NAME} - Startup Error",
            f"Unable to create a writable models folder.\n\n{MODEL_DIR_ERROR}\n\n"
            "Please ensure the application has write permissions to its directory "
            "or to %LOCALAPPDATA%.",
        )
        sys.exit(1)
    apply_app_theme(app)
    window = WhisperApp()
    window.show()
    sys.exit(app.exec())
