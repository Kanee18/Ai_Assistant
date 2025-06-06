import threading
import tkinter as tk
import os  
from dotenv import load_dotenv  

load_dotenv()

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Spotify API Credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID") 
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET") 
SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback" 

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