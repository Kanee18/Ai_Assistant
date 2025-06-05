import threading
import tkinter as tk

# Engine and Recognizer
TTS_ENGINE = None
RECOGNIZER = None
TRAY_ICON = None
NLP = None
MATCHER = None
SPACY_MODEL_INITIALIZED = False

# Continuous Mode
is_continuous_mode_active = False
continuous_listen_thread = None
is_assistant_speaking = False

# Tkinter
main_tk_root = None
tray_icon_object = None
tray_icon_thread = None

# UI Settings
available_voices_display = []
available_voice_ids_settings_cache = []
mic_map_display_to_index = {"Default Sistem": None}

# Desktop Icon
desktop_icon_window = None
desktop_icon_label = None
desktop_icon_photo = None
desktop_icon_thread = None
desktop_icon_shutdown_event = threading.Event()
DESKTOP_ICON_IMAGE_PATH = "siri_style_icon.png"
MACOS_LIKE_ICON_BG_COLOR = 'lime green'

# Gemini and To-Do
gemini_chat_session = None
todo_list = []
GEMINI_API_KEY = "AIzaSyA2KXCsk6Z92gCu8GLeoPrXHvCyT9pP9iw"  # <-- Tambahkan API Key Anda di sini

# TTS Threading
tts_thread = None
tts_lock = threading.Lock()

# Audio
AUDIO_FILENAME = "temp_tts_output.wav"

# Settings Window
settings_window = None
settings_window_close_event = threading.Event()
MIC_INDEX = None
CONFIG_FILE = "assistant_config.json"