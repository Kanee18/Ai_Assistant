import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox

import cv2
import pygetwindow as gw
import pyautogui
import pystray
import pyttsx3
import pygame
import speech_recognition as sr

import api
import config
import gui
import utils

def set_default_indonesian_voice():
    if not config.TTS_ENGINE: return
    voices = config.TTS_ENGINE.getProperty('voices'); found_indonesian_voice = False
    for voice in voices:
        if "indonesian" in voice.name.lower() or any(lang in voice.languages for lang in [[b'id'], [b'id_ID']]):
            try: config.TTS_ENGINE.setProperty('voice', voice.id); print(f"Menggunakan suara TTS: {voice.name}"); found_indonesian_voice = True; break
            except Exception: pass 
    if not found_indonesian_voice: print("Tidak ditemukan suara TTS Indo, pakai default sistem.")

def initialize_engines(preferred_voice_id=None):
    print("Menginisialisasi Pygame dan Pygame Mixer...")
    try:
        pygame.init(); pygame.mixer.init(); print("Pygame dan Pygame Mixer berhasil diinisialisasi.")
    except Exception as e: print(f"KRITIS: Gagal inisialisasi Pygame: {e}")

    print("Menginisialisasi mesin Text-to-Speech (TTS)...")
    try:
        config.TTS_ENGINE = pyttsx3.init(); config.TTS_ENGINE.setProperty('rate', 165) 
        if preferred_voice_id:
            try: config.TTS_ENGINE.setProperty('voice', preferred_voice_id); print(f"Suara dari konfigurasi diterapkan: {preferred_voice_id}")
            except Exception as e: print(f"Gagal menerapkan suara dari konfigurasi ({preferred_voice_id}): {e}. Mencari default Indo."); set_default_indonesian_voice()
        else: set_default_indonesian_voice()
        print("Mesin TTS berhasil diinisialisasi.")
    except Exception as e: print(f"KRITIS: Gagal inisialisasi TTS: {e}"); config.TTS_ENGINE = None

    if not config.SPACY_MODEL_INITIALIZED:
        utils.initialize_spacy_model()

    print("Menginisialisasi Speech Recognizer..."); config.RECOGNIZER = sr.Recognizer(); print("Speech Recognizer berhasil diinisialisasi.")

    print("INFO (windows_assistant.py): Memanggil inisialisasi Gemini dari api.py...")
    api.initialize_gemini()

    if not api.GEMINI_MODEL_INITIALIZED:
        print("PERINGATAN (windows_assistant.py): Model Gemini GAGAL diinisialisasi melalui api.py.")
    else:
        print("INFO (windows_assistant.py): Model Gemini BERHASIL diinisialisasi melalui api.py.")

def speak_with_pygame(text_to_speak):
    if not config.TTS_ENGINE: print(f"Asisten (TTS engine N/A): {text_to_speak}"); return
    if not pygame.mixer.get_init(): print(f"Asisten (Pygame mixer N/A): {text_to_speak}"); return
    
    def _save_and_play_in_thread(current_text):
        thread_name = threading.current_thread().name; acquired_lock_for_flag_init = False; sound_played_successfully = False
        try:
            if not config.tts_lock.acquire(timeout=1.0): print(f"TTS Thread {thread_name}: Gagal lock awal, batal."); return 
            acquired_lock_for_flag_init = True; config.is_assistant_speaking = True; config.tts_lock.release(); acquired_lock_for_flag_init = False 
            
            print(f"Asisten (simpan file - thread {thread_name}): {current_text}")
            config.TTS_ENGINE.save_to_file(current_text, config.AUDIO_FILENAME); config.TTS_ENGINE.runAndWait(); print(f"Audio disimpan: {config.AUDIO_FILENAME}")
            
            with config.tts_lock: 
                if not config.is_assistant_speaking: print(f"TTS Thread {thread_name}: Interupsi saat simpan."); return 
            
            if not pygame.mixer.get_init(): print(f"TTS Thread {thread_name}: Pygame mixer mati saat akan putar."); return

            pygame.mixer.music.load(config.AUDIO_FILENAME); pygame.mixer.music.play(); sound_played_successfully = True
            
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
                with config.tts_lock: 
                    if not config.is_assistant_speaking: 
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
            
            if sound_played_successfully and not pygame.mixer.music.get_busy() and config.is_assistant_speaking: print(f"TTS Thread {thread_name}: Audio selesai normal.")
            elif pygame.mixer.music.get_busy(): pygame.mixer.music.stop(); print(f"TTS Thread {thread_name}: Musik stop paksa di akhir.")
            
            if sound_played_successfully and hasattr(pygame.mixer.music, 'unload'):
                try: time.sleep(0.05); pygame.mixer.music.unload(); print(f"Thread TTS {thread_name}: File {config.AUDIO_FILENAME} di-unload.")
                except pygame.error as e: print(f"TTS Thread {thread_name}: Pygame error unload '{config.AUDIO_FILENAME}': {e}")
        except Exception as e: print(f"Error simpan/putar (thread {thread_name}): {e}")
        finally:
            if os.path.exists(config.AUDIO_FILENAME):
                print(f"Hapus file: {config.AUDIO_FILENAME}"); time.sleep(0.2) 
                for i in range(5): 
                    try: os.remove(config.AUDIO_FILENAME); print(f"File {config.AUDIO_FILENAME} hapus percobaan {i+1} sukses."); break 
                    except PermissionError as e_perm:
                        if i == 4: print(f"Gagal total hapus {config.AUDIO_FILENAME} (PermissionError): {e_perm}")
                        else: print(f"Gagal hapus percobaan ke-{i+1} (PermissionError), coba lagi..."); time.sleep(0.3 + (i*0.1)) 
                    except Exception as e_del: print(f"Gagal hapus percobaan ke-{i+1} (Error Lain): {e_del}"); break 
            
            if acquired_lock_for_flag_init and config.tts_lock.locked(): 
                 config.tts_lock.release() 
            
            with config.tts_lock: 
                if threading.current_thread() is config.tts_thread: 
                    config.is_assistant_speaking = False
            print(f"Asisten (selesai proses audio - thread {thread_name}): {current_text}")

    if not config.tts_lock.acquire(timeout=0.5): print("Speak_pygame: Gagal lock utama, speak batal."); 
    try:
        if config.tts_thread and config.tts_thread.is_alive():
            print("Speak_pygame: Thread TTS lama aktif, stop musiknya...");
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
            config.is_assistant_speaking = False; config.tts_thread.join(timeout=0.3) 
            if config.tts_thread.is_alive(): print("Speak_pygame: Peringatan, thread TTS lama masih hidup.")
        
        config.tts_thread = threading.Thread(target=_save_and_play_in_thread, args=(text_to_speak,), name=f"PygameTTS-{int(time.time())}")
        config.tts_thread.daemon = True; config.tts_thread.start()
    finally:
        config.tts_lock.release()

def process_nlu(text):
    if not text: return {"intent": "NO_INPUT", "entities": {}}
    text_lower = text.lower()
    print(f"DEBUG (process_nlu): Menerima teks input: '{text_lower}'") 
    print(f"DEBUG (process_nlu): Status Awal: SPACY_MODEL_INITIALIZED={config.SPACY_MODEL_INITIALIZED}, NLP is None={config.NLP is None}, MATCHER is None={config.MATCHER is None}")

    if config.SPACY_MODEL_INITIALIZED and config.NLP and config.MATCHER:
        doc = config.NLP(text_lower)
        matches = config.MATCHER(doc)
        matches_sorted = sorted(matches, key=lambda m: m[2] - m[1], reverse=True)
        print(f"DEBUG (process_nlu): spaCy matches (sorted by length) = {[(config.NLP.vocab.strings[match_id], doc[start:end].text) for match_id, start, end in matches_sorted]}")

        for match_id, start, end in matches_sorted: 
            span = doc[start:end]  
            intent_name_spacy = config.NLP.vocab.strings[match_id]  

            if intent_name_spacy == "OPEN_APPLICATION_SPACY":
                print("DEBUG (process_nlu): spaCy cocok dengan OPEN_APPLICATION_SPACY") 
                app_name_tokens = []
                if len(span) > 1 and span[1].lower_ == "aplikasi": 
                    app_name_tokens = span[2:] 
                elif len(span) > 0: 
                    app_name_tokens = span[1:]
                app_name_parts = [token.text for token in app_name_tokens if token.is_alpha or token.is_digit]
                app_name = " ".join(app_name_parts).strip()
                if app_name: 
                    print(f"DEBUG (process_nlu): spaCy menemukan app_name: '{app_name}'") 
                    return {"intent": "OPEN_APPLICATION", "entities": {"app_name": app_name}}
                else: 
                    print("DEBUG (process_nlu): spaCy OPEN_APPLICATION_SPACY tapi tidak ada app_name.") 
                    return {"intent": "OPEN_APPLICATION_PROMPT", "entities": {}}

            elif intent_name_spacy == "CLOSE_APPLICATION_SPACY":
                print("DEBUG (process_nlu): spaCy cocok dengan CLOSE_APPLICATION_SPACY")
                app_name_tokens = []
                if len(span) > 1 and span[1].lower_ == "aplikasi": 
                    app_name_tokens = span[2:] 
                elif len(span) > 0: 
                    app_name_tokens = span[1:]
                app_name = " ".join([token.text for token in app_name_tokens if token.is_alpha or token.is_digit]).strip()
                if app_name:
                    print(f"DEBUG (process_nlu): spaCy menemukan app_name untuk ditutup: '{app_name}'")
                    return {"intent": "CLOSE_APPLICATION", "entities": {"app_name": app_name}}
                else:
                    print("DEBUG (process_nlu): spaCy CLOSE_APPLICATION_SPACY tapi tidak ada app_name.")
                    return {"intent": "ASK_AI", "entities": {"prompt": text}} 

            elif intent_name_spacy == "SEARCH_INFO_SPACY":
                print("DEBUG (process_nlu): spaCy cocok dengan SEARCH_INFO_SPACY") 
                topic_tokens = []
                if span[0].lower_ in ["cari", "carikan", "jelaskan", "terangkan", "apa"]:
                    start_index_for_topic = 1 
                    for i, token in enumerate(span):
                        if token.lower_ in ["tentang", "mengenai", "itu"]:
                            start_index_for_topic = i + 1
                            break 
                    if start_index_for_topic < len(span):
                        topic_tokens = span[start_index_for_topic:]
                
                topic = " ".join([token.text for token in topic_tokens]).strip()
                if topic: 
                    print(f"DEBUG (process_nlu): spaCy menemukan topic: '{topic}'") 
                    return {"intent": "SEARCH_INFO", "entities": {"topic": topic}}
                else:
                    print(f"DEBUG (process_nlu): spaCy SEARCH_INFO_SPACY tapi tidak ada topic.")
        
        print(f"DEBUG (process_nlu): Tidak ada pola spaCy Matcher yang dikenal yang menghasilkan return untuk: '{text_lower}'. Melanjutkan ke fallback regex/keyword.")
    else:
        print(f"DEBUG (process_nlu): spaCy tidak diinisialisasi atau tidak aktif. Menggunakan fallback regex/keyword.")

    print(f"DEBUG (process_nlu): Mencoba regex CHAINED_OPEN_TYPE_NAVIGATE untuk: '{text_lower}'")
    match_open_type_navigate = re.search(
        r"^(?:buka|jalankan|aktifkan)\s+(?:aplikasi\s+)?(.+?)\s+dan\s+(?:ketik|tuliskan|tulis)\s+(.+?)\s+dan\s+(?:buka|cari|tuju|pergi ke)\s+(.+?)(?:nya)?$", 
        text_lower
    )
    if match_open_type_navigate:
        app_name = match_open_type_navigate.group(1).strip()
        text_to_type = match_open_type_navigate.group(2).strip()
        target_action_or_site = match_open_type_navigate.group(3).strip()
        print(f"DEBUG (process_nlu): Regex CHAINED_OPEN_TYPE_NAVIGATE cocok. App: '{app_name}', Teks: '{text_to_type}', Target: '{target_action_or_site}'")
        if app_name and text_to_type and target_action_or_site:
            return {
                "intent": "CHAINED_OPEN_TYPE_NAVIGATE",
                "entities": {
                    "app_name": app_name,
                    "text_to_type": text_to_type,
                    "target_action_or_site": target_action_or_site
                }
            }
    else:
        print(f"DEBUG (process_nlu): Regex CHAINED_OPEN_TYPE_NAVIGATE TIDAK cocok.")

    print(f"DEBUG (process_nlu): Mencoba regex CHAINED_OPEN_TYPE untuk: '{text_lower}'")
    match_open_then_type = re.search(r"^(?:buka|jalankan|aktifkan)\s+(?:aplikasi\s+)?(.+?)\s+dan\s+(?:ketik|tuliskan|tulis)\s+(.+)", text_lower)
    if match_open_then_type:
        app_name = match_open_then_type.group(1).strip()
        text_to_type = match_open_then_type.group(2).strip()
        print(f"DEBUG (process_nlu): Regex CHAINED_OPEN_TYPE cocok. App: '{app_name}', Teks: '{text_to_type}'")
        if app_name and text_to_type:
            return {
                "intent": "CHAINED_OPEN_THEN_TYPE",
                "entities": {
                    "app_name": app_name,
                    "text_to_type": text_to_type
                }
            }
    else:
        print(f"DEBUG (process_nlu): Regex CHAINED_OPEN_TYPE TIDAK cocok.")
    print(f"DEBUG (process_nlu): Mencoba fallback regex OPEN_APPLICATION (umum) untuk: '{text_lower}'")
    match_open_app_fallback = re.search(r"^(?:buka|jalankan|aktifkan)\s+(?:aplikasi\s+)?([a-zA-Z0-9\s]+?)(?:\s+dan\s+.*)?$", text_lower)
    if match_open_app_fallback:
        app_name = match_open_app_fallback.group(1).strip()
        if app_name: 
            print(f"DEBUG (process_nlu): Fallback regex OPEN_APPLICATION (umum) cocok, app_name = '{app_name}'")
            return {"intent": "OPEN_APPLICATION", "entities": {"app_name": app_name}}
    else:
        print(f"DEBUG (process_nlu): Fallback regex OPEN_APPLICATION (umum) TIDAK cocok.")

    print(f"DEBUG (process_nlu): Mencoba fallback regex CLOSE_APPLICATION untuk: '{text_lower}'")
    match_close_app_fallback = re.search(r"^(?:tutup|close|hentikan)\s+(?:aplikasi\s+)?(.+)", text_lower) # Regex ini mungkin juga perlu disesuaikan agar tidak rakus
    if match_close_app_fallback:
        app_name = match_close_app_fallback.group(1).strip()
        if app_name: # Pastikan app_name tidak kosong
            print(f"DEBUG (process_nlu): Fallback regex CLOSE_APPLICATION cocok, app_name = '{app_name}'")
            return {"intent": "CLOSE_APPLICATION", "entities": {"app_name": app_name}}
    else:
        print(f"DEBUG (process_nlu): Fallback regex CLOSE_APPLICATION TIDAK cocok.") 

    # Keyword spotting
    if any(word in text_lower for word in ["selamat tinggal", "keluar program", "berhenti program"]):
        print("DEBUG (process_nlu): Keyword cocok dengan GOODBYE_APP") 
        return {"intent": "GOODBYE_APP", "entities": {}}
    if "siapa namamu" in text_lower: 
        print("DEBUG (process_nlu): Keyword cocok dengan GET_NAME") 
        return {"intent": "GET_NAME", "entities": {}}
    if any(word in text_lower for word in ["jam berapa", "pukul berapa"]):
        print("DEBUG (process_nlu): Keyword cocok dengan GET_TIME") 
        return {"intent": "GET_TIME", "entities": {}}
    if any(phrase in text_lower for phrase in ["apa judul jendela ini", "judul jendela aktif", "jendela apa yang aktif", "apa nama window ini", "sebutkan judul window"]):
        print("DEBUG (process_nlu): Keyword cocok dengan GET_ACTIVE_WINDOW_TITLE")  
        return {"intent": "GET_ACTIVE_WINDOW_TITLE", "entities": {}}
    
    print(f"DEBUG (process_nlu): Mencoba regex TYPE_IN_NEW_TAB_BROWSER untuk: '{text_lower}'")
    match_type_new_tab = re.search(
        r"^(?:ketik|tuliskan|tulis|carikan)\s+(.+?)\s+di\s+(?:tab\s+baru|new\s+tab)(?:\s+(?:di\s+)?(chrome|edge|firefox))?$",
        text_lower
    )
    if match_type_new_tab:
        text_to_type = match_type_new_tab.group(1).strip()
        browser_name_from_regex = match_type_new_tab.group(2) 
        
        
        entities_dict = {"text_to_type": text_to_type}
        if browser_name_from_regex:
            entities_dict["target_app"] = browser_name_from_regex.strip().lower()
        
        return {
            "intent": "TYPE_IN_NEW_TAB_BROWSER",
            "entities": entities_dict
        }
    else:
        print(f"DEBUG (process_nlu): Regex TYPE_IN_NEW_TAB_BROWSER TIDAK cocok.")

    print(f"DEBUG (process_nlu): Tidak ada intent spesifik yang cocok, jatuh ke ASK_AI untuk '{text_lower}'") 
    return {"intent": "ASK_AI", "entities": {"prompt": text}}

def handle_chained_open_then_type(entities):
    app_name = entities.get("app_name")
    text_to_type = entities.get("text_to_type")

    if not app_name or not text_to_type:
        return "Perintah tidak lengkap. Saya butuh nama aplikasi dan teks yang akan diketik."

    # Langkah 1: Buka Aplikasi
    response_open = handle_open_application({"app_name": app_name})
    speak_with_pygame(response_open) 

    if "gagal" in response_open.lower() or "tidak ditemukan" in response_open.lower() or "error" in response_open.lower():
        return f"Gagal membuka {app_name}, jadi saya tidak bisa mengetik."

    print(f"INFO (chained_open_then_type): Aplikasi '{app_name}' diasumsikan terbuka. Menunggu sebelum mengetik...")
    time.sleep(5) 

    try:
        target_window_title_keyword = app_name
        if app_name.lower() == "chrome": target_window_title_keyword = "chrome"
        
        print(f"INFO (chained_open_then_type): Mencoba mencari dan mengaktifkan jendela '{target_window_title_keyword}'...")
        windows = gw.getWindowsWithTitle(target_window_title_keyword)
        activated = False
        if windows:
            for win in sorted(windows, key=lambda w: w.title.lower().find(target_window_title_keyword.lower())):
                if not win.isMinimized:
                    try: 
                        win.activate()
                        print(f"  Jendela '{win.title}' diaktifkan.")
                        time.sleep(0.5) 
                        activated = True
                        break
                    except Exception as e_activate:
                        print(f"  Gagal mengaktifkan jendela '{win.title}': {e_activate}")
            if not activated and windows[0]: 
                 try: 
                    windows[0].activate()
                    print(f"  Jendela (fallback) '{windows[0].title}' diaktifkan.")
                    time.sleep(0.5)
                    activated = True
                 except Exception: pass 
        
        if not activated:
            print(f"PERINGATAN (chained_open_then_type): Tidak bisa otomatis mengaktifkan jendela '{app_name}'. Pastikan jendela sudah aktif manual.")

    except Exception as e_gw:
        print(f"ERROR (chained_open_then_type): Kesalahan saat pygetwindow: {e_gw}")

    response_type = handle_type_text({"text_to_type": text_to_type}) 

    try:
        print(f"INFO (chained_open_then_type): Menekan tombol 'enter' setelah mengetik '{text_to_type}'.")
        pyautogui.press('enter')
        return f"Selesai: {app_name} dibuka, '{text_to_type}' diketik, dan tombol enter ditekan."
    except Exception as e_pyautogui_enter:
        print(f"ERROR (chained_open_then_type): Gagal menekan tombol enter: {e_pyautogui_enter}")
        return f"Selesai mengetik '{text_to_type}', tetapi gagal menekan tombol enter."

def interpret_target_action(typed_text, target_action_or_site):
    typed_text_lower = typed_text.lower()
    target_lower = target_action_or_site.lower()

    if target_lower == "nya" or target_lower == typed_text_lower:
        if "." in typed_text_lower and (" " not in typed_text_lower or any(domain in typed_text_lower for domain in [".com", ".co.id", ".org", ".net"])):
            url_to_open = typed_text
            if not url_to_open.startswith("http://") and not url_to_open.startswith("https://"):
                url_to_open = "https://" + url_to_open
            return {"action": "open_url", "url": url_to_open}
        else:
            return {"action": "press_enter"}
    else:
        if "." in target_lower and (" " not in target_lower or any(domain in target_lower for domain in [".com", ".co.id", ".org", ".net"])):
            url_to_open = target_action_or_site
            if not url_to_open.startswith("http://") and not url_to_open.startswith("https://"):
                url_to_open = "https://" + url_to_open
            return {"action": "open_url", "url": url_to_open}
        else:
            print(f"  Interpretasi target: '{target_action_or_site}' setelah mengetik '{typed_text}'. Mengasumsikan 'press_enter' pada '{typed_text}'.")
            return {"action": "press_enter"}


def handle_chained_open_type_navigate(entities):
    app_name = entities.get("app_name")
    text_to_type = entities.get("text_to_type")
    target_action_or_site = entities.get("target_action_or_site")

    if not app_name or not text_to_type or not target_action_or_site:
        return "Perintah tidak lengkap. Saya butuh nama aplikasi, teks yang diketik, dan target aksi/situs."

    response_open = handle_open_application({"app_name": app_name})
    speak_with_pygame(response_open)

    if "gagal" in response_open.lower() or "tidak ditemukan" in response_open.lower() or "error" in response_open.lower():
        return f"Gagal membuka {app_name}, jadi saya tidak bisa melanjutkan."

    print(f"INFO (chained_navigate): Aplikasi '{app_name}' diasumsikan sedang terbuka. Menunggu sebelum mengetik...")
    time.sleep(5) 

    try:
        target_window_title_keyword = app_name
        if app_name.lower() == "chrome": target_window_title_keyword = "chrome"
        
        print(f"INFO (chained_navigate): Mencoba mencari dan mengaktifkan jendela yang mengandung '{target_window_title_keyword}'...")
        windows = gw.getWindowsWithTitle(target_window_title_keyword)
        activated = False
        if windows:
            for win in sorted(windows, key=lambda w: w.title.lower().find(target_window_title_keyword.lower())):
                if not win.isMinimized:
                    try: win.activate(); print(f"  Jendela '{win.title}' diaktifkan."); time.sleep(0.5); activated = True; break
                    except Exception as e_activate: print(f"  Gagal mengaktifkan jendela '{win.title}': {e_activate}")
            if not activated and windows[0]:
                 try: windows[0].activate(); print(f"  Jendela (fallback) '{windows[0].title}' diaktifkan."); time.sleep(0.5); activated = True
                 except Exception: pass
        if not activated:
            print(f"PERINGATAN (chained_navigate): Tidak bisa otomatis mengaktifkan jendela '{app_name}'.")
    except Exception as e_gw:
        print(f"ERROR (chained_navigate): Kesalahan saat pygetwindow: {e_gw}")

    response_type = handle_type_text({"text_to_type": text_to_type}) 

    time.sleep(1) 

    interpreted_action = interpret_target_action(text_to_type, target_action_or_site)
    action_taken_message = ""

    if interpreted_action["action"] == "press_enter":
        print(f"INFO (chained_navigate): Menekan tombol 'enter'...")
        pyautogui.press('enter')
        action_taken_message = f"Tombol enter ditekan setelah mengetik {text_to_type}."
    
    elif interpreted_action["action"] == "open_url":
        url = interpreted_action["url"]
        print(f"INFO (chained_navigate): Mencoba membuka URL: {url} di browser default...")
        try:
            webbrowser.open(url, new=2) 
            action_taken_message = f"Mencoba membuka {url}."
        except Exception as e_wb:
            print(f"ERROR (chained_navigate): Gagal membuka URL {url} dengan webbrowser: {e_wb}")
            action_taken_message = f"Gagal membuka {url}."
            if app_name.lower() in ["chrome", "edge", "firefox"]: 
                 print(f"  Fallback: Menekan enter setelah mengetik '{text_to_type}' di {app_name}")
                 pyautogui.press('enter')
                 action_taken_message += " Mencoba menekan enter di browser."

    return f"Selesai: Aplikasi {app_name} dibuka, '{text_to_type}' diketik, dan aksi '{interpreted_action['action']}' dilakukan. {action_taken_message}"

def get_currently_active_browser(supported_browsers):
    try:
        active_window = gw.getActiveWindow()
        if active_window and active_window.title:
            active_title_lower = active_window.title.lower()
            print(f"  DEBUG (get_active_browser): Judul jendela AKTIF: '{active_window.title}' (lower: '{active_title_lower}')")

            if ("microsoft edge" in active_title_lower or active_title_lower.endswith(" - microsoft edge")) and "edge" in supported_browsers:
                print(f"  INFO: Browser aktif terdeteksi (spesifik): 'edge' dari judul '{active_window.title}'")
                return "edge"
            if ("google chrome" in active_title_lower or active_title_lower.endswith(" - google chrome")) and "chrome" in supported_browsers:
                print(f"  INFO: Browser aktif terdeteksi (spesifik): 'chrome' dari judul '{active_window.title}'")
                return "chrome"
            if ("mozilla firefox" in active_title_lower or active_title_lower.endswith(" - mozilla firefox")) and "firefox" in supported_browsers:
                print(f"  INFO: Browser aktif terdeteksi (spesifik): 'firefox' dari judul '{active_window.title}'")
                return "firefox"

            for browser_name in supported_browsers:
                if browser_name in active_title_lower:
                    print(f"  INFO: Browser aktif terdeteksi (umum): '{browser_name}' dari judul '{active_window.title}'")
                    return browser_name
        else:
            print("  DEBUG (get_active_browser): Tidak ada jendela aktif atau tidak ada judul pada jendela aktif.")
    except Exception as e:
        print(f"  WARNING (get_active_browser): Tidak bisa mendapatkan jendela aktif atau judulnya: {e}")

    print("  DEBUG (get_active_browser): Jendela aktif tidak cocok/tidak ada. Mencari di semua jendela terbuka yang tidak terminimize...")
    all_windows = gw.getAllWindows()
    for win in all_windows:
        if win.title and not win.isMinimized: 
            win_title_lower = win.title.lower()
            print(f"    DEBUG (get_active_browser): Memeriksa jendela terbuka: '{win.title}' (lower: '{win_title_lower}')")

            if ("microsoft edge" in win_title_lower or win_title_lower.endswith(" - microsoft edge")) and "edge" in supported_browsers:
                print(f"  INFO: Browser terbuka ditemukan (spesifik): 'edge' dari judul '{win.title}'")
                return "edge" 
            if ("google chrome" in win_title_lower or win_title_lower.endswith(" - google chrome")) and "chrome" in supported_browsers:
                print(f"  INFO: Browser terbuka ditemukan (spesifik): 'chrome' dari judul '{win.title}'")
                return "chrome"
            if ("mozilla firefox" in win_title_lower or win_title_lower.endswith(" - mozilla firefox")) and "firefox" in supported_browsers:
                print(f"  INFO: Browser terbuka ditemukan (spesifik): 'firefox' dari judul '{win.title}'")
                return "firefox"
            
            for browser_name in supported_browsers:
                if browser_name in win_title_lower:
                    print(f"  INFO: Browser terbuka ditemukan (umum): '{browser_name}' dari judul '{win.title}'")
                    return browser_name 

    print("  DEBUG (get_active_browser): Tidak ada browser dari daftar yang didukung ditemukan aktif atau terbuka (tidak terminimize).")
    return None

def handle_type_in_new_tab(entities):
    text_to_type = entities.get("text_to_type")
    
    supported_browsers = ["chrome", "edge", "firefox"]
    app_from_nlu = entities.get("target_app") 
    
    target_app_name = None

    if app_from_nlu and app_from_nlu.lower() in supported_browsers:
        target_app_name = app_from_nlu.lower() # <-- Ini akan diisi dengan "edge"
        print(f"INFO (handle_type_in_new_tab): Target browser dari NLU: '{target_app_name}'")
    else:
        print(f"INFO (handle_type_in_new_tab): Browser tidak disebut NLU, mencoba deteksi otomatis...")
        detected_browser = get_currently_active_browser(supported_browsers)
        if detected_browser:
            target_app_name = detected_browser
            print(f"  INFO: Menggunakan browser terdeteksi: '{target_app_name}'")
        else:
            default_browser_if_none_detected = "chrome" 
            print(f"  INFO: Tidak ada browser aktif/terbuka yang terdeteksi dari daftar. Default ke '{default_browser_if_none_detected}'.")
            target_app_name = default_browser_if_none_detected

    if not text_to_type:
        return f"Apa yang ingin saya ketikkan di tab baru {target_app_name}?"

    print(f"INFO (handle_type_in_new_tab): Perintah diterima - Ketik '{text_to_type}' di tab baru {target_app_name}.")

    try:
        browser_windows = []
        all_window_titles = gw.getAllTitles() 
        for title in all_window_titles:
            if target_app_name.lower() in title.lower():
                wins = gw.getWindowsWithTitle(title) 
                if wins:
                    browser_windows.extend(wins) 

        active_browser_window = None
        if not browser_windows:
            print(f"  INFO: Tidak ditemukan jendela {target_app_name} yang terbuka. Mencoba membuka instance baru...")
            open_response = handle_open_application({"app_name": target_app_name})
            speak_with_pygame(open_response)
            time.sleep(5) 
            for title in gw.getAllTitles(): 
                 if target_app_name.lower() in title.lower():
                     wins = gw.getWindowsWithTitle(title)
                     if wins: browser_windows.extend(wins)
            if not browser_windows:
                 return f"Maaf, saya gagal membuka atau menemukan jendela {target_app_name}."

        current_active_win_obj = gw.getActiveWindow()
        if current_active_win_obj and target_app_name.lower() in current_active_win_obj.title.lower():
            active_browser_window = current_active_win_obj
            print(f"  INFO: Menggunakan jendela {target_app_name} yang sudah aktif: '{active_browser_window.title}'")
        else:
            for win in browser_windows:
                if not win.isMinimized: 
                    active_browser_window = win
                    break
            if not active_browser_window and browser_windows: 
                active_browser_window = browser_windows[0]

        if active_browser_window:
            print(f"  Mengaktifkan jendela: '{active_browser_window.title}'")
            if active_browser_window.isMinimized:
                active_browser_window.restore()
            active_browser_window.activate()
            time.sleep(0.7) 
        else:
            return f"Tidak dapat menemukan atau mengaktifkan jendela {target_app_name}."
        
        
        try:
            final_active_check = gw.getActiveWindow()
            if final_active_check:
                print(f"  DEBUG: Jendela aktif SEBELUM pyautogui: '{final_active_check.title}'")
            else:
                print("  DEBUG: Tidak ada jendela aktif terdeteksi SEBELUM pyautogui.")
        except Exception as e_dbg_active:
            print(f"  DEBUG: Error cek jendela aktif: {e_dbg_active}")

        print(f"  Membuka tab baru di {target_app_name} (Ctrl+T)...") 
        pyautogui.hotkey('ctrl', 't')
        time.sleep(1)

        # 3. Ketik Teks
        print(f"  Mengetik '{text_to_type}'...")
        pyautogui.write(text_to_type, interval=0.05)
        time.sleep(0.5)

        # 4. Tekan Enter
        print("  Menekan tombol 'Enter'...")
        pyautogui.press('enter')

        return f"Selesai: '{text_to_type}' diketik di tab baru {target_app_name} dan tombol enter ditekan."

    except Exception as e:
        print(f"ERROR (handle_type_in_new_tab): Terjadi kesalahan - {str(e)}")
        return f"Maaf, terjadi kesalahan saat mencoba mengetik di tab baru: {str(e)}"

def handle_type_text(entities):
    text_to_type = entities.get("text_to_type")
    if not text_to_type:
        return "Apa yang ingin saya ketikkan?"

    try:
        print(f"INFO (handle_type_text): Akan mengetik: '{text_to_type}'")
        time.sleep(1) 
        pyautogui.write(text_to_type, interval=0.05) 
        return f"Selesai mengetik: {text_to_type}"
    except Exception as e:
        print(f"ERROR (handle_type_text): Terjadi kesalahan - {e}")
        if isinstance(e, pyautogui.PyAutoGUIException) or "pyautogui" in str(e).lower():
             return "Maaf, saya mengalami masalah dengan fitur mengetik. Pastikan library yang dibutuhkan sudah terinstal."
        return "Maaf, terjadi kesalahan saat mencoba mengetik."

def handle_open_application(entities):
    app_name_from_nlu = entities.get("app_name")
    if not app_name_from_nlu:
        return "Aplikasi apa yang ingin Anda buka?"

    print(f"INFO (handle_open_application): Menerima permintaan untuk membuka: '{app_name_from_nlu}'")

    app_alias_map = {
        "notepad": "notepad.exe",
        "kalkulator": "start calc", 
        "paint": "mspaint.exe",
        "google chrome": "chrome.exe",
        "chrome": "chrome.exe",
        "microsoft edge": "start msedge", 
        "edge": "start msedge",
        "word": "start winword", 
        "excel": "start excel",  
        "powerpoint": "start powerpnt", 
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "file explorer": "explorer.exe",
        "explorer": "explorer.exe",
        "spotify": "spotify.exe" 
    }
    
    name_to_process = app_name_from_nlu.lower()
    command_to_run_or_find = app_alias_map.get(name_to_process, name_to_process) 

    print(f"INFO (handle_open_application): Perintah/nama awal yang akan diproses: '{command_to_run_or_find}'")

    command_path = None
    is_start_command = False

    if command_to_run_or_find.lower().startswith("start "):
        command_path = command_to_run_or_find 
        is_start_command = True
        print(f"  Ini adalah perintah 'start': {command_path}")
    else:
        print(f"  Mencari path untuk executable: '{command_to_run_or_find}'")
        command_path = utils.find_executable_path(command_to_run_or_find)
        
        if not command_path and name_to_process != command_to_run_or_find:
            print(f"  Pencarian awal gagal, mencoba dengan nama NLU asli: '{name_to_process}'")
            command_path = utils.find_executable_path(name_to_process)

    if command_path:
        try:
            if is_start_command:
                print(f"INFO (handle_open_application): Menjalankan perintah start: {command_path}")
                subprocess.Popen(command_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                print(f"INFO (handle_open_application): Menjalankan aplikasi dari path: {command_path}")
                subprocess.Popen(command_path) 
            
            return f"Aplikasi {app_name_from_nlu} seharusnya sedang dibuka."

        except Exception as e:
            print(f"ERROR (handle_open_application): Gagal menjalankan Popen untuk '{command_path}': {e}")
            if not is_start_command:
                base_exe_name_fallback = command_to_run_or_find 
                if not base_exe_name_fallback.lower().endswith(".exe"):
                    base_exe_name_fallback += ".exe"
                try:
                    print(f"  Popen dengan path gagal, mencoba '{base_exe_name_fallback}' via shell (mengandalkan PATH)...")
                    subprocess.Popen(base_exe_name_fallback, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    return f"Mencoba membuka {app_name_from_nlu} (mengandalkan PATH sistem)."
                except Exception as e_shell:
                    print(f"  ERROR: Gagal fallback Popen shell untuk '{base_exe_name_fallback}': {e_shell}")
                    return f"Error saat mencoba membuka {app_name_from_nlu}: {e_shell}"
            return f"Error saat mencoba membuka {app_name_from_nlu}: {e}"
    else:
        print(f"GAGAL (handle_open_application): Path atau perintah untuk aplikasi '{app_name_from_nlu}' tidak dapat ditemukan/dijalankan.")
        return f"Maaf, saya tidak dapat menemukan atau menjalankan aplikasi {app_name_from_nlu} di komputer Anda."

def handle_close_application(entities):
    app_name_to_close = entities.get("app_name")
    if not app_name_to_close:
        return "Aplikasi apa yang ingin Anda tutup?"

    app_name_lower = app_name_to_close.lower()
    print(f"INFO (handle_close_application): Mencoba menutup aplikasi: '{app_name_to_close}'")
    
    try:
        windows = gw.getWindowsWithTitle(app_name_to_close) 
        
        target_window = None
        all_titles = []
        for win in gw.getAllWindows():
             all_titles.append(win.title.lower()) 
             if app_name_lower in win.title.lower():
                 target_window = win
                 break 

        if target_window:
            print(f"  Menemukan jendela: '{target_window.title}'. Mencoba menutup...")
            target_window.close() 
            time.sleep(0.5) 
            if target_window.isClosed: 
                 return f"Aplikasi {app_name_to_close} seharusnya sudah ditutup."
            else:
                 print(f"  Jendela '{target_window.title}' tidak merespons .close(). Mencoba taskkill.")
                 process_map = {
                     "chrome": "chrome.exe",
                     "notepad": "notepad.exe",
                     "paint": "mspaint.exe",
                     "kalkulator": "calc.exe", 
                     "word": "winword.exe",
                     "spotify": "spotify.exe",
                     "excel": "excel.exe",
                 }
                 process_name = process_map.get(app_name_lower, f"{app_name_lower}.exe")
                 try:
                     subprocess.run(["taskkill", "/F", "/IM", process_name], check=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                     return f"Aplikasi {app_name_to_close} (proses {process_name}) telah ditutup paksa."
                 except subprocess.CalledProcessError:
                     return f"Gagal menutup paksa proses {process_name}. Mungkin sudah tertutup atau nama proses salah."
                 except FileNotFoundError: 
                     return f"Perintah taskkill tidak ditemukan. Tidak bisa menutup paksa."

        else:
            print(f"  Tidak ditemukan jendela yang cocok dengan '{app_name_to_close}'. Daftar judul yang terdeteksi: {all_titles}")
            process_map = {
                 "chrome": "chrome.exe", "notepad": "notepad.exe", "paint": "mspaint.exe", 
                 "kalkulator": "calc.exe", 
            }
            process_name_direct = process_map.get(app_name_lower)
            if process_name_direct:
                print(f"  Tidak ada jendela, mencoba taskkill langsung untuk proses: {process_name_direct}")
                try:
                    subprocess.run(["taskkill", "/F", "/IM", process_name_direct], check=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    return f"Proses {process_name_direct} untuk aplikasi {app_name_to_close} telah ditutup paksa."
                except Exception as e_tk_direct:
                    print(f"  Gagal taskkill direct: {e_tk_direct}")
                    return f"Tidak ditemukan jendela untuk {app_name_to_close}, dan gagal menutup prosesnya secara langsung."
            return f"Tidak dapat menemukan jendela aplikasi {app_name_to_close} yang aktif."

    except Exception as e:
        print(f"ERROR (handle_close_application): Terjadi kesalahan - {e}")
        return f"Maaf, terjadi kesalahan saat mencoba menutup {app_name_to_close}."

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
    if not api.GEMINI_MODEL_INITIALIZED or not config.gemini_chat_session: 
        return "Maaf, AI belum siap."
    if not user_prompt: 
        return "Tidak ada pertanyaan untuk AI."
    
    try:
        print(f"Kirim ke Gemini: {user_prompt}")
        response = config.gemini_chat_session.send_message(user_prompt)
        
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
    if not config.RECOGNIZER: return
    mic_to_use_idx = config.MIC_INDEX if config.MIC_INDEX is not None else None
    mic_display_name = f"indeks {config.MIC_INDEX}" if config.MIC_INDEX is not None else "default"
    try:
        with sr.Microphone(device_index=mic_to_use_idx) as source:
            print(f"Kalibrasi mic {mic_display_name} (2 detik)...")
            config.RECOGNIZER.adjust_for_ambient_noise(source, duration=2)
            print(f"Threshold mic {mic_display_name}: {config.RECOGNIZER.energy_threshold:.2f}")
    except Exception as e: 
        print(f"Peringatan: Gagal kalibrasi mic {mic_display_name}: {e}.")
        if config.MIC_INDEX is not None: 
            print("Mencoba kalibrasi mic default...")
            try:
                with sr.Microphone(device_index=None) as source_default:
                    config.RECOGNIZER.adjust_for_ambient_noise(source_default, duration=2)
                    print(f"Threshold mic default: {config.RECOGNIZER.energy_threshold:.2f}")
            except Exception as e_default: print(f"Gagal kalibrasi mic default juga: {e_default}")

def continuous_conversation_loop():
    initial_ambient_noise_adjustment(); consecutive_timeouts = 0 
    while config.is_continuous_mode_active:
        if not config.RECOGNIZER: print("Recognizer N/A..."); time.sleep(1); 
        print("\n[Percakapan Aktif] Menunggu..."); command_text = None
        try:
            with sr.Microphone(device_index=config.MIC_INDEX if config.MIC_INDEX is not None else None) as source:
                try:
                    print("Mendengarkan..."); audio = config.RECOGNIZER.listen(source, timeout=7, phrase_time_limit=10)
                    print("Audio diterima, mengenali..."); command_text = config.RECOGNIZER.recognize_google(audio, language='id-ID')
                    print(f"Anda: {command_text}"); consecutive_timeouts = 0 
                    if config.is_assistant_speaking and command_text: 
                        interruption_command = command_text.lower()
                        if any(word in interruption_command for word in ["stop", "berhenti", "diam", "cukup", "sudah"]):
                            print(f"INTERUPSI: '{interruption_command}'")
                            with config.tts_lock: 
                                    if pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                                    if hasattr(pygame.mixer.music, 'unload'): 
                                        try: 
                                            print(f"Thread TTS: Mencoba unload musik setelah interupsi di dalam listen...") 
                                            pygame.mixer.music.unload()
                                            print(f"Thread TTS: Musik di-unload (interupsi dalam listen).")
                                        except pygame.error as e_unload_inner: 
                                            print(f"Thread TTS: Pygame error saat unload (interupsi dalam listen): {e_unload_inner}")
                                            pass 
                                        config.is_assistant_speaking = False 
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
                    if not config.is_assistant_speaking: 
                        print("Tidak dapat memahami audio.")
                        speak_with_pygame("Hmm, kurang jelas. Ulangi?")
                    else: 
                        print("Audio tak dikenali saat AI bicara.")
                    continue 

                except sr.RequestError as e: 
                    consecutive_timeouts = 0
                    print(f"Masalah layanan STT; {e}")
                    if not config.is_assistant_speaking: 
                        speak_with_pygame("Masalah koneksi layanan suara.")
                    time.sleep(3) 
                    continue 

                except Exception as e: 
                    consecutive_timeouts = 0
                    print(f"Error listen/recognize: {e}")
                    if not config.is_assistant_speaking: 
                        speak_with_pygame("Error saat mendengarkan.")
                    continue 

            if command_text and not config.is_assistant_speaking: 
                nlu_result = process_nlu(command_text)
                intent = nlu_result["intent"]; entities = nlu_result["entities"]
                assistant_response = "Maaf, saya tidak paham." 
                print(f"Intent: {intent}, Entities: {entities}")

                if intent == "GOODBYE_APP":
                    assistant_response = "Baik, sampai jumpa!"
                    speak_with_pygame(assistant_response); time.sleep(1.5) 
                    config.is_continuous_mode_active = False 
                    if config.TRAY_ICON: config.TRAY_ICON.stop(); break 
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
                
                elif intent == "CLOSE_APPLICATION":
                    assistant_response = handle_close_application(entities)

                elif intent == "CHAINED_OPEN_THEN_TYPE":
                    assistant_response = handle_chained_open_then_type(entities)

                elif intent == "TYPE_IN_NEW_TAB_BROWSER":
                    assistant_response = handle_type_in_new_tab(entities)
                
                elif intent == "TYPE_TEXT":
                    assistant_response = handle_type_text(entities)

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
                    if not api.GEMINI_MODEL_INITIALIZED: # Cek variabel dari modul api
                        assistant_response = "Fitur AI belum aktif."
                    else:
                        assistant_response = api.send_to_gemini(entities["prompt"])
                speak_with_pygame(assistant_response)
            if not config.is_continuous_mode_active: break
        except sr.RequestError as e: print(f"Mic Error: {e}"); speak_with_pygame("Masalah mic. Mode stop."); config.is_continuous_mode_active=False; break
        except Exception as e: print(f"Loop Error: {e}"); speak_with_pygame("Error. Mode stop."); time.sleep(1); continue
    print("Mode percakapan berkelanjutan berhenti.")

def apply_settings(selected_voice_id_to_set, selected_mic_str_from_gui, window_ref):
    print(f"Terapkan: Suara ID = {selected_voice_id_to_set}, Mic Str = {selected_mic_str_from_gui}")
    applied_settings_feedback = []

    if config.TTS_ENGINE and selected_voice_id_to_set:
        current_tts_voice = config.TTS_ENGINE.getProperty('voice')
        if current_tts_voice != selected_voice_id_to_set:
            with config.tts_lock: 
                if config.is_assistant_speaking and pygame.mixer.get_init() and pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
                config.is_assistant_speaking = False 
            try:
                config.TTS_ENGINE.setProperty('voice', selected_voice_id_to_set)
                utils.save_configuration(selected_voice_id_to_set, config.MIC_INDEX) 
                applied_settings_feedback.append("Suara berhasil diubah.")
            except Exception as e: print(f"Gagal ubah suara TTS: {e}"); messagebox.showerror("Error Suara", f"Gagal ubah suara: {e}", parent=window_ref)
        else: print("Suara TTS tidak berubah.")
    
    new_mic_idx_val = None
    if selected_mic_str_from_gui == "Default Sistem": new_mic_idx_val = None
    elif selected_mic_str_from_gui and ":" in selected_mic_str_from_gui:
        try: new_mic_idx_val = int(selected_mic_str_from_gui.split(":")[0].strip())
        except ValueError: print(f"Indeks mic tidak valid: {selected_mic_str_from_gui}"); messagebox.showerror("Error Mikrofon", "Indeks mic tidak valid.", parent=window_ref); new_mic_idx_val = config.MIC_INDEX
    
    if config.MIC_INDEX != new_mic_idx_val:
        config.MIC_INDEX = new_mic_idx_val
        print(f"Mikrofon diubah ke: {config.MIC_INDEX if config.MIC_INDEX is not None else 'Default'}")
        utils.save_configuration(config.TTS_ENGINE.getProperty('voice') if config.TTS_ENGINE else None, config.MIC_INDEX)
        applied_settings_feedback.append("Mikrofon berhasil diubah.")
        initial_ambient_noise_adjustment() 
    else: print("Mikrofon tidak berubah.")
    
    if applied_settings_feedback:
        speak_with_pygame("Pengaturan telah diterapkan: " + ", ".join(applied_settings_feedback))
    else:
        pass

    if window_ref and window_ref.winfo_exists(): config.settings_window_close_event.set()

def toggle_continuous_listening(icon, item):
    config.is_continuous_mode_active = not config.is_continuous_mode_active
    if config.is_continuous_mode_active:
        if not config.TTS_ENGINE or not config.RECOGNIZER or not pygame.mixer.get_init():
            speak_with_pygame("Engine suara atau pygame belum siap.")
            config.is_continuous_mode_active = False 
            return
        speak_with_pygame("Mode percakapan berkelanjutan diaktifkan.")
        gui.show_desktop_icon() 
        if not (config.continuous_listen_thread and config.continuous_listen_thread.is_alive()):
            print("Memulai thread percakapan...")
            config.continuous_listen_thread = threading.Thread(target=continuous_conversation_loop, daemon=True, name="ContinuousListenThread")
            config.continuous_listen_thread.start()
        else:
            print("Thread percakapan sudah berjalan.")
    else:
        print("Sinyal menghentikan percakapan dikirim.")
        speak_with_pygame("Mode percakapan berkelanjutan akan dihentikan.")
        gui.hide_desktop_icon() 
    if config.TRAY_ICON:
        try:
            config.TRAY_ICON.update_menu()
        except Exception as e_update_menu:
            print(f"Tidak bisa update menu tray: {e_update_menu}") 

def get_listening_status_text(item): 
    return "Hentikan Percakapan" if config.is_continuous_mode_active else "Mulai Percakapan"

def quit_action(icon, item):
    print("Menerima perintah keluar...")
    config.is_continuous_mode_active = False
    gui.hide_desktop_icon()

    if config.desktop_icon_thread and config.desktop_icon_thread.is_alive():
        print("Menghentikan thread ikon desktop...")
        config.desktop_icon_shutdown_event.set()

    if config.settings_window and config.settings_window.winfo_exists():
        print("Menutup jendela pengaturan...")
        config.settings_window_close_event.set()
        time.sleep(0.5) 

    with config.tts_lock:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        config.is_assistant_speaking = False
        if config.tts_thread and config.tts_thread.is_alive():
            config.tts_thread.join(timeout=0.5)
    
    speak_with_pygame("Menutup asisten. Sampai jumpa!")
    final_tts_thread_ref = None
    with config.tts_lock:
        final_tts_thread_ref = config.tts_thread
    
    if final_tts_thread_ref and final_tts_thread_ref.is_alive():
        print("Menunggu pesan keluar terakhir...")
        final_tts_thread_ref.join(timeout=3.0)
    
    if config.continuous_listen_thread and config.continuous_listen_thread.is_alive():
        print("Menunggu thread percakapan...")
        config.continuous_listen_thread.join(timeout=1.0)

    if config.desktop_icon_thread and config.desktop_icon_thread.is_alive():
        print("Menunggu thread ikon desktop selesai...")
        config.desktop_icon_thread.join(timeout=2.0) 
        if config.desktop_icon_thread.is_alive():
            print("Peringatan: Thread ikon desktop tidak berhenti tepat waktu.")

    if config.TRAY_ICON:
        print("Menghentikan ikon tray...")
        config.TRAY_ICON.stop()
    
    if pygame.mixer.get_init():
        pygame.mixer.quit()
    if pygame.get_init():
        pygame.quit()
    
    print("Aplikasi ditutup.")
    os._exit(0) 

def new_quit_action(): 
    print("Perintah keluar diterima...")
    config.is_continuous_mode_active = False 

    if config.desktop_icon_window and config.desktop_icon_window.winfo_exists():
        print("Menutup jendela ikon desktop...")
        if config.desktop_icon_shutdown_event: config.desktop_icon_shutdown_event.set()

    if config.settings_window and config.settings_window.winfo_exists():
        print("Menutup jendela pengaturan...")
        if config.settings_window_close_event: config.settings_window_close_event.set()

    print("Menghentikan thread TTS...")
    with config.tts_lock:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        config.is_assistant_speaking = False 
        if config.tts_thread and config.tts_thread.is_alive():
            config.tts_thread.join(timeout=0.5) 

    print("Menghentikan thread percakapan berkelanjutan...")
    if config.continuous_listen_thread and config.continuous_listen_thread.is_alive():
        config.continuous_listen_thread.join(timeout=1.0)

    if config.tray_icon_object:
        print("Menghentikan ikon tray...")
        config.tray_icon_object.stop()
    if config.tray_icon_thread and config.tray_icon_thread.is_alive():
        print("Menunggu thread pystray selesai...")
        config.tray_icon_thread.join(timeout=1.0)

    if pygame.mixer.get_init():
        pygame.mixer.quit()
    if pygame.get_init():
        pygame.quit()
    print("Pygame dihentikan.")

    if config.main_tk_root:
        print("Menjadwalkan penutupan aplikasi Tkinter utama...")
        config.main_tk_root.destroy() 
    
    print("Proses keluar hampir selesai.")

def apply_settings_tk(selected_voice_display_from_gui, selected_mic_display_from_gui, window_ref):
    print(f"Terapkan (TK): Suara Display = {selected_voice_display_from_gui}, Mic Display = {selected_mic_display_from_gui}")
    applied_settings_feedback = []
    
    selected_voice_id_to_set = None
    if config.TTS_ENGINE and selected_voice_display_from_gui and config.available_voice_ids_settings_cache:
        try:
            idx_voice = config.available_voices_display.index(selected_voice_display_from_gui) 
            selected_voice_id_to_set = config.available_voice_ids_settings_cache[idx_voice]
        except (ValueError, IndexError):
            print(f"Error: Display suara '{selected_voice_display_from_gui}' tidak ditemukan di cache.")
            selected_voice_id_to_set = config.TTS_ENGINE.getProperty('voice') 

    if config.TTS_ENGINE and selected_voice_id_to_set:
        current_tts_voice_id = config.TTS_ENGINE.getProperty('voice')
        if current_tts_voice_id != selected_voice_id_to_set:
            with config.tts_lock:
                if config.is_assistant_speaking and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                config.is_assistant_speaking = False 
            
            try:
                config.TTS_ENGINE.setProperty('voice', selected_voice_id_to_set)
                utils.save_configuration(selected_voice_id_to_set, config.MIC_INDEX)
                applied_settings_feedback.append("Suara berhasil diubah.")
                print(f"Suara TTS diubah ke ID: {selected_voice_id_to_set}")
            except Exception as e:
                print(f"Gagal mengubah suara TTS: {e}")
                messagebox.showerror("Error Suara", f"Gagal mengubah suara: {e}", parent=window_ref)
        else:
            print("Suara TTS tidak berubah (sudah sama).")

    new_mic_idx_val = config.MIC_INDEX 
    if selected_mic_display_from_gui in config.mic_map_display_to_index: 
        new_mic_idx_val = config.mic_map_display_to_index[selected_mic_display_from_gui]
    else:
        print(f"Error: Display mic '{selected_mic_display_from_gui}' tidak ditemukan di map.")


    if config.MIC_INDEX != new_mic_idx_val:
        config.MIC_INDEX = new_mic_idx_val
        print(f"Mikrofon diubah ke: Indeks {config.MIC_INDEX if config.MIC_INDEX is not None else 'Default Sistem'}")
        current_voice_id_for_save = config.TTS_ENGINE.getProperty('voice') if config.TTS_ENGINE else None
        utils.save_configuration(current_voice_id_for_save, config.MIC_INDEX)
        applied_settings_feedback.append("Mikrofon berhasil diubah.")
        if config.is_continuous_mode_active or True: 
            initial_ambient_noise_adjustment()
    else:
        print("Mikrofon tidak berubah (sudah sama).")

    if applied_settings_feedback:
        speak_with_pygame("Pengaturan telah diterapkan: " + ", dan ".join(applied_settings_feedback))
        messagebox.showinfo("Pengaturan Diterapkan", "Pengaturan telah diterapkan.", parent=window_ref)
    else:
        messagebox.showinfo("Pengaturan", "Tidak ada perubahan pada pengaturan.", parent=window_ref)

    gui._destroy_settings_window()

def main():
    config.main_tk_root = tk.Tk()
    config.main_tk_root.withdraw() 
    config.main_tk_root.title("Windows Assistant Root") 
    config.main_tk_root.quit_called = False

    loaded_voice_id = utils.load_configuration()
    initialize_engines(preferred_voice_id=loaded_voice_id) 

    print("INFO (__main__): Memanggil create_desktop_icon_tk...")
    gui.create_desktop_icon_tk(config.main_tk_root) 

    if not config.TTS_ENGINE: print("PERINGATAN: Mesin TTS tidak aktif!") 
    if not pygame.mixer.get_init(): print("PERINGATAN: Pygame Mixer tidak aktif!") 
    if not api.GEMINI_MODEL_INITIALIZED: 
        print("PERINGATAN (__main__): Model Gemini tidak aktif")
    else:
        print("INFO (__main__): Model Gemini AKTIF")

    print("INFO (__main__): Memanggil setup_pystray_icon_thread...")
    gui.setup_pystray_icon_thread(config.main_tk_root) 

    print("Asisten Windows di System Tray. Klik ikon untuk opsi.") 
    print("Menjalankan loop utama Tkinter (main_tk_root.mainloop())...")
    
    try:
        config.main_tk_root.mainloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt diterima. Memulai proses keluar...")
        new_quit_action() 
    finally:
        print("Loop utama Tkinter (main_tk_root.mainloop()) telah berhenti.")
        if config.tray_icon_object and config.tray_icon_object.visible:
            print("Memastikan pystray berhenti...")
            config.tray_icon_object.stop()
        if config.tray_icon_thread and config.tray_icon_thread.is_alive():
            config.tray_icon_thread.join(timeout=1.0)
        print("Aplikasi ditutup sepenuhnya.")

if __name__ == "__main__":
    main()