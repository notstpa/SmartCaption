import os
import sys
import threading
import shutil
import stat
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from huggingface_hub.utils import disable_progress_bars
from tkinterdnd2 import DND_FILES
from tkinterdnd2.TkinterDnD import DnDWrapper, _require

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

os.environ["HF_HOME"] = MODEL_DIR
os.environ["HF_HUB_CACHE"] = MODEL_DIR
os.environ["TRANSFORMERS_CACHE"] = MODEL_DIR
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

disable_progress_bars()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class OutputConflictDialog(ctk.CTkToplevel):
    def __init__(self, parent, file_path):
        super().__init__(parent)
        self.choice = None
        self.file_path = file_path

        self.title("Output File Exists")
        self.geometry("520x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        prompt = ctk.CTkLabel(
            self,
            text=(
                "The output file already exists.\n\n"
                f"{os.path.basename(file_path)}\n\n"
                "Do you want to overwrite it, create a renamed copy, or cancel?"
            ),
            justify="left",
            anchor="w",
            wraplength=460
        )
        prompt.grid(row=0, column=0, padx=20, pady=(20, 16), sticky="ew")

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        button_row.grid_columnconfigure((0, 1, 2), weight=1)

        overwrite_btn = ctk.CTkButton(button_row, text="Overwrite", command=lambda: self.finish("overwrite"))
        overwrite_btn.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        rename_btn = ctk.CTkButton(button_row, text="Rename", command=lambda: self.finish("rename"))
        rename_btn.grid(row=0, column=1, padx=8, sticky="ew")

        cancel_btn = ctk.CTkButton(button_row, text="Cancel", command=lambda: self.finish("cancel"))
        cancel_btn.grid(row=0, column=2, padx=(8, 0), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", lambda: self.finish("cancel"))
        self.after(10, lambda: self.finalize_dialog(parent))

    def finalize_dialog(self, parent):
        parent.center_window(self)
        self.focus()

    def finish(self, choice):
        self.choice = choice
        self.destroy()


class HelpTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.hide_job = None

        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.schedule_hide)
        self.widget.bind("<ButtonPress>", self.hide)
        self.widget.bind("<Destroy>", self.hide)

    def show(self, _event=None):
        if self.hide_job is not None:
            self.widget.after_cancel(self.hide_job)
            self.hide_job = None

        if self.tip_window is not None:
            return

        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
        y = self.widget.winfo_rooty() - 2

        self.tip_window = ctk.CTkToplevel(self.widget)
        self.tip_window.overrideredirect(True)
        self.tip_window.attributes("-topmost", True)
        self.tip_window.geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(
            self.tip_window,
            text=self.text,
            justify="left",
            anchor="w",
            wraplength=220,
            corner_radius=8,
            fg_color=("#f4f4f4", "#1f1f1f")
        )
        label.pack(padx=1, pady=1)
        self.tip_window.bind("<Leave>", self.hide)
        self.tip_window.bind("<ButtonPress>", self.hide)

    def schedule_hide(self, _event=None):
        if self.hide_job is not None:
            self.widget.after_cancel(self.hide_job)
        self.hide_job = self.widget.after(80, self.hide)

    def hide(self, _event=None):
        if self.hide_job is not None:
            self.widget.after_cancel(self.hide_job)
            self.hide_job = None
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class AdvancedOptionsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("Advanced Options")
        self.geometry("640x340")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, corner_radius=14)
        shell.grid(row=0, column=0, padx=18, pady=18, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(shell, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(14, 4), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header,
            text="Advanced Options",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")

        info_label = ctk.CTkLabel(
            header,
            text="A few expert controls for troubleshooting accuracy and pacing.",
            justify="left",
            anchor="w",
            text_color=("gray35", "gray70")
        )
        info_label.grid(row=1, column=0, pady=(4, 0), sticky="w")

        container = ctk.CTkFrame(shell, corner_radius=12)
        container.grid(row=1, column=0, padx=16, pady=(8, 10), sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        self.beam_size_menu = self.add_option_row(
            container,
            row=0,
            title="Beam Size",
            help_text="Beam size controls how many candidate transcriptions Whisper explores. Higher values usually help difficult audio, but increase processing time.",
            values=["1", "3", "5", "8", "10"],
            variable=parent.beam_size
        )

        self.no_speech_menu = self.add_option_row(
            container,
            row=1,
            title="No Speech Threshold",
            help_text="Higher values make Whisper more likely to skip quiet or uncertain sections. Lower values keep more borderline speech, which can help with soft voices but may add junk captions.",
            values=["0.3", "0.6", "0.8", "1.0"],
            variable=parent.no_speech_threshold
        )

        self.add_switch_row(
            container,
            row=2,
            title="Condition On Previous Text",
            help_text="When enabled, the model uses previous text as context for the next chunk. This can improve continuity, but sometimes carries mistakes forward.",
            variable=parent.condition_on_previous_text
        )

        footer_note = ctk.CTkLabel(
            shell,
            text="Defaults are usually the best choice for normal subtitle generation.",
            justify="left",
            anchor="w",
            text_color=("gray35", "gray70")
        )
        footer_note.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")

        button_row = ctk.CTkFrame(shell, fg_color="transparent")
        button_row.grid(row=3, column=0, padx=16, pady=(0, 14), sticky="ew")
        button_row.grid_columnconfigure((0, 1), weight=1)

        reset_button = ctk.CTkButton(button_row, text="Reset Defaults", command=self.reset_defaults)
        reset_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        close_button = ctk.CTkButton(button_row, text="Close", command=self.destroy)
        close_button.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        bottom_spacer = ctk.CTkFrame(shell, fg_color="transparent", height=12)
        bottom_spacer.grid(row=4, column=0, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(10, lambda: self.finalize_dialog(parent))

    def finalize_dialog(self, parent):
        parent.center_window(self)
        self.focus()

    def add_option_row(self, parent, row, title, help_text, values, variable):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, padx=18, pady=(12 if row == 0 else 6, 6), sticky="ew")
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, minsize=140)

        label_row = ctk.CTkFrame(row_frame, fg_color="transparent")
        label_row.grid(row=0, column=0, sticky="w")

        title_label = ctk.CTkLabel(label_row, text=title, font=ctk.CTkFont(size=14, weight="bold"))
        title_label.grid(row=0, column=0, sticky="w")

        help_button = ctk.CTkButton(
            label_row,
            text="?",
            width=22,
            height=22,
            corner_radius=11,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray78", "gray24"),
            hover_color=("gray70", "gray30"),
            text_color=("gray15", "white")
        )
        help_button.grid(row=0, column=1, padx=(8, 0), sticky="w")
        HelpTooltip(help_button, help_text)

        value_var = ctk.StringVar(value=self.format_option_value(variable.get()))
        option_menu = ctk.CTkOptionMenu(
            row_frame,
            values=values,
            variable=value_var,
            width=120,
            command=lambda selected, var=variable: self.on_option_change(var, selected)
        )
        option_menu.grid(row=0, column=1, padx=(10, 0), pady=(0, 0), sticky="e")
        return option_menu

    def add_switch_row(self, parent, row, title, help_text, variable):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, padx=18, pady=6, sticky="ew")
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, minsize=140)

        label_row = ctk.CTkFrame(row_frame, fg_color="transparent")
        label_row.grid(row=0, column=0, sticky="w")

        title_label = ctk.CTkLabel(label_row, text=title, font=ctk.CTkFont(size=14, weight="bold"))
        title_label.grid(row=0, column=0, sticky="w")

        help_button = ctk.CTkButton(
            label_row,
            text="?",
            width=22,
            height=22,
            corner_radius=11,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("gray78", "gray24"),
            hover_color=("gray70", "gray30"),
            text_color=("gray15", "white")
        )
        help_button.grid(row=0, column=1, padx=(8, 0), sticky="w")
        HelpTooltip(help_button, help_text)

        toggle = ctk.CTkSwitch(row_frame, text="", variable=variable)
        toggle.grid(row=0, column=1, padx=(10, 2), pady=(0, 0), sticky="e")

    def format_option_value(self, value):
        if isinstance(value, float):
            return f"{value:.1f}"
        return str(value)

    def on_option_change(self, variable, selected_value):
        if isinstance(variable, ctk.DoubleVar):
            variable.set(float(selected_value))
        else:
            variable.set(int(selected_value))

    def reset_defaults(self):
        defaults = self.parent.get_default_advanced_settings()
        self.parent.beam_size.set(defaults["beam_size"])
        self.parent.no_speech_threshold.set(defaults["no_speech_threshold"])
        self.parent.condition_on_previous_text.set(defaults["condition_on_previous_text"])
        self.destroy()
        self.parent.open_advanced_options()


class WhisperApp(ctk.CTk, DnDWrapper):
    def __init__(self):
        super().__init__()

        if os.path.exists(APP_ICON_PATH):
            try:
                self.iconbitmap(APP_ICON_PATH)
            except Exception:
                pass

        self.title(APP_NAME)
        self.geometry("900x600")
        self.withdraw()

        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.model_name = ctk.StringVar(value="small")
        self.model_display = ctk.StringVar()
        self.use_word_timestamps = ctk.BooleanVar(value=True)
        self.remove_punctuation = ctk.BooleanVar(value=False)
        self.text_case = ctk.StringVar(value="Normal")
        self.language_display = ctk.StringVar()
        self.max_words_per_subtitle = ctk.StringVar(value="8")
        self.max_chars_per_line = ctk.StringVar(value="42")
        self.beam_size = ctk.IntVar(value=5)
        self.no_speech_threshold = ctk.DoubleVar(value=0.6)
        self.condition_on_previous_text = ctk.BooleanVar(value=True)

        self.available_models = ["tiny", "base", "small", "medium", "large-v3"]
        self.model_display_map = {}
        self.installed_models = set()
        self.spinner_frames = ["|", "/", "-", "\\"]
        self.spinner_index = 0
        self.spinner_job = None
        self.spinner_message = "Idle"
        self.advanced_dialog = None
        self.language_display_map = {
            f"{SUPPORTED_LANGUAGE_NAMES[code]} ({code})": code for code in sorted(
                SUPPORTED_LANGUAGE_NAMES,
                key=lambda code: SUPPORTED_LANGUAGE_NAMES[code].lower()
            )
        }

        self.is_downloading = False
        self.is_transcribing = False

        _require(self)
        self.configure_ttk_styles()
        self.build_menu_bar()
        self.build_ui()
        self.log(f"Models folder: {MODEL_DIR}")
        if MODEL_DIR_MODE == "user":
            self.log("App folder is not writable, so models will be stored in your user profile.")
        self.after(10, self.show_centered)

    def build_menu_bar(self):
        self.menu_bar = ctk.CTkFrame(self, fg_color="#242424", corner_radius=0, height=28)
        self.menu_bar.grid(row=0, column=0, sticky="ew")
        self.menu_bar.grid_columnconfigure(99, weight=1)
        self.menu_bar.grid_propagate(False)

        self.options_popup_menu = tk.Menu(self, tearoff=0)
        self.options_popup_menu.add_command(label="Advanced Options", command=self.open_advanced_options)

        self.help_popup_menu = tk.Menu(self, tearoff=0)
        self.help_popup_menu.add_command(label="Best Accuracy Settings", command=self.show_best_accuracy_info)
        self.help_popup_menu.add_command(label="Accuracy Tips", command=self.show_accuracy_tips)
        self.help_popup_menu.add_separator()
        self.help_popup_menu.add_command(label="Supported Formats", command=self.show_supported_formats)
        self.help_popup_menu.add_command(label="Credits", command=self.show_credits_info)

        self.options_menu_button = ctk.CTkButton(
            self.menu_bar,
            text="Options",
            width=64,
            height=24,
            corner_radius=4,
            fg_color="transparent",
            text_color="#f2f2f2",
            hover_color="#343638",
            command=lambda: self.show_popup_menu(self.options_popup_menu, self.options_menu_button)
        )
        self.options_menu_button.grid(row=0, column=0, padx=(6, 4), pady=2, sticky="w")

        self.help_menu_button = ctk.CTkButton(
            self.menu_bar,
            text="Help",
            width=52,
            height=24,
            corner_radius=4,
            fg_color="transparent",
            text_color="#f2f2f2",
            hover_color="#343638",
            command=lambda: self.show_popup_menu(self.help_popup_menu, self.help_menu_button)
        )
        self.help_menu_button.grid(row=0, column=1, padx=(0, 4), pady=2, sticky="w")

    def show_popup_menu(self, menu, button):
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def configure_ttk_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "SmartCaption.TCombobox",
            fieldbackground="#343638",
            background="#343638",
            foreground="#f2f2f2",
            borderwidth=0,
            relief="flat",
            arrowsize=14,
            padding=4
        )
        style.map(
            "SmartCaption.TCombobox",
            fieldbackground=[("readonly", "#343638"), ("focus", "#343638"), ("!focus", "#343638")],
            background=[("readonly", "#343638"), ("focus", "#343638"), ("!focus", "#343638")],
            foreground=[("readonly", "#f2f2f2"), ("focus", "#f2f2f2"), ("!focus", "#f2f2f2")],
            selectbackground=[("readonly", "#343638"), ("focus", "#343638"), ("!focus", "#343638")],
            selectforeground=[("readonly", "#f2f2f2"), ("focus", "#f2f2f2"), ("!focus", "#f2f2f2")]
        )

    def show_best_accuracy_info(self):
        messagebox.showinfo(
            "Best Accuracy Settings",
            (
                "Best overall setup:\n\n"
                "Model: large-v3\n"
                "Beam Size: 8-10\n"
                "No Speech Threshold: 0.3-0.6\n"
                "Condition On Previous Text: On\n\n"
                "Recommended start:\n"
                "large-v3 + Beam Size 8 + No Speech Threshold 0.6 + Context On\n\n"
                "Max accuracy preset:\n"
                "large-v3 + Beam Size 10 + No Speech Threshold 0.3 + Context On"
            )
        )

    def show_accuracy_tips(self):
        messagebox.showinfo(
            "Accuracy Tips",
            (
                "Tips:\n\n"
                "- Missing quiet words: lower No Speech Threshold to 0.3.\n"
                "- Hard audio or accents: raise Beam Size to 10.\n"
                "- Repeats or carried mistakes: turn Context off.\n\n"
                "Tradeoffs:\n\n"
                "- large-v3 gives the best accuracy.\n"
                "- Higher Beam Size is slower on CPU.\n"
                "- Lower No Speech Threshold keeps more speech, but may add noise.\n"
                "- Context usually helps continuity in longer speech."
            )
        )

    def show_supported_formats(self):
        messagebox.showinfo(
            "Supported Formats",
            (
                "Supported formats:\n\n"
                "Audio: mp3, wav, m4a, flac, aac, ogg, wma\n"
                "Video: mp4, mkv, mov, avi, webm, mpeg, mpg, m4v\n\n"
                "You can also drag and drop supported files.\n"
                "Actual support depends on the decoding libraries included in the build."
            )
        )

    def show_credits_info(self):
        messagebox.showinfo(
            "Credits",
            (
                "This app uses open-source software, including:\n\n"
                "- CustomTkinter\n"
                "- faster-whisper\n"
                "- CTranslate2\n"
                "- huggingface_hub\n"
                "- tkinterdnd2\n"
                "- PyAV\n"
                "- NumPy\n"
                "- tokenizers\n"
                "- tqdm\n\n"
                "For redistribution, include THIRD_PARTY_NOTICES.md with the app."
            )
        )

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)

        self.input_btn = ctk.CTkButton(file_frame, text="Input", command=self.pick_input)
        self.input_btn.grid(row=0, column=0, padx=10)

        self.input_entry = ctk.CTkEntry(file_frame, textvariable=self.input_path)
        self.input_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.output_btn = ctk.CTkButton(file_frame, text="Output", command=self.pick_output)
        self.output_btn.grid(row=1, column=0, padx=10)

        self.output_entry = ctk.CTkEntry(file_frame, textvariable=self.output_path)
        self.output_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.setup_drag_and_drop()

        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        options_frame.grid_columnconfigure((0, 1, 2), weight=1)

        model_frame = ctk.CTkFrame(options_frame)
        model_frame.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="nsew")
        model_frame.grid_columnconfigure(0, weight=1)

        self.model_section_label = ctk.CTkLabel(model_frame, text="Model")
        self.model_section_label.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        self.model_menu = ctk.CTkOptionMenu(
            model_frame,
            variable=self.model_display,
            values=[],
            command=self.on_model_selected
        )
        self.model_menu.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.refresh_model_menu()

        self.download_btn = ctk.CTkButton(model_frame, text="Download", command=self.download_model)
        self.download_btn.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")

        self.delete_btn = ctk.CTkButton(model_frame, text="Delete Model", command=self.delete_model)
        self.delete_btn.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="ew")

        timing_frame = ctk.CTkFrame(options_frame)
        timing_frame.grid(row=0, column=1, padx=6, pady=12, sticky="nsew")
        timing_frame.grid_columnconfigure(1, weight=1)

        self.timing_section_label = ctk.CTkLabel(timing_frame, text="Timing")
        self.timing_section_label.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")

        self.word_timestamps_checkbox = ctk.CTkCheckBox(
            timing_frame,
            text="Word-level subtitle timing",
            variable=self.use_word_timestamps
        )
        self.word_timestamps_checkbox.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

        self.max_words_label = ctk.CTkLabel(timing_frame, text="Max words")
        self.max_words_label.grid(row=2, column=0, padx=(12, 8), pady=(0, 8), sticky="w")

        self.max_words_entry = ctk.CTkEntry(
            timing_frame,
            textvariable=self.max_words_per_subtitle,
            width=60
        )
        self.max_words_entry.grid(row=2, column=1, padx=(0, 12), pady=(0, 8), sticky="ew")

        self.max_chars_label = ctk.CTkLabel(timing_frame, text="Max chars/line")
        self.max_chars_label.grid(row=3, column=0, padx=(12, 8), pady=(0, 12), sticky="w")

        self.max_chars_entry = ctk.CTkEntry(
            timing_frame,
            textvariable=self.max_chars_per_line,
            width=60
        )
        self.max_chars_entry.grid(row=3, column=1, padx=(0, 12), pady=(0, 12), sticky="ew")

        text_frame = ctk.CTkFrame(options_frame)
        text_frame.grid(row=0, column=2, padx=(6, 12), pady=12, sticky="nsew")
        text_frame.grid_columnconfigure(1, weight=1)

        self.text_section_label = ctk.CTkLabel(text_frame, text="Text")
        self.text_section_label.grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")

        self.remove_punctuation_checkbox = ctk.CTkCheckBox(
            text_frame,
            text="Remove punctuation",
            variable=self.remove_punctuation
        )
        self.remove_punctuation_checkbox.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

        self.text_case_label = ctk.CTkLabel(text_frame, text="Text case")
        self.text_case_label.grid(row=2, column=0, padx=(12, 8), pady=(0, 12), sticky="w")

        self.text_case_menu = ctk.CTkOptionMenu(
            text_frame,
            variable=self.text_case,
            values=["Normal", "lowercase", "UPPERCASE"]
        )
        self.text_case_menu.grid(row=2, column=1, padx=(0, 12), pady=(0, 12), sticky="ew")

        self.language_label = ctk.CTkLabel(text_frame, text="Language")
        self.language_label.grid(row=3, column=0, padx=(12, 8), pady=(0, 12), sticky="w")

        language_values = list(self.language_display_map.keys())
        english_display = next(
            display for display, code in self.language_display_map.items() if code == "en"
        )
        self.language_display.set(english_display)

        self.language_menu = ttk.Combobox(
            text_frame,
            textvariable=self.language_display,
            values=language_values,
            state="readonly",
            height=12,
            style="SmartCaption.TCombobox"
        )
        self.language_menu.grid(row=3, column=1, padx=(0, 12), pady=(0, 12), sticky="ew")

        self.download_status = ctk.StringVar(value="Idle")
        self.download_status_label = ctk.CTkLabel(self, textvariable=self.download_status, anchor="w")
        self.download_status_label.grid(row=3, column=0, padx=(24, 140), pady=(0, 6), sticky="ew")

        self.generate_btn = ctk.CTkButton(
            self,
            text="Generate",
            command=self.start_transcription,
            width=120
        )
        self.generate_btn.grid(row=3, column=0, padx=24, pady=(0, 6), sticky="e")

        self.log_box = ctk.CTkTextbox(self)
        self.log_box.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.grid_rowconfigure(4, weight=1)

    def _append_log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def log(self, text):
        self.after(0, lambda text=text: self._append_log(text))

    def show_centered(self):
        self.geometry("900x600")
        self.update_idletasks()
        self.minsize(900, 600)
        self.maxsize(self.winfo_screenwidth(), self.winfo_screenheight())
        self.center_window(self)
        self.deiconify()
        self.update_idletasks()
        self.center_window(self)
        self.lift()
        self.focus_force()

    def setup_drag_and_drop(self):
        for widget in (self, self.input_entry):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.handle_file_drop)

    def center_window(self, window):
        window.update_idletasks()

        width = window.winfo_width()
        height = window.winfo_height()

        if width <= 1 or height <= 1:
            geometry = window.geometry().split("+")[0]
            if "x" in geometry:
                width_str, height_str = geometry.split("x", 1)
                try:
                    width = int(width_str)
                    height = int(height_str)
                except ValueError:
                    width = max(window.winfo_reqwidth(), 1)
                    height = max(window.winfo_reqheight(), 1)
            else:
                width = max(window.winfo_reqwidth(), 1)
                height = max(window.winfo_reqheight(), 1)

        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def set_download_state(self, active, model_name=None):
        def update_ui():
            if active:
                self.start_status_spinner(f"Downloading {model_name}...")
                self.download_btn.configure(state="disabled")
                self.generate_btn.configure(state="disabled")
                self.delete_btn.configure(state="disabled")
                self.model_menu.configure(state="disabled")
            else:
                self.stop_status_spinner()
                self.download_btn.configure(state="normal")
                self.generate_btn.configure(state="normal")
                self.delete_btn.configure(state="normal")
                self.model_menu.configure(state="normal")

        self.after(0, update_ui)

    def start_status_spinner(self, message):
        self.spinner_message = message
        self.spinner_index = 0
        self.download_status.set(f"{self.spinner_frames[self.spinner_index]} {self.spinner_message}")
        if self.spinner_job is not None:
            self.after_cancel(self.spinner_job)
        self.spinner_job = self.after(120, self.schedule_spinner)

    def stop_status_spinner(self):
        if self.spinner_job is not None:
            self.after_cancel(self.spinner_job)
            self.spinner_job = None
        self.spinner_message = "Idle"
        self.download_status.set("Idle")

    def schedule_spinner(self):
        if not self.is_downloading and not self.is_transcribing:
            self.spinner_job = None
            return

        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        self.download_status.set(f"{self.spinner_frames[self.spinner_index]} {self.spinner_message}")
        self.spinner_job = self.after(120, self.schedule_spinner)

    def set_transcription_state(self, active):
        def update_ui():
            self.is_transcribing = active
            if active:
                self.start_status_spinner("Transcribing...")
                self.generate_btn.configure(state="disabled")
                self.download_btn.configure(state="disabled")
                self.delete_btn.configure(state="disabled")
                self.model_menu.configure(state="disabled")
                self.word_timestamps_checkbox.configure(state="disabled")
                self.remove_punctuation_checkbox.configure(state="disabled")
                self.text_case_menu.configure(state="disabled")
                self.language_menu.configure(state="disabled")
                self.max_words_entry.configure(state="disabled")
                self.max_chars_entry.configure(state="disabled")
            else:
                self.stop_status_spinner()
                self.generate_btn.configure(state="normal")
                self.download_btn.configure(state="normal")
                self.delete_btn.configure(state="normal")
                self.model_menu.configure(state="normal")
                self.word_timestamps_checkbox.configure(state="normal")
                self.remove_punctuation_checkbox.configure(state="normal")
                self.text_case_menu.configure(state="normal")
                self.language_menu.configure(state="readonly")
                self.max_words_entry.configure(state="normal")
                self.max_chars_entry.configure(state="normal")

        self.after(0, update_ui)

    def get_default_advanced_settings(self):
        return {
            "beam_size": 5,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": True,
        }

    def open_advanced_options(self):
        if self.advanced_dialog is not None and self.advanced_dialog.winfo_exists():
            self.advanced_dialog.focus()
            return

        self.advanced_dialog = AdvancedOptionsDialog(self)
        self.advanced_dialog.bind("<Destroy>", self.on_advanced_dialog_destroy, add="+")

    def on_advanced_dialog_destroy(self, event):
        if event.widget is self.advanced_dialog:
            self.advanced_dialog = None

    def get_repo_id(self, model_name):
        return f"{MODEL_REPO_PREFIX}{model_name}"

    def get_model_cache_path(self, model_name):
        safe_repo_name = self.get_repo_id(model_name).replace("/", "--")
        return os.path.join(MODEL_DIR, f"models--{safe_repo_name}")

    def detect_installed_models(self):
        installed_models = set()

        for model_name in self.available_models:
            repo_cache_path = self.get_model_cache_path(model_name)
            snapshots_path = os.path.join(repo_cache_path, "snapshots")
            if os.path.isdir(snapshots_path):
                try:
                    if any(os.scandir(snapshots_path)):
                        installed_models.add(model_name)
                except OSError:
                    pass

        self.installed_models = installed_models

    def get_model_display_name(self, model_name):
        marker = "✓" if model_name in self.installed_models else "x"
        return f"{marker} {model_name}"

    def refresh_model_menu(self):
        self.detect_installed_models()
        current_model = self.model_name.get()
        display_values = [self.get_model_display_name(model) for model in self.available_models]
        self.model_display_map = dict(zip(display_values, self.available_models))
        self.model_menu.configure(values=display_values)

        selected_display = next(
            (display for display, model in self.model_display_map.items() if model == current_model),
            display_values[0]
        )
        self.model_display.set(selected_display)
        self.model_name.set(self.model_display_map[selected_display])

    def on_model_selected(self, selected_display):
        model_name = self.model_display_map.get(selected_display)
        if model_name:
            self.model_name.set(model_name)

    def set_input_file(self, path):
        self.input_path.set(path)
        self.output_path.set(os.path.dirname(path))
        self.log(f"Selected input file: {os.path.basename(path)}")
        self.log(f"Output folder set to: {self.output_path.get()}")

    def pick_input(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Supported media", " ".join(f"*{ext}" for ext in SUPPORTED_MEDIA_EXTENSIONS)),
                ("Audio files", "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.wma"),
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.mpeg *.mpg *.m4v"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.set_input_file(path)

    def pick_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def handle_file_drop(self, event):
        try:
            paths = self.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]

        if not paths:
            return "copy"

        file_path = paths[0].strip().strip("{}")
        if not os.path.isfile(file_path):
            self.log("Drop a file onto the input field or app window.")
            return "copy"

        self.set_input_file(file_path)
        return "copy"

    # ✅ REAL DETECTION (load test)
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

        threading.Thread(target=self._download_worker, args=(model_name,), daemon=True).start()

    def _download_worker(self, model_name):
        try:
            snapshot_download(
                repo_id=self.get_repo_id(model_name),
                cache_dir=MODEL_DIR,
                max_workers=1,
                tqdm_class=None
            )

            self.after(0, self.refresh_model_menu)
            self.after(0, lambda: self.log(f"{model_name} installed ✅"))

        except Exception as err:
            self.after(0, lambda err=err: self.log(f"Error: {err}"))

        self.after(0, self.finish_download)

    def finish_download(self):
        self.is_downloading = False
        self.set_download_state(False)

    # SAFE DELETE
    def force_delete(self, path):
        def onerror(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except:
                pass

        shutil.rmtree(path, onerror=onerror)

    def delete_model(self):
        if self.is_downloading:
            self.log("Cannot delete while downloading ❌")
            return

        model_name = self.model_name.get()
        repo_cache_path = self.get_model_cache_path(model_name)
        deleted = False

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

        subtitle_settings["output_file"] = output_file
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
        threading.Thread(target=self.run_whisper, args=(subtitle_settings,), daemon=True).start()

    def run_whisper(self, subtitle_settings):
        try:
            model = WhisperModel(
                self.model_name.get(),
                compute_type="int8",
                device="cpu",
                download_root=MODEL_DIR,
                local_files_only=True
            )
            self.log("Model loaded. Processing audio...")

            use_word_timestamps = subtitle_settings["use_word_timestamps"]
            segments, _ = model.transcribe(
                self.input_path.get(),
                language=subtitle_settings["language_code"],
                beam_size=subtitle_settings["beam_size"],
                best_of=5,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=subtitle_settings["no_speech_threshold"],
                condition_on_previous_text=subtitle_settings["condition_on_previous_text"],
                word_timestamps=use_word_timestamps
            )

            subtitle_segments = self.build_subtitle_segments(segments, subtitle_settings)
            self.log(f"Created {len(subtitle_segments)} subtitle segments.")

            output_file = subtitle_settings["output_file"]
            self.write_srt_file(output_file, subtitle_segments)
            self.log(f"Done! Saved {len(subtitle_segments)} subtitles.")

        except Exception as err:
            self.log(f"Error: {err}")
        finally:
            self.after(0, lambda: self.set_transcription_state(False))

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
        self.wait_window(dialog)
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
        duration = words[-1].end - words[0].start
        last_word = words[-1].word.strip()

        if len(words) >= subtitle_settings["max_words"]:
            return True
        if len(text) >= subtitle_settings["max_chars"]:
            return True
        if duration >= 3.2:
            return True
        if len(words) >= 3 and last_word.endswith((".", "!", "?", ",")):
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
        if not text:
            return ""

        if subtitle_settings["remove_punctuation"]:
            text = text.translate(str.maketrans("", "", ".,'?!"))

        if subtitle_settings["text_case"] == "lowercase":
            text = text.lower()
        elif subtitle_settings["text_case"] == "UPPERCASE":
            text = text.upper()

        return " ".join(text.split())



if __name__ == "__main__":
    app = WhisperApp()
    app.mainloop()
