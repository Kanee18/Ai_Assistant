import pystray
from PIL import Image, ImageDraw, ImageFont, ImageTk
import speech_recognition as sr
import pyttsx3
import pygame 
import threading
import time
import google.generativeai as genai
import os
import requests 
import json     
import subprocess 
import sys 
import tkinter as tk 
import re
import cv2
import spacy 
import pygetwindow as gw 
from spacy.matcher import Matcher 
from tkinter import ttk, messagebox 

TTS_ENGINE = None
RECOGNIZER = None
TRAY_ICON = None 
NLP = None 
MATCHER = None 
SPACY_MODEL_INITIALIZED = False 
is_continuous_mode_active = False
continuous_listen_thread = None
is_assistant_speaking = False
main_tk_root = None
tray_icon_object = None
tray_icon_thread = None

available_voices_display = []
available_voice_ids_settings_cache = []
mic_map_display_to_index = {"Default Sistem": None}

desktop_icon_window = None
desktop_icon_label = None
desktop_icon_photo = None 
desktop_icon_thread = None
desktop_icon_shutdown_event = threading.Event()
DESKTOP_ICON_IMAGE_PATH = "siri_style_icon.png" 
MACOS_LIKE_ICON_BG_COLOR = 'lime green' 

OWM_API_KEY = "1d74db05478bcfd86603446160cf4d36" 
GEMINI_API_KEY = "AIzaSyDEF9aODiHNEqQHzHm3zOYLEIGRTomx68Q" 
DEFAULT_LOCATION_WEATHER = "Indonesia" 

gemini_chat_session = None
GEMINI_MODEL_INITIALIZED = False
todo_list = [] 

is_continuous_mode_active = False 
continuous_listen_thread = None
is_assistant_speaking = False 
tts_thread = None 
tts_lock = threading.Lock() 

AUDIO_FILENAME = "temp_tts_output.wav" 

settings_window = None 
settings_window_close_event = threading.Event() 
MIC_INDEX = None 
CONFIG_FILE = "assistant_config.json"

def _destroy_settings_window():
    """Fungsi untuk menghancurkan jendela pengaturan jika ada, memastikan settings_window direset."""
    global settings_window
    try:
        if settings_window and settings_window.winfo_exists():
            print("  _destroy_settings_window: Mencoba menghancurkan jendela pengaturan yang ada.")
            try:
                settings_window.grab_release()
                print("    Settings window: grab_release() berhasil.")
            except tk.TclError as e_grab:
                print(f"    Settings window: Error saat grab_release: {e_grab}")
            try:
                settings_window.destroy()
                print("    Settings window: Jendela berhasil dihancurkan.")
            except tk.TclError as e_destroy:
                print(f"    Settings window: Error saat destroy: {e_destroy}")
        elif settings_window:
            print("  _destroy_settings_window: settings_window ada tapi winfo_exists() false.")
        else:
            print("  _destroy_settings_window: Tidak ada settings_window untuk dihancurkan.")
            
    except Exception as e_outer:
        print(f"  _destroy_settings_window: Error tak terduga selama proses destroy: {e_outer}")
    finally:
        settings_window = None
        print("  Variabel global settings_window DIJAMIN di-reset ke None (dalam blok finally).")

def _create_actual_settings_gui():
    global settings_window, main_tk_root, TTS_ENGINE, MIC_INDEX
    global available_voices_display, available_voice_ids_settings_cache, mic_map_display_to_index

    if not main_tk_root:
        print("Error (_create_actual_settings_gui): Root Tkinter utama belum siap.")
        return

    if settings_window is not None and settings_window.winfo_exists():
        print("Jendela pengaturan sudah ada (menurut .winfo_exists()), mencoba memulihkan.")
        revived_successfully = False
        try:
            current_state = settings_window.state()
            is_mapped = settings_window.winfo_ismapped()
            geom = "N/A"
            try: geom = settings_window.geometry()
            except tk.TclError: geom = "Error saat ambil geometri"

            print(f"  Info Jendela Saat Ini: ID={settings_window}, State='{current_state}', Terpetakan='{is_mapped}', Geometri='{geom}'")

            if current_state == 'withdrawn' or not is_mapped:
                print(f"    Jendela dalam kondisi '{current_state}' atau tidak terpetakan. Mencoba 'deiconify'.")
                settings_window.deiconify()
            
            settings_window.lift()
            settings_window.focus_set()
            
            settings_window.update_idletasks()
            win_width = settings_window.winfo_width()
            win_height = settings_window.winfo_height()

            if win_width <= 1 or geom.startswith("1x1"): win_width = 650 
            if win_height <= 1 or geom.startswith("1x1"): win_height = 300
            
            scr_width = settings_window.winfo_screenwidth()
            scr_height = settings_window.winfo_screenheight()
            new_x = (scr_width // 2) - (win_width // 2)
            new_y = (scr_height // 2) - (win_height // 2)
            
            print(f"    Mengatur ulang geometri ke: {win_width}x{win_height}+{new_x}+{new_y}")
            settings_window.geometry(f"{win_width}x{win_height}+{new_x}+{new_y}")
            
            settings_window.grab_set()

            settings_window.update_idletasks() 
            if settings_window.winfo_ismapped() and settings_window.state() == 'normal':
                revived_successfully = True
                print("    Jendela pengaturan berhasil dipulihkan dan ditampilkan.")
            else:
                print(f"  PERINGATAN SETELAH PEMULIHAN: State='{settings_window.state()}', Terpetakan='{settings_window.winfo_ismapped()}'")
                print("  Gagal memulihkan jendela pengaturan agar terlihat sepenuhnya.")

        except tk.TclError as e:
            print(f"    Error Tcl saat memulihkan jendela pengaturan yang ada: {e}")
        
        if not revived_successfully:
            print("    Upaya pemulihan gagal. Memaksa penghancuran jendela pengaturan yang bermasalah.")
            _destroy_settings_window() 
        else:
            return 

    if settings_window is None: 
        print("Membuat instance BARU untuk jendela pengaturan...")
        
        available_voices_display.clear()
        available_voice_ids_settings_cache.clear()
        mic_map_display_to_index.clear()
        mic_map_display_to_index["Default Sistem"] = None

        if not TTS_ENGINE:
            print("TTS Engine N/A, batal buka pengaturan baru.")
            if main_tk_root and main_tk_root.winfo_exists():
                messagebox.showerror("Error TTS", "Mesin TTS tidak aktif. Pengaturan tidak bisa dibuka.", 
                                     parent=main_tk_root if main_tk_root.winfo_exists() else None)
            return

        settings_window = tk.Toplevel(main_tk_root)
        settings_window.title("Pengaturan Suara & Mikrofon")
        settings_window.geometry("650x300") 
        settings_window.resizable(False, False)
        #try:
            #settings_window.transient(main_tk_root)
        #except tk.TclError:
            #print("Info: Gagal set transient, mungkin karena root utama tersembunyi.")
            #pass

        main_frame = ttk.Frame(settings_window, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        tts_frame = ttk.LabelFrame(main_frame, text="Output Suara (TTS)", padding="10")

        tts_frame = ttk.LabelFrame(main_frame, text="Output Suara (TTS)", padding="10")
        tts_frame.pack(pady=10, fill=tk.X)
        ttk.Label(tts_frame, text="Pilih Suara:").pack(side=tk.LEFT, padx=5, pady=5, anchor='w')
        if TTS_ENGINE:
            voices_props = TTS_ENGINE.getProperty('voices')
            for voice in voices_props:
                lang_str = ", ".join([lang.decode('utf-8', 'ignore') for lang in voice.languages]) if voice.languages else "N/A"
                display_name = f"{voice.name} (Lang: {lang_str})"
                available_voices_display.append(display_name)
                available_voice_ids_settings_cache.append(voice.id)
        selected_voice_display_str = tk.StringVar() 
        voice_dropdown = ttk.Combobox(tts_frame, textvariable=selected_voice_display_str, values=available_voices_display, state="readonly", width=60)
        if TTS_ENGINE:
            current_voice_id_tts = TTS_ENGINE.getProperty('voice')
            try:
                current_voice_idx_in_list = available_voice_ids_settings_cache.index(current_voice_id_tts)
                selected_voice_display_str.set(available_voices_display[current_voice_idx_in_list])
            except (ValueError, IndexError):
                if available_voices_display: selected_voice_display_str.set(available_voices_display[0])
                else: selected_voice_display_str.set("Tidak ada suara"); voice_dropdown.config(state="disabled")
        else: selected_voice_display_str.set("TTS tidak aktif"); voice_dropdown.config(state="disabled")
        voice_dropdown.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

        mic_frame = ttk.LabelFrame(main_frame, text="Input Audio (Mikrofon)", padding="10")
        mic_frame.pack(pady=10, fill=tk.X)
        ttk.Label(mic_frame, text="Pilih Mikrofon:").pack(side=tk.LEFT, padx=5, pady=5, anchor='w')
        mic_display_list = ["Default Sistem"]
        try:
            mic_list_from_sr = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(mic_list_from_sr):
                display_name = f"{idx}: {name[:55]}"
                mic_display_list.append(display_name)
                mic_map_display_to_index[display_name] = idx
        except Exception as e: print(f"Gagal dapat daftar mic: {e}")
        selected_mic_display_str = tk.StringVar() 
        mic_dropdown = ttk.Combobox(mic_frame, textvariable=selected_mic_display_str, values=mic_display_list, state="readonly", width=60)
        current_mic_set_display = "Default Sistem"
        if MIC_INDEX is not None:
            for display_name_key, idx_val_map in mic_map_display_to_index.items():
                if idx_val_map == MIC_INDEX: current_mic_set_display = display_name_key; break
        selected_mic_display_str.set(current_mic_set_display)
        mic_dropdown.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20, side=tk.BOTTOM, fill=tk.X)
        cancel_btn = ttk.Button(button_frame, text="Batal", command=_destroy_settings_window)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))
        apply_btn = ttk.Button(button_frame, text="Terapkan & Tutup",
            command=lambda: apply_settings_tk(selected_voice_display_str.get(),selected_mic_display_str.get(),settings_window))
        apply_btn.pack(side=tk.RIGHT, padx=(0,10))

        def on_closing_settings_via_x():
            print("Tombol X jendela pengaturan ditekan.")
            _destroy_settings_window()
        
        settings_window.protocol("WM_DELETE_WINDOW", on_closing_settings_via_x)
        
        print("Mencoba deiconify jendela pengaturan yang baru dibuat...")
        settings_window.deiconify() 
        
        try:
            settings_window.grab_set()
            settings_window.focus_set() 
            print("Jendela pengaturan baru berhasil di-grab dan fokus di-set.")
        except tk.TclError as e:
            print(f"Error saat grab_set/focus_set pada jendela pengaturan baru: {e}")
        
        print(f"Status jendela baru setelah dibuat: State='{settings_window.state()}', Terpetakan='{settings_window.winfo_ismapped()}'")

    else: 
        print("Kondisi tidak terduga: settings_window bukan None tapi juga tidak winfo_exists(). Memanggil _destroy_settings_window.")
        _destroy_settings_window()

def _create_desktop_icon_window():
    global desktop_icon_window, desktop_icon_label, desktop_icon_photo

    try:
        root = tk.Tk()
        desktop_icon_window = root 
        root.title("Tes Ikon Asisten - KOTAK MERAH") 
        root.withdraw()

        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)

        DEBUG_FRAME_COLOR = "red" 
        debug_width = 150  
        debug_height = 150 

        root.config(bg=DEBUG_FRAME_COLOR) 

        try:
            pil_image = Image.open(DESKTOP_ICON_IMAGE_PATH)
            desktop_icon_photo = ImageTk.PhotoImage(pil_image)
        except FileNotFoundError:
            print(f"ERROR: Desktop icon image not found at {DESKTOP_ICON_IMAGE_PATH}")
            speak_with_pygame(f"Icon image not found.") 
            desktop_icon_shutdown_event.set() 
            return
        except Exception as e:
            print(f"ERROR: Could not load desktop icon image: {e}")
            desktop_icon_shutdown_event.set()
            return

        root.config(bg=MACOS_LIKE_ICON_BG_COLOR)
        root.attributes("-transparentcolor", MACOS_LIKE_ICON_BG_COLOR)

        desktop_icon_label = tk.Label(root, image=desktop_icon_photo, bg=MACOS_LIKE_ICON_BG_COLOR)
        desktop_icon_label.pack()

        root.update_idletasks() 
        
        window_width = debug_width
        window_height = debug_height

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_pos = (screen_width // 2) - (window_width // 2)
        y_pos = screen_height - window_height - 100 
        root.geometry(f'{window_width}x{window_height}+{x_pos}+{y_pos}')

        print("Jendela ikon (DEBUG KOTAK MERAH) dibuat dan diposisikan.") 

        while not desktop_icon_shutdown_event.is_set():
            if root.winfo_exists():
                root.update()
            else: 
                break
            time.sleep(0.05)

    except tk.TclError as e:
        if "application has been destroyed" not in str(e).lower():
            print(f"TclError di thread ikon desktop: {e}")
    except Exception as e:
        print(f"Error di thread ikon desktop: {e}")
    finally:
        if desktop_icon_window and desktop_icon_window.winfo_exists():
            try:
                desktop_icon_window.destroy()
            except tk.TclError:
                pass 
        desktop_icon_window = None 
        print("Thread ikon desktop (DEBUG KOTAK MERAH) selesai.") 

def create_desktop_icon_tk(parent_root):
    """
    Membuat jendela Toplevel untuk ikon desktop, tersembunyi awalnya.
    Dipanggil sekali saat startup.
    """
    global desktop_icon_window, desktop_icon_label, desktop_icon_photo, main_tk_root 

    if not parent_root:
        print("ERROR (create_desktop_icon_tk): Root Tkinter utama (parent_root) tidak ada.")
        return

    if desktop_icon_window and desktop_icon_window.winfo_exists():
        print("INFO (create_desktop_icon_tk): Jendela ikon desktop lama ditemukan, menghancurkan...")
        desktop_icon_window.destroy()
        desktop_icon_window = None

    desktop_icon_window = tk.Toplevel(parent_root)
    desktop_icon_window.withdraw() 

    desktop_icon_window.overrideredirect(True) 
    desktop_icon_window.wm_attributes("-topmost", True) 

    try:
        print(f"INFO (create_desktop_icon_tk): Mencoba memuat gambar dari '{DESKTOP_ICON_IMAGE_PATH}'")
        pil_image = Image.open(DESKTOP_ICON_IMAGE_PATH)
        print(f"  Gambar dimuat: Ukuran={pil_image.size}, Mode={pil_image.mode}")

        desktop_icon_photo = ImageTk.PhotoImage(pil_image)
    
    except FileNotFoundError:
        print(f"KRITIS (create_desktop_icon_tk): File gambar ikon '{DESKTOP_ICON_IMAGE_PATH}' tidak ditemukan.")
        if main_tk_root and main_tk_root.winfo_exists():
            main_tk_root.after(0, lambda: messagebox.showerror("Error Gambar Ikon Desktop", f"File gambar '{DESKTOP_ICON_IMAGE_PATH}' tidak ditemukan. Ikon tidak akan tampil.", parent=main_tk_root))
        if desktop_icon_window and desktop_icon_window.winfo_exists(): desktop_icon_window.destroy()
        desktop_icon_window = None
        return
    except Exception as e:
        print(f"KRITIS (create_desktop_icon_tk): Tidak bisa memuat atau memproses gambar ikon: {e}")
        if main_tk_root and main_tk_root.winfo_exists():
            main_tk_root.after(0, lambda: messagebox.showerror("Error Gambar Ikon Desktop", f"Tidak bisa memuat gambar ikon: {e}", parent=main_tk_root))
        if desktop_icon_window and desktop_icon_window.winfo_exists(): desktop_icon_window.destroy()
        desktop_icon_window = None
        return

    desktop_icon_window.config(bg=MACOS_LIKE_ICON_BG_COLOR)
    desktop_icon_window.attributes("-transparentcolor", MACOS_LIKE_ICON_BG_COLOR)

    if desktop_icon_label and desktop_icon_label.winfo_exists():
        desktop_icon_label.destroy()
        
    desktop_icon_label = tk.Label(desktop_icon_window, image=desktop_icon_photo, bg=MACOS_LIKE_ICON_BG_COLOR)
    desktop_icon_label.pack() 

    desktop_icon_window.update_idletasks()
    
    print(f"INFO (create_desktop_icon_tk): Objek Toplevel ikon desktop telah dibuat (tersembunyi). Ukuran awal dari gambar: {desktop_icon_window.winfo_width()}x{desktop_icon_window.winfo_height()}")


def _set_icon_position():
    if desktop_icon_window and desktop_icon_window.winfo_exists():
        desktop_icon_window.update_idletasks() 
        
        window_width = desktop_icon_window.winfo_width()
        window_height = desktop_icon_window.winfo_height()
        
        if window_width <= 1 or window_height <= 1:
            print(f"PERINGATAN (_set_icon_position): Ukuran jendela ikon tidak valid ({window_width}x{window_height}). Mungkin gambar gagal render. Ikon tidak akan diposisikan/ditampilkan dengan benar.")
            return 

        screen_width = desktop_icon_window.winfo_screenwidth()
        screen_height = desktop_icon_window.winfo_screenheight()
        
        x_pos = (screen_width // 2) - (window_width // 2)
        y_pos = screen_height - window_height - 100 
        
        desktop_icon_window.geometry(f'+{x_pos}+{y_pos}') 
        print(f"INFO (_set_icon_position): Posisi ikon desktop diatur ke X:{x_pos}, Y:{y_pos} (Ukuran jendela: {window_width}x{window_height})")
    else:
        print("PERINGATAN (_set_icon_position): Jendela ikon desktop tidak ada untuk diatur posisinya.")

def show_desktop_icon():
    global main_tk_root
    
    def _show():
        global desktop_icon_window 
        print("DEBUG (show_desktop_icon._show): Dipanggil.")
        if desktop_icon_window and desktop_icon_window.winfo_exists():
            print(f"  Jendela ikon ada. State awal: {desktop_icon_window.state()}, Terpetakan: {desktop_icon_window.winfo_ismapped()}")
            _set_icon_position() 
            desktop_icon_window.deiconify() 
            desktop_icon_window.lift() 
            print(f"  Ikon desktop di-deiconify dan lift. State akhir: {desktop_icon_window.state()}, Terpetakan: {desktop_icon_window.winfo_ismapped()}")
            if not desktop_icon_window.winfo_ismapped():
                print("  PERINGATAN (_show): Ikon desktop MASIH tidak terpetakan setelah deiconify/lift.")
        elif not desktop_icon_window:
            print("ERROR (_show): Tidak bisa menampilkan ikon, objek jendela ikon adalah None (mungkin gagal dibuat).")
        else: 
            print("ERROR (_show): Tidak bisa menampilkan ikon, jendela ikon sudah dihancurkan.")

    if main_tk_root:
        main_tk_root.after(0, _show)
    else:
        print("KRITIS (show_desktop_icon): main_tk_root tidak tersedia.")


def hide_desktop_icon():
    global main_tk_root
    
    def _hide():
        global desktop_icon_window
        print("DEBUG (hide_desktop_icon._hide): Dipanggil.")
        if desktop_icon_window and desktop_icon_window.winfo_exists():
            desktop_icon_window.withdraw() 
            print(f"  Ikon desktop di-withdraw. State: {desktop_icon_window.state()}, Terpetakan: {desktop_icon_window.winfo_ismapped()}")
        else:
            print("  Tidak ada jendela ikon desktop untuk disembunyikan atau sudah dihancurkan.")
            
    if main_tk_root:
        main_tk_root.after(0, _hide)
    else:
        print("KRITIS (hide_desktop_icon): main_tk_root tidak tersedia.")

def save_configuration(voice_id, mic_idx):
    config = {"voice_id": voice_id, "mic_index": mic_idx}
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Konfigurasi berhasil disimpan ke {CONFIG_FILE}")
    except Exception as e:
        print(f"Gagal menyimpan konfigurasi: {e}")

def load_configuration():
    global MIC_INDEX 
    voice_id_from_config = None
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            print(f"Konfigurasi dimuat dari {CONFIG_FILE}: {config}")
            
            mic_idx_cfg = config.get("mic_index")
            if isinstance(mic_idx_cfg, int):
                MIC_INDEX = mic_idx_cfg
            elif mic_idx_cfg is None: 
                MIC_INDEX = None
            else:
                print(f"Peringatan: mic_index di config ('{mic_idx_cfg}') tidak valid, menggunakan default.")
                MIC_INDEX = None 
            
            voice_id_from_config = config.get("voice_id")
        except Exception as e:
            print(f"Gagal memuat atau mem-parse konfigurasi dari {CONFIG_FILE}: {e}")
            MIC_INDEX = None 
    else:
        print(f"File konfigurasi {CONFIG_FILE} tidak ditemukan. Menggunakan pengaturan default.")
        MIC_INDEX = None 
    
    return voice_id_from_config

def define_spacy_patterns():
    global MATCHER, NLP
    if not MATCHER or not NLP: 
        print("SpaCy Matcher atau NLP model belum siap untuk mendefinisikan pola.") 
        return

    pattern_open_app = [
        {"LOWER": {"IN": ["buka", "jalankan", "aktifkan"]}},
        {"LOWER": "aplikasi", "OP": "?"}, 
        {"IS_ALPHA": True, "OP": "+"} 
    ]
    MATCHER.add("OPEN_APPLICATION_SPACY", [pattern_open_app])

    pattern_search_info_1 = [ 
        {"LOWER": {"IN": ["cari", "carikan"]}}, 
        {"LOWER": "informasi", "OP": "?"}, 
        {"LOWER": {"IN": ["tentang", "mengenai"]}}, 
        {"OP": "+"}  
    ]
    pattern_search_info_2 = [ 
        {"LOWER": "apa"}, 
        {"LOWER": "itu"}, 
        {"OP": "+"}
    ]
    pattern_search_info_3 = [ 
        {"LOWER": {"IN": ["jelaskan", "terangkan"]}}, 
        {"LOWER": {"IN": ["tentang", "mengenai"]}, "OP": "?"}, 
        {"OP": "+"}
    ]
    MATCHER.add("SEARCH_INFO_SPACY", [pattern_search_info_1, pattern_search_info_2, pattern_search_info_3])
    
    print("Pola-pola spaCy Matcher telah didefinisikan.")


def initialize_spacy_model():
    global NLP, MATCHER, SPACY_MODEL_INITIALIZED 
    if SPACY_MODEL_INITIALIZED: 
        print("Model spaCy sudah diinisialisasi sebelumnya.")
        return
    try:
        NLP = spacy.load("en_core_web_sm") 
        print("Model spaCy 'en_core_web_sm' berhasil dimuat.")
        MATCHER = Matcher(NLP.vocab)
        define_spacy_patterns() 
        SPACY_MODEL_INITIALIZED = True
    except OSError:
        print("KRITIS: Gagal memuat model spaCy 'en_core_web_sm'.")
        print("Pastikan Anda sudah mengunduhnya dengan: python -m spacy download en_core_web_sm")
        NLP = None; MATCHER = None; SPACY_MODEL_INITIALIZED = False
    except Exception as e:
        print(f"Error saat memuat model spaCy atau membuat Matcher: {e}")
        NLP = None; MATCHER = None; SPACY_MODEL_INITIALIZED = False

def initialize_engines(preferred_voice_id=None):
    global TTS_ENGINE, RECOGNIZER, gemini_chat_session, GEMINI_MODEL_INITIALIZED, pygame, SPACY_MODEL_INITIALIZED
    
    print("Menginisialisasi Pygame dan Pygame Mixer...")
    try:
        pygame.init(); pygame.mixer.init(); print("Pygame dan Pygame Mixer berhasil diinisialisasi.")
    except Exception as e: print(f"KRITIS: Gagal inisialisasi Pygame: {e}")

    print("Menginisialisasi mesin Text-to-Speech (TTS)...")
    try:
        TTS_ENGINE = pyttsx3.init(); TTS_ENGINE.setProperty('rate', 165) 
        if preferred_voice_id:
            try: TTS_ENGINE.setProperty('voice', preferred_voice_id); print(f"Suara dari konfigurasi diterapkan: {preferred_voice_id}")
            except Exception as e: print(f"Gagal menerapkan suara dari konfigurasi ({preferred_voice_id}): {e}. Mencari default Indo."); set_default_indonesian_voice()
        else: set_default_indonesian_voice()
        print("Mesin TTS berhasil diinisialisasi.")
    except Exception as e: print(f"KRITIS: Gagal inisialisasi TTS: {e}"); TTS_ENGINE = None

    if not SPACY_MODEL_INITIALIZED:
        initialize_spacy_model()

    print("Menginisialisasi Speech Recognizer..."); RECOGNIZER = sr.Recognizer(); print("Speech Recognizer berhasil diinisialisasi.")

    print("Menginisialisasi Model AI Gemini...")
    if GEMINI_API_KEY and GEMINI_API_KEY != "MASUKKAN_API_KEY_GEMINI_ANDA_YANG_VALID": 
        try:
            genai.configure(api_key=GEMINI_API_KEY); model = genai.GenerativeModel('gemini-1.5-flash-latest')
            initial_history = [
                {'role':'user', 'parts': ["Kamu adalah \"Asisten Cerdas Kanee\"."]}, 
                {'role':'model', 'parts': ["Baik, saya Kane."]}
            ]
            gemini_chat_session = model.start_chat(history=initial_history); GEMINI_MODEL_INITIALIZED = True
            print("Model Gemini dan sesi chat berhasil diinisialisasi.")
        except Exception as e: print(f"Kesalahan konfigurasi Gemini: {e}"); gemini_chat_session = None; GEMINI_MODEL_INITIALIZED = False
    else: print("PERINGATAN: API Key Gemini belum diatur."); GEMINI_MODEL_INITIALIZED = False

def set_default_indonesian_voice():
    global TTS_ENGINE
    if not TTS_ENGINE: return
    voices = TTS_ENGINE.getProperty('voices'); found_indonesian_voice = False
    for voice in voices:
        if "indonesian" in voice.name.lower() or any(lang in voice.languages for lang in [[b'id'], [b'id_ID']]):
            try: TTS_ENGINE.setProperty('voice', voice.id); print(f"Menggunakan suara TTS: {voice.name}"); found_indonesian_voice = True; break
            except Exception: pass 
    if not found_indonesian_voice: print("Tidak ditemukan suara TTS Indo, pakai default sistem.")

def speak_with_pygame(text_to_speak):
    global TTS_ENGINE, is_assistant_speaking, tts_thread, tts_lock, pygame, AUDIO_FILENAME
    if not TTS_ENGINE: print(f"Asisten (TTS engine N/A): {text_to_speak}"); return
    if not pygame.mixer.get_init(): print(f"Asisten (Pygame mixer N/A): {text_to_speak}"); return
    
    def _save_and_play_in_thread(current_text):
        global is_assistant_speaking, tts_lock, tts_thread, TTS_ENGINE, pygame, AUDIO_FILENAME
        thread_name = threading.current_thread().name; acquired_lock_for_flag_init = False; sound_played_successfully = False
        try:
            if not tts_lock.acquire(timeout=1.0): print(f"TTS Thread {thread_name}: Gagal lock awal, batal."); return 
            acquired_lock_for_flag_init = True; is_assistant_speaking = True; tts_lock.release(); acquired_lock_for_flag_init = False 
            
            print(f"Asisten (simpan file - thread {thread_name}): {current_text}")
            TTS_ENGINE.save_to_file(current_text, AUDIO_FILENAME); TTS_ENGINE.runAndWait(); print(f"Audio disimpan: {AUDIO_FILENAME}")
            
            with tts_lock: 
                if not is_assistant_speaking: print(f"TTS Thread {thread_name}: Interupsi saat simpan."); return 
            
            if not pygame.mixer.get_init(): print(f"TTS Thread {thread_name}: Pygame mixer mati saat akan putar."); return

            pygame.mixer.music.load(AUDIO_FILENAME); pygame.mixer.music.play(); sound_played_successfully = True
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
                with tts_lock: 
                    if not is_assistant_speaking: 
                        print(f"Thread TTS {thread_name}: Sinyal interupsi diterima saat audio diputar.")
                        pygame.mixer.music.stop()
                        
                        if hasattr(pygame.mixer.music, 'unload'):
                            try:
                                print(f"Thread TTS {thread_name}: Mencoba unload musik setelah interupsi...")
                                pygame.mixer.music.unload()
                                print(f"Thread TTS {thread_name}: File musik di-unload dari mixer (setelah interupsi).")
                            except pygame.error as e_unload_int: 
                                print(f"Thread TTS {thread_name}: Pygame error saat unload (setelah interupsi): {e_unload_int}")
                            except Exception as e_unload_general_int: 
                                print(f"Thread TTS {thread_name}: Error umum saat unload (setelah interupsi): {e_unload_general_int}")
                        break 
            
            if sound_played_successfully and not pygame.mixer.music.get_busy() and is_assistant_speaking: print(f"TTS Thread {thread_name}: Audio selesai normal.")
            elif pygame.mixer.music.get_busy(): pygame.mixer.music.stop(); print(f"TTS Thread {thread_name}: Musik stop paksa di akhir.")
            
            if sound_played_successfully and hasattr(pygame.mixer.music, 'unload'):
                try: time.sleep(0.05); pygame.mixer.music.unload(); print(f"TTS Thread {thread_name}: File {AUDIO_FILENAME} di-unload.")
                except pygame.error as e: print(f"TTS Thread {thread_name}: Pygame error unload '{AUDIO_FILENAME}': {e}")
        except Exception as e: print(f"Error simpan/putar (thread {thread_name}): {e}")
        finally:
            if os.path.exists(AUDIO_FILENAME):
                print(f"Hapus file: {AUDIO_FILENAME}"); time.sleep(0.2) 
                for i in range(5): 
                    try: os.remove(AUDIO_FILENAME); print(f"File {AUDIO_FILENAME} hapus percobaan {i+1} sukses."); break 
                    except PermissionError as e_perm:
                        if i == 4: print(f"Gagal total hapus {AUDIO_FILENAME} (PermissionError): {e_perm}")
                        else: print(f"Gagal hapus percobaan ke-{i+1} (PermissionError), coba lagi..."); time.sleep(0.3 + (i*0.1)) 
                    except Exception as e_del: print(f"Gagal hapus percobaan ke-{i+1} (Error Lain): {e_del}"); break 
            
            if acquired_lock_for_flag_init and tts_lock.locked(): 
                 tts_lock.release() 
            
            with tts_lock: 
                if threading.current_thread() is tts_thread: 
                    is_assistant_speaking = False
            print(f"Asisten (selesai proses audio - thread {thread_name}): {current_text}")

    if not tts_lock.acquire(timeout=0.5): print("Speak_pygame: Gagal lock utama, speak batal."); 
    try:
        if tts_thread and tts_thread.is_alive():
            print("Speak_pygame: Thread TTS lama aktif, stop musiknya...");
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
            is_assistant_speaking = False; tts_thread.join(timeout=0.3) 
            if tts_thread.is_alive(): print("Speak_pygame: Peringatan, thread TTS lama masih hidup.")
        
        tts_thread = threading.Thread(target=_save_and_play_in_thread, args=(text_to_speak,), name=f"PygameTTS-{int(time.time())}")
        tts_thread.daemon = True; tts_thread.start()
    finally:
        tts_lock.release()

def process_nlu(text):
    global NLP, MATCHER, SPACY_MODEL_INITIALIZED 

    if not text: return {"intent": "NO_INPUT", "entities": {}}
    text_lower = text.lower() 

    if SPACY_MODEL_INITIALIZED and NLP and MATCHER:
        doc = NLP(text_lower) 
        matches = MATCHER(doc)

        for match_id, start, end in matches:
            span = doc[start:end]  
            intent_name_spacy = NLP.vocab.strings[match_id]  

            if intent_name_spacy == "OPEN_APPLICATION_SPACY":
                app_name_tokens = []
                if len(span) > 1 and span[1].lower_ == "aplikasi": 
                    app_name_tokens = span[2:] 
                elif len(span) > 0: 
                    app_name_tokens = span[1:]
                
                app_name_parts = [token.text for token in app_name_tokens if token.is_alpha or token.is_digit]
                app_name = " ".join(app_name_parts).strip()

                if app_name: 
                    return {"intent": "OPEN_APPLICATION", "entities": {"app_name": app_name}}
                else: 
                     return {"intent": "OPEN_APPLICATION_PROMPT", "entities": {}}

            elif intent_name_spacy == "SEARCH_INFO_SPACY":
                topic_tokens = []
                if span[0].lower_ in ["cari", "carikan"]: 
                    idx_start_topic = 2
                    if span[1].lower_ in ["tentang", "mengenai"]:
                        idx_start_topic = 2
                    elif span[1].lower_ == "informasi" and len(span) > 2 and span[2].lower_ in ["tentang", "mengenai"]:
                         idx_start_topic = 3
                    topic_tokens = span[idx_start_topic:]
                elif span[0].lower_ == "apa" and span[1].lower_ == "itu": 
                    topic_tokens = span[2:]
                elif span[0].lower_ in ["jelaskan", "terangkan"]: 
                    if len(span) > 1 and span[1].lower_ in ["tentang", "mengenai"]:
                        topic_tokens = span[2:]
                    else:
                        topic_tokens = span[1:]
                        
                topic = " ".join([token.text for token in topic_tokens]).strip()
                if topic: 
                    return {"intent": "SEARCH_INFO", "entities": {"topic": topic}}
        print(f"Tidak ada pola spaCy Matcher yang cocok untuk: '{text_lower}'. Mencoba keyword spotting...")


    if any(word in text_lower for word in ["selamat tinggal", "keluar program", "berhenti program"]):
        return {"intent": "GOODBYE_APP", "entities": {}}
    if "siapa namamu" in text_lower: 
        return {"intent": "GET_NAME", "entities": {}}
    if any(word in text_lower for word in ["jam berapa", "pukul berapa"]):
        return {"intent": "GET_TIME", "entities": {}}
    
    if NLP is None or MATCHER is None or not SPACY_MODEL_INITIALIZED: 
         match_open_app_fallback = re.search(r"^(?:buka|jalankan)\s+(?:aplikasi\s+)?(.+)", text_lower)
         if match_open_app_fallback:
             app_name = match_open_app_fallback.group(1).strip()
             if app_name: return {"intent": "OPEN_APPLICATION", "entities": {"app_name": app_name}}
    
    if any(phrase in text_lower for phrase in ["apa judul jendela ini", "judul jendela aktif", "jendela apa yang aktif", "apa nama window ini", "sebutkan judul window"]):
        return {"intent": "GET_ACTIVE_WINDOW_TITLE", "entities": {}}

    return {"intent": "ASK_AI", "entities": {"prompt": text}}

def handle_open_application(entities):
    app_name = entities.get("app_name")
    if not app_name: return "Aplikasi apa? Katakan 'buka aplikasi [nama]'."
    app_name_cleaned = app_name 
    app_map = {"notepad": "notepad.exe", "kalkulator": "calc.exe", "paint": "mspaint.exe","google chrome": "chrome.exe", 
               "chrome": "chrome.exe", "edge": "msedge.exe","word": "winword.exe", "excel": "excel.exe", "powerpoint": 
               "powerpnt.exe", "cmd": "cmd.exe", "command prompt": "cmd.exe", "file explorer": "explorer.exe", "explorer": 
               "explorer.exe", "spotify": "spotify.exe",}
    command_to_run = app_map.get(app_name_cleaned.lower(), app_name_cleaned)
    command_to_run_exe = None
    if not command_to_run.lower().endswith(".exe") and command_to_run not in app_map.values() and " " not in command_to_run: command_to_run_exe = f"{command_to_run}.exe"
    response_msg = f"Aplikasi {app_name} seharusnya sedang dibuka." 
    try: print(f"Mencoba: {command_to_run}"); subprocess.Popen(command_to_run, shell=True)
    except FileNotFoundError:
        if command_to_run_exe and command_to_run_exe != command_to_run:
            try: print(f"Gagal, mencoba: {command_to_run_exe}"); subprocess.Popen(command_to_run_exe, shell=True)
            except FileNotFoundError: response_msg = f"Tidak ditemukan '{app_name}'/'{command_to_run_exe}'."
            except Exception as e: response_msg = f"Error buka {app_name} (.exe): {e}"
        else: response_msg = f"Tidak ditemukan '{app_name}'."
    except Exception as e: response_msg = f"Error buka {app_name}: {e}"
    return response_msg

def handle_get_active_window_title():
    try:
        active_window = gw.getActiveWindow()
        if active_window:
            if active_window.title:
                print(f"Judul jendela aktif terdeteksi: {active_window.title}")
                return f"Jendela yang sedang aktif berjudul: {active_window.title}"
            else:
                print("Jendela aktif tidak memiliki judul.")
                return "Jendela yang aktif saat ini tidak memiliki judul."
        else:
            print("Tidak ada jendela aktif yang terdeteksi.")
            return "Maaf, saya tidak dapat mendeteksi jendela yang aktif saat ini."
    except Exception as e:
        print(f"Error saat mendapatkan judul jendela aktif: {e}")
        return "Maaf, terjadi kesalahan saat mencoba mendapatkan judul jendela."

def send_to_gemini_chat(user_prompt):
    global gemini_chat_session, GEMINI_MODEL_INITIALIZED
    
    if not GEMINI_MODEL_INITIALIZED or not gemini_chat_session: 
        return "Maaf, AI belum siap."
    if not user_prompt: 
        return "Tidak ada pertanyaan untuk AI."
    
    try:
        print(f"Kirim ke Gemini: {user_prompt}")
        response = gemini_chat_session.send_message(user_prompt)
        
        if response.parts: 
            return response.text
        
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            block_reason_msg = getattr(response.prompt_feedback, 'block_reason_message', '')
            return f"Permintaan Anda diblokir oleh AI: {block_reason_msg}."
        
        return "Hmm, AI tidak memberikan jawaban yang valid atau responsnya kosong."

    except Exception as e:
        print(f"Error saat berkomunikasi dengan Gemini: {e}")
        return "Maaf, terjadi masalah saat berkomunikasi dengan AI."


def initial_ambient_noise_adjustment():
    global RECOGNIZER, MIC_INDEX
    if not RECOGNIZER: return
    mic_to_use_idx = MIC_INDEX if MIC_INDEX is not None else None
    mic_display_name = f"indeks {MIC_INDEX}" if MIC_INDEX is not None else "default"
    try:
        with sr.Microphone(device_index=mic_to_use_idx) as source:
            print(f"Kalibrasi mic {mic_display_name} (2 detik)...")
            RECOGNIZER.adjust_for_ambient_noise(source, duration=2)
            print(f"Threshold mic {mic_display_name}: {RECOGNIZER.energy_threshold:.2f}")
    except Exception as e: 
        print(f"Peringatan: Gagal kalibrasi mic {mic_display_name}: {e}.")
        if MIC_INDEX is not None: 
            print("Mencoba kalibrasi mic default...")
            try:
                with sr.Microphone(device_index=None) as source_default:
                    RECOGNIZER.adjust_for_ambient_noise(source_default, duration=2)
                    print(f"Threshold mic default: {RECOGNIZER.energy_threshold:.2f}")
            except Exception as e_default: print(f"Gagal kalibrasi mic default juga: {e_default}")

def continuous_conversation_loop():
    global is_continuous_mode_active, RECOGNIZER, TRAY_ICON, GEMINI_MODEL_INITIALIZED, is_assistant_speaking, tts_thread, tts_lock, pygame, MIC_INDEX
    initial_ambient_noise_adjustment(); consecutive_timeouts = 0 
    while is_continuous_mode_active:
        if not RECOGNIZER: print("Recognizer N/A..."); time.sleep(1); 
        print("\n[Percakapan Aktif] Menunggu..."); command_text = None
        try:
            with sr.Microphone(device_index=MIC_INDEX if MIC_INDEX is not None else None) as source:
                try:
                    print("Mendengarkan..."); audio = RECOGNIZER.listen(source, timeout=7, phrase_time_limit=10)
                    print("Audio diterima, mengenali..."); command_text = RECOGNIZER.recognize_google(audio, language='id-ID')
                    print(f"Anda: {command_text}"); consecutive_timeouts = 0 
                    if is_assistant_speaking and command_text: 
                        interruption_command = command_text.lower()
                        if any(word in interruption_command for word in ["stop", "berhenti", "diam", "cukup", "sudah"]):
                            print(f"INTERUPSI: '{interruption_command}'")
                            with tts_lock: 
                                    if pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                                    if hasattr(pygame.mixer.music, 'unload'): 
                                        try: 
                                            print(f"Thread TTS: Mencoba unload musik setelah interupsi di dalam listen...") 
                                            pygame.mixer.music.unload()
                                            print(f"Thread TTS: Musik di-unload (interupsi dalam listen).")
                                        except pygame.error as e_unload_inner: 
                                            print(f"Thread TTS: Pygame error saat unload (interupsi dalam listen): {e_unload_inner}")
                                            pass 
                                        is_assistant_speaking = False 
                            speak_with_pygame("Baik."); time.sleep(1.0); continue 
                except sr.WaitTimeoutError: 
                    print("Timeout (tidak ada ucapan).")
                    consecutive_timeouts += 1
                    if consecutive_timeouts >= 3: 
                        print("Banyak timeout, kalibrasi ulang...")
                        initial_ambient_noise_adjustment() 
                        consecutive_timeouts = 0 
                    continue 

                except sr.UnknownValueError: 
                    consecutive_timeouts = 0 
                    if not is_assistant_speaking: 
                        print("Tidak dapat memahami audio.")
                        speak_with_pygame("Hmm, kurang jelas. Ulangi?")
                    else: 
                        print("Audio tak dikenali saat AI bicara.")
                    continue 

                except sr.RequestError as e: 
                    consecutive_timeouts = 0
                    print(f"Masalah layanan STT; {e}")
                    if not is_assistant_speaking: 
                        speak_with_pygame("Masalah koneksi layanan suara.")
                    time.sleep(3) 
                    continue 

                except Exception as e: 
                    consecutive_timeouts = 0
                    print(f"Error listen/recognize: {e}")
                    if not is_assistant_speaking: 
                        speak_with_pygame("Error saat mendengarkan.")
                    continue 

            if command_text and not is_assistant_speaking: 
                nlu_result = process_nlu(command_text)
                intent = nlu_result["intent"]; entities = nlu_result["entities"]
                assistant_response = "Maaf, saya tidak paham." 
                print(f"Intent: {intent}, Entities: {entities}")

                if intent == "GOODBYE_APP":
                    assistant_response = "Baik, sampai jumpa!"
                    speak_with_pygame(assistant_response); time.sleep(1.5) 
                    is_continuous_mode_active = False 
                    if TRAY_ICON: TRAY_ICON.stop(); break 
                elif intent == "GET_NAME": assistant_response = "Saya Widya, asisten Windows."
                elif intent == "GET_TIME":
                    current_time = time.strftime("%A, %d %B %Y, pukul %H:%M WITA") 
                    assistant_response = f"Sekarang hari {current_time}."
                elif intent == "OPEN_APPLICATION":
                    speak_with_pygame(f"Mencoba membuka {entities.get('app_name','aplikasi tersebut')}.") 
                    time.sleep(0.3) 
                    assistant_response = handle_open_application(entities) 
                elif intent == "OPEN_APPLICATION_PROMPT":
                    assistant_response = "Aplikasi apa? Katakan 'buka aplikasi [nama]'."

                elif intent == "GET_ACTIVE_WINDOW_TITLE":
                    assistant_response = handle_get_active_window_title()

                elif intent == "SEARCH_INFO": 
                    topic = entities.get("topic")
                    if topic:
                        speak_with_pygame(f"Baik, mencari informasi tentang {topic}...")
                        search_prompt = f"Jelaskan secara ringkas dan jelas tentang {topic} dalam Bahasa Indonesia."
                        assistant_response = send_to_gemini_chat(search_prompt)
                    else:
                        assistant_response = "Topik apa yang ingin Anda cari informasinya?"

                elif intent == "ASK_AI":
                    if not GEMINI_MODEL_INITIALIZED: assistant_response = "Fitur AI belum aktif."
                    else: assistant_response = send_to_gemini_chat(entities["prompt"])
                speak_with_pygame(assistant_response)
            if not is_continuous_mode_active: break
        except sr.RequestError as e: print(f"Mic Error: {e}"); speak_with_pygame("Masalah mic. Mode stop."); is_continuous_mode_active=False; break
        except Exception as e: print(f"Loop Error: {e}"); speak_with_pygame("Error. Mode stop."); time.sleep(1); continue
    print("Mode percakapan berkelanjutan berhenti.")

def apply_settings(selected_voice_id_to_set, selected_mic_str_from_gui, window_ref):
    global TTS_ENGINE, MIC_INDEX, tts_lock, is_assistant_speaking, pygame
    print(f"Terapkan: Suara ID = {selected_voice_id_to_set}, Mic Str = {selected_mic_str_from_gui}")
    applied_settings_feedback = []

    if TTS_ENGINE and selected_voice_id_to_set:
        current_tts_voice = TTS_ENGINE.getProperty('voice')
        if current_tts_voice != selected_voice_id_to_set:
            with tts_lock: 
                if is_assistant_speaking and pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                is_assistant_speaking = False 
            try:
                TTS_ENGINE.setProperty('voice', selected_voice_id_to_set)
                save_configuration(selected_voice_id_to_set, MIC_INDEX) 
                applied_settings_feedback.append("Suara berhasil diubah.")
            except Exception as e: print(f"Gagal ubah suara TTS: {e}"); messagebox.showerror("Error Suara", f"Gagal ubah suara: {e}", parent=window_ref)
        else: print("Suara TTS tidak berubah.")
    
    new_mic_idx_val = None
    if selected_mic_str_from_gui == "Default Sistem": new_mic_idx_val = None
    elif selected_mic_str_from_gui and ":" in selected_mic_str_from_gui:
        try: new_mic_idx_val = int(selected_mic_str_from_gui.split(":")[0].strip())
        except ValueError: print(f"Indeks mic tidak valid: {selected_mic_str_from_gui}"); messagebox.showerror("Error Mikrofon", "Indeks mic tidak valid.", parent=window_ref); new_mic_idx_val = MIC_INDEX
    
    if MIC_INDEX != new_mic_idx_val:
        MIC_INDEX = new_mic_idx_val
        print(f"Mikrofon diubah ke: {MIC_INDEX if MIC_INDEX is not None else 'Default'}")
        save_configuration(TTS_ENGINE.getProperty('voice') if TTS_ENGINE else None, MIC_INDEX)
        applied_settings_feedback.append("Mikrofon berhasil diubah.")
        initial_ambient_noise_adjustment() 
    else: print("Mikrofon tidak berubah.")
    
    if applied_settings_feedback:
        speak_with_pygame("Pengaturan telah diterapkan: " + ", ".join(applied_settings_feedback))
    else:
        pass

    if window_ref and window_ref.winfo_exists(): settings_window_close_event.set()

def open_settings_window(icon, item):
    global settings_window, TTS_ENGINE, MIC_INDEX, settings_window_close_event
    if settings_window is not None and settings_window.winfo_exists():
        settings_window.lift(); settings_window.focus_force(); return
    settings_window_close_event.clear()
    def create_gui_in_thread():
        global settings_window, TTS_ENGINE, MIC_INDEX, settings_window_close_event 

        if not TTS_ENGINE: 
            print("TTS Engine N/A, batal buka pengaturan.")
            return
        
        root = tk.Tk()
        settings_window = root 
        root.title("Pengaturan Suara")
        root.geometry("600x350") 
        
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)
        

        tts_frame = ttk.LabelFrame(main_frame, text="Output Suara (TTS)", padding="10"); tts_frame.pack(pady=5, fill=tk.X)
        ttk.Label(tts_frame, text="Pilih Suara:").pack(side=tk.LEFT, padx=5, pady=5)
        available_voices_display = []; available_voice_ids = []
        if TTS_ENGINE:
            voices_props = TTS_ENGINE.getProperty('voices')
            for voice in voices_props:
                lang_str = ", ".join([lang.decode('utf-8', 'ignore') for lang in voice.languages]) if voice.languages else "N/A"
                available_voices_display.append(f"{voice.name} (Lang: {lang_str}, Gender: {voice.gender})")
                available_voice_ids.append(voice.id)
        selected_voice_display_str = tk.StringVar()
        voice_dropdown = ttk.Combobox(tts_frame, textvariable=selected_voice_display_str, values=available_voices_display, state="readonly", width=70)
        current_voice_id_tts = TTS_ENGINE.getProperty('voice')
        try: 
            current_voice_idx_in_list = available_voice_ids.index(current_voice_id_tts)
            selected_voice_display_str.set(available_voices_display[current_voice_idx_in_list])
        except (ValueError, IndexError): 
            if available_voices_display: selected_voice_display_str.set(available_voices_display[0])
        voice_dropdown.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

        mic_frame = ttk.LabelFrame(main_frame, text="Input Audio (Mikrofon)", padding="10"); mic_frame.pack(pady=5, fill=tk.X)
        ttk.Label(mic_frame, text="Pilih Mikrofon:").pack(side=tk.LEFT, padx=5, pady=5)
        mic_display_list = ["Default Sistem"]; mic_map_display_to_index = {"Default Sistem": None}
        try:
            mic_list_from_sr = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(mic_list_from_sr):
                display_name = f"{idx}: {name[:60]}"
                mic_display_list.append(display_name); mic_map_display_to_index[display_name] = idx
        except Exception as e: print(f"Gagal dapat daftar mic: {e}")
        selected_mic_display_str = tk.StringVar()
        mic_dropdown = ttk.Combobox(mic_frame, textvariable=selected_mic_display_str, values=mic_display_list, state="readonly", width=70)
        current_mic_set_display = "Default Sistem"
        if MIC_INDEX is not None:
            for display_name, idx_val in mic_map_display_to_index.items():
                if idx_val == MIC_INDEX: current_mic_set_display = display_name; break
        selected_mic_display_str.set(current_mic_set_display)
        mic_dropdown.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)
        
        button_frame = ttk.Frame(main_frame); button_frame.pack(pady=15, side=tk.BOTTOM, fill=tk.X, anchor='e')
        apply_btn = ttk.Button(button_frame, text="Terapkan & Tutup", 
            command=lambda: apply_settings(
                available_voice_ids[available_voices_display.index(selected_voice_display_str.get())] 
                    if selected_voice_display_str.get() and selected_voice_display_str.get() in available_voices_display and available_voice_ids 
                    else (TTS_ENGINE.getProperty('voice') if TTS_ENGINE else None),
                selected_mic_display_str.get(), 
                root 
            ))
        apply_btn.pack(side=tk.RIGHT, padx=5)
        cancel_btn = ttk.Button(button_frame, text="Batal", command=lambda: settings_window_close_event.set())
        cancel_btn.pack(side=tk.RIGHT)
        
        def on_closing_settings_window(): 
            global settings_window_close_event 
            print("Tombol X jendela pengaturan ditekan.")
            settings_window_close_event.set() 
        root.protocol("WM_DELETE_WINDOW", on_closing_settings_window)
        
        while not settings_window_close_event.is_set():
            try:
                if root.winfo_exists(): 
                    root.update(); root.update_idletasks()
                else: break
            except tk.TclError as e: print(f"TclError update Tkinter: {e}"); break 
            except Exception as e_update: print(f"Error update loop Tkinter: {e_update}"); break
            time.sleep(0.05) 

        print("Loop Tkinter untuk jendela pengaturan selesai.")
        if root.winfo_exists(): 
            root.destroy()
        
        settings_window = None 

    gui_settings_thread = threading.Thread(target=create_gui_in_thread, daemon=True, name="SettingsGUIThread")
    gui_settings_thread.start()

def toggle_continuous_listening(icon, item):
    global is_continuous_mode_active, continuous_listen_thread, TRAY_ICON
    is_continuous_mode_active = not is_continuous_mode_active
    if is_continuous_mode_active:
        if not TTS_ENGINE or not RECOGNIZER or not pygame.mixer.get_init():
            speak_with_pygame("Engine suara atau pygame belum siap.")
            is_continuous_mode_active = False 
            return
        speak_with_pygame("Mode percakapan berkelanjutan diaktifkan.")
        show_desktop_icon() 
        if not (continuous_listen_thread and continuous_listen_thread.is_alive()):
            print("Memulai thread percakapan...")
            continuous_listen_thread = threading.Thread(target=continuous_conversation_loop, daemon=True, name="ContinuousListenThread")
            continuous_listen_thread.start()
        else:
            print("Thread percakapan sudah berjalan.")
    else:
        print("Sinyal menghentikan percakapan dikirim.")
        speak_with_pygame("Mode percakapan berkelanjutan akan dihentikan.")
        hide_desktop_icon() 
    if TRAY_ICON:
        try:
            TRAY_ICON.update_menu()
        except Exception as e_update_menu:
            print(f"Tidak bisa update menu tray: {e_update_menu}") 

def get_listening_status_text(item): 
    return "Hentikan Percakapan" if is_continuous_mode_active else "Mulai Percakapan"

def quit_action(icon, item):
    global TRAY_ICON, is_continuous_mode_active, tts_thread, tts_lock, pygame, settings_window, settings_window_close_event
    global desktop_icon_shutdown_event, desktop_icon_thread 

    print("Menerima perintah keluar...")
    is_continuous_mode_active = False
    hide_desktop_icon()

    if desktop_icon_thread and desktop_icon_thread.is_alive():
        print("Menghentikan thread ikon desktop...")
        desktop_icon_shutdown_event.set()

    if settings_window and settings_window.winfo_exists():
        print("Menutup jendela pengaturan...")
        settings_window_close_event.set()
        time.sleep(0.5) 

    with tts_lock:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        is_assistant_speaking = False
        if tts_thread and tts_thread.is_alive():
            tts_thread.join(timeout=0.5)
    
    speak_with_pygame("Menutup asisten. Sampai jumpa!")
    final_tts_thread_ref = None
    with tts_lock:
        final_tts_thread_ref = tts_thread
    
    if final_tts_thread_ref and final_tts_thread_ref.is_alive():
        print("Menunggu pesan keluar terakhir...")
        final_tts_thread_ref.join(timeout=3.0)
    
    if continuous_listen_thread and continuous_listen_thread.is_alive():
        print("Menunggu thread percakapan...")
        continuous_listen_thread.join(timeout=1.0)

    if desktop_icon_thread and desktop_icon_thread.is_alive():
        print("Menunggu thread ikon desktop selesai...")
        desktop_icon_thread.join(timeout=2.0) 
        if desktop_icon_thread.is_alive():
            print("Peringatan: Thread ikon desktop tidak berhenti tepat waktu.")

    if TRAY_ICON:
        print("Menghentikan ikon tray...")
        TRAY_ICON.stop()
    
    if pygame.mixer.get_init():
        pygame.mixer.quit()
    if pygame.get_init():
        pygame.quit()
    
    print("Aplikasi ditutup.")
    os._exit(0) 

def open_settings_window_tk(icon=None, item=None): 
    global main_tk_root
    if main_tk_root:
        main_tk_root.after(0, _create_actual_settings_gui)
    else:
        print("Error: main_tk_root belum siap saat mencoba membuka pengaturan.")

def apply_settings_tk(selected_voice_display_from_gui, selected_mic_display_from_gui, window_ref):
    global TTS_ENGINE, MIC_INDEX, tts_lock, is_assistant_speaking, pygame, available_voice_ids_settings_cache, mic_map_display_to_index

    print(f"Terapkan (TK): Suara Display = {selected_voice_display_from_gui}, Mic Display = {selected_mic_display_from_gui}")
    applied_settings_feedback = []
    
    selected_voice_id_to_set = None
    if TTS_ENGINE and selected_voice_display_from_gui and available_voice_ids_settings_cache:
        try:
            idx_voice = available_voices_display.index(selected_voice_display_from_gui) 
            selected_voice_id_to_set = available_voice_ids_settings_cache[idx_voice]
        except (ValueError, IndexError):
            print(f"Error: Display suara '{selected_voice_display_from_gui}' tidak ditemukan di cache.")
            selected_voice_id_to_set = TTS_ENGINE.getProperty('voice') 

    if TTS_ENGINE and selected_voice_id_to_set:
        current_tts_voice_id = TTS_ENGINE.getProperty('voice')
        if current_tts_voice_id != selected_voice_id_to_set:
            with tts_lock:
                if is_assistant_speaking and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                is_assistant_speaking = False 
            
            try:
                TTS_ENGINE.setProperty('voice', selected_voice_id_to_set)
                save_configuration(selected_voice_id_to_set, MIC_INDEX)
                applied_settings_feedback.append("Suara berhasil diubah.")
                print(f"Suara TTS diubah ke ID: {selected_voice_id_to_set}")
            except Exception as e:
                print(f"Gagal mengubah suara TTS: {e}")
                messagebox.showerror("Error Suara", f"Gagal mengubah suara: {e}", parent=window_ref)
        else:
            print("Suara TTS tidak berubah (sudah sama).")

    new_mic_idx_val = MIC_INDEX 
    if selected_mic_display_from_gui in mic_map_display_to_index: 
        new_mic_idx_val = mic_map_display_to_index[selected_mic_display_from_gui]
    else:
        print(f"Error: Display mic '{selected_mic_display_from_gui}' tidak ditemukan di map.")


    if MIC_INDEX != new_mic_idx_val:
        MIC_INDEX = new_mic_idx_val
        print(f"Mikrofon diubah ke: Indeks {MIC_INDEX if MIC_INDEX is not None else 'Default Sistem'}")
        current_voice_id_for_save = TTS_ENGINE.getProperty('voice') if TTS_ENGINE else None
        save_configuration(current_voice_id_for_save, MIC_INDEX)
        applied_settings_feedback.append("Mikrofon berhasil diubah.")
        if is_continuous_mode_active or True: 
            initial_ambient_noise_adjustment()
    else:
        print("Mikrofon tidak berubah (sudah sama).")

    if applied_settings_feedback:
        speak_with_pygame("Pengaturan telah diterapkan: " + ", dan ".join(applied_settings_feedback))
        messagebox.showinfo("Pengaturan Diterapkan", "Pengaturan telah diterapkan.", parent=window_ref)
    else:
        messagebox.showinfo("Pengaturan", "Tidak ada perubahan pada pengaturan.", parent=window_ref)

    _destroy_settings_window()

def create_tray_icon_image():
    width = 64; height = 64; image = Image.new('RGBA', (width, height), (0,0,0,0))
    draw = ImageDraw.Draw(image); draw.ellipse((4, 4, width - 4, height - 4), fill='skyblue', outline='darkblue', width=2)
    try: font = ImageFont.truetype("arial.ttf", size=38)
    except IOError: font = ImageFont.load_default()
    text = "AI"
    try: 
        bbox = draw.textbbox((0,0), text, font=font); text_width = bbox[2] - bbox[0]; text_height = bbox[3] - bbox[1]
        position = ((width - text_width) / 2, (height - text_height) / 2 - (height*0.08)) 
        draw.text(position, text, font=font, fill="white")
    except AttributeError: draw.text((width/3.5, height/4.5), text, font=font, fill="white")
    return image

def setup_tray_icon(): 
    global TRAY_ICON
    try: icon_image = create_tray_icon_image()
    except Exception as e: print(f"Gagal buat ikon: {e}"); icon_image = None
    
    TRAY_ICON = pystray.Icon(
        "windows_assistant", 
        icon_image, 
        "Assistant Kanee", 
        menu=pystray.Menu(
            pystray.MenuItem(get_listening_status_text, toggle_continuous_listening, default=True,
                             checked=lambda item: is_continuous_mode_active),
            pystray.MenuItem("Pengaturan Suara", open_settings_window), 
            pystray.MenuItem("Keluar", quit_action)
        )
    )
    print("Asisten Windows di System Tray. Klik ikon untuk opsi."); TRAY_ICON.run()

def new_quit_action(): 
    global main_tk_root, tray_icon_object, tray_icon_thread
    global is_continuous_mode_active, continuous_listen_thread, tts_thread, tts_lock, pygame
    global desktop_icon_window, settings_window
    global desktop_icon_shutdown_event, settings_window_close_event

    print("Perintah keluar diterima...")
    is_continuous_mode_active = False 

    if desktop_icon_window and desktop_icon_window.winfo_exists():
        print("Menutup jendela ikon desktop...")
        if desktop_icon_shutdown_event: desktop_icon_shutdown_event.set()

    if settings_window and settings_window.winfo_exists():
        print("Menutup jendela pengaturan...")
        if settings_window_close_event: settings_window_close_event.set()

    print("Menghentikan thread TTS...")
    with tts_lock:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        is_assistant_speaking = False 
        if tts_thread and tts_thread.is_alive():
            tts_thread.join(timeout=0.5) 

    print("Menghentikan thread percakapan berkelanjutan...")
    if continuous_listen_thread and continuous_listen_thread.is_alive():
        continuous_listen_thread.join(timeout=1.0)

    if tray_icon_object:
        print("Menghentikan ikon tray...")
        tray_icon_object.stop()
    if tray_icon_thread and tray_icon_thread.is_alive():
        print("Menunggu thread pystray selesai...")
        tray_icon_thread.join(timeout=1.0)

    if pygame.mixer.get_init():
        pygame.mixer.quit()
    if pygame.get_init():
        pygame.quit()
    print("Pygame dihentikan.")

    if main_tk_root:
        print("Menjadwalkan penutupan aplikasi Tkinter utama...")
        main_tk_root.destroy() 
    
    print("Proses keluar hampir selesai.")

def setup_pystray_icon_thread(app_root):
    global tray_icon_object, tray_icon_thread

    try:
        icon_image = create_tray_icon_image()
    except Exception as e:
        print(f"Gagal membuat gambar ikon tray: {e}")
        icon_image = None

    menu = pystray.Menu(
        pystray.MenuItem(get_listening_status_text, toggle_continuous_listening, default=True,
                         checked=lambda item: is_continuous_mode_active),
        pystray.MenuItem("Pengaturan Suara", open_settings_window_tk), 
        pystray.MenuItem("Keluar", new_quit_action) 
    )

    tray_icon_object = pystray.Icon(
        "windows_assistant",
        icon_image,
        "Asisten Kanee",
        menu
    )

    print("Menjalankan ikon tray di thread terpisah...")
    
    def run_icon_detached():
        tray_icon_object.run()
        print("Thread pystray.Icon.run() telah berhenti.")
        if main_tk_root and main_tk_root.winfo_exists():
             print("Pystray berhenti, memberi tahu main_tk_root untuk keluar jika masih ada.")
             if not main_tk_root.quit_called: 
                 main_tk_root.after(100, main_tk_root.destroy)

    tray_icon_thread = threading.Thread(target=run_icon_detached, daemon=True, name="PystrayThread")
    tray_icon_thread.start()

if __name__ == "__main__":
    main_tk_root = tk.Tk()
    main_tk_root.withdraw() 
    main_tk_root.title("Windows Assistant Root") 
    main_tk_root.quit_called = False

    loaded_voice_id = load_configuration()
    initialize_engines(preferred_voice_id=loaded_voice_id) 

    print("INFO (__main__): Memanggil create_desktop_icon_tk...")
    create_desktop_icon_tk(main_tk_root) 

    if not TTS_ENGINE: print("PERINGATAN: Mesin TTS tidak aktif!") 
    if not pygame.mixer.get_init(): print("PERINGATAN: Pygame Mixer tidak aktif!") 
    if not GEMINI_MODEL_INITIALIZED: print("PERINGATAN: Model Gemini tidak aktif!") 

    print("INFO (__main__): Memanggil setup_pystray_icon_thread...")
    setup_pystray_icon_thread(main_tk_root) 

    print("Asisten Windows di System Tray. Klik ikon untuk opsi.") 
    print("Menjalankan loop utama Tkinter (main_tk_root.mainloop())...")
    
    try:
        main_tk_root.mainloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt diterima. Memulai proses keluar...")
        new_quit_action() 
    finally:
        print("Loop utama Tkinter (main_tk_root.mainloop()) telah berhenti.")
        if tray_icon_object and tray_icon_object.visible:
            print("Memastikan pystray berhenti...")
            tray_icon_object.stop()
        if tray_icon_thread and tray_icon_thread.is_alive():
            tray_icon_thread.join(timeout=1.0)
        print("Aplikasi ditutup sepenuhnya.")