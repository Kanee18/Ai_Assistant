import json
import os
import shutil
import string
import winreg
import spacy
from spacy.matcher import Matcher

import config

def save_configuration(voice_id, mic_idx):
    config_data = {"voice_id": voice_id, "mic_index": mic_idx}
    try:
        with open(config.CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"Konfigurasi berhasil disimpan ke {config.CONFIG_FILE}")
    except Exception as e:
        print(f"Gagal menyimpan konfigurasi: {e}")

def load_configuration():
    voice_id_from_config = None
    
    if os.path.exists(config.CONFIG_FILE):
        try:
            with open(config.CONFIG_FILE, 'r') as f:
                config_data = json.load(f)
            print(f"Konfigurasi dimuat dari {config.CONFIG_FILE}: {config_data}")
            
            mic_idx_cfg = config_data.get("mic_index")
            if isinstance(mic_idx_cfg, int):
                config.MIC_INDEX = mic_idx_cfg
            elif mic_idx_cfg is None: 
                config.MIC_INDEX = None
            else:
                print(f"Peringatan: mic_index di config ('{mic_idx_cfg}') tidak valid, menggunakan default.")
                config.MIC_INDEX = None 
            
            voice_id_from_config = config_data.get("voice_id")
        except Exception as e:
            print(f"Gagal memuat atau mem-parse konfigurasi dari {config.CONFIG_FILE}: {e}")
            config.MIC_INDEX = None 
    else:
        print(f"File konfigurasi {config.CONFIG_FILE} tidak ditemukan. Menggunakan pengaturan default.")
        config.MIC_INDEX = None 
    
    return voice_id_from_config

def define_spacy_patterns():
    if not config.MATCHER or not config.NLP: 
        print("SpaCy Matcher atau NLP model belum siap untuk mendefinisikan pola.") 
        return

    pattern_open_app = [
        {"LOWER": {"IN": ["buka", "jalankan", "aktifkan"]}},
        {"LOWER": "aplikasi", "OP": "?"}, 
        {"IS_ALPHA": True, "OP": "+"} 
    ]
    config.MATCHER.add("OPEN_APPLICATION_SPACY", [pattern_open_app])

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

    pattern_close_app = [
        {"LOWER": {"IN": ["tutup", "close", "hentikan"]}}, 
        {"LOWER": "aplikasi", "OP": "?"}, 
        {"IS_ALPHA": True, "OP": "+"} 
    ]
    config.MATCHER.add("CLOSE_APPLICATION_SPACY", [pattern_close_app])
    config.MATCHER.add("SEARCH_INFO_SPACY", [pattern_search_info_1, pattern_search_info_2, pattern_search_info_3])
    
    print("Pola-pola spaCy Matcher telah didefinisikan.")

def initialize_spacy_model():
    if config.SPACY_MODEL_INITIALIZED: 
        print("Model spaCy sudah diinisialisasi sebelumnya.")
        return
    try:
        config.NLP = spacy.load("en_core_web_sm") 
        print("Model spaCy 'en_core_web_sm' berhasil dimuat.")
        config.MATCHER = Matcher(config.NLP.vocab)
        define_spacy_patterns() 
        config.SPACY_MODEL_INITIALIZED = True
    except OSError:
        print("KRITIS: Gagal memuat model spaCy 'en_core_web_sm'.")
        print("Pastikan Anda sudah mengunduhnya dengan: python -m spacy download en_core_web_sm")
        config.NLP = None; config.MATCHER = None; config.SPACY_MODEL_INITIALIZED = False
    except Exception as e:
        print(f"Error saat memuat model spaCy atau membuat Matcher: {e}")
        config.NLP = None; config.MATCHER = None; config.SPACY_MODEL_INITIALIZED = False

def find_executable_path(app_name_from_nlu, target_exe_name=None):
    """
    Mencari path lengkap ke sebuah executable aplikasi di Windows secara lebih komprehensif.

    Args:
        app_name_from_nlu (str): Nama aplikasi yang diucapkan pengguna (misalnya "blender", "discord").
        target_exe_name (str, optional): Nama file .exe yang spesifik jika diketahui (misalnya "blender.exe"). 
                                         Jika None, akan dicoba dibuat dari app_name_from_nlu.

    Returns:
        str or None: Path lengkap ke executable jika ditemukan, atau None jika tidak.
    """
    print(f"INFO (find_executable_path): Memulai pencarian untuk aplikasi NLU: '{app_name_from_nlu}', target .exe: '{target_exe_name}'")

    exe_to_search = target_exe_name
    if not exe_to_search:
        if app_name_from_nlu.lower().endswith(".exe"):
            exe_to_search = app_name_from_nlu
        else:
            exe_to_search = app_name_from_nlu + ".exe"
    
    print(f"  Akan mencari file executable: '{exe_to_search}'")

    app_paths_keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"
    ]
    registries_to_check = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    for hkey_type in registries_to_check:
        for app_path_key in app_paths_keys:
            try:
                with winreg.OpenKey(hkey_type, os.path.join(app_path_key, exe_to_search)) as key:
                    executable_path, _ = winreg.QueryValueEx(key, None)
                    if os.path.exists(executable_path) and os.path.isfile(executable_path):
                        print(f"  INFO: Ditemukan di Registry: {executable_path}")
                        return executable_path
            except FileNotFoundError:
                continue
            except Exception: 
                continue
    print(f"  INFO: Tidak ditemukan '{exe_to_search}' di Registry App Paths.")

    print(f"  INFO: Mencari '{exe_to_search}' di variabel PATH (shutil.which)...")
    path_from_which = shutil.which(exe_to_search)
    if path_from_which and os.path.exists(path_from_which):
        print(f"  INFO: Ditemukan via shutil.which (PATH): {path_from_which}")
        return path_from_which
    
    if not app_name_from_nlu.lower().endswith(".exe") and app_name_from_nlu.lower() != exe_to_search.replace(".exe", "").lower():
        print(f"  INFO: Mencari '{app_name_from_nlu}' (nama NLU asli) di PATH (shutil.which)...")
        path_from_which_alias = shutil.which(app_name_from_nlu)
        if path_from_which_alias and os.path.exists(path_from_which_alias):
            print(f"  INFO: Ditemukan alias NLU via shutil.which (PATH): {path_from_which_alias}")
            return path_from_which_alias
    print(f"  INFO: Tidak ditemukan '{exe_to_search}' atau '{app_name_from_nlu}' di variabel PATH.")

    common_install_folders = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    if os.environ.get("LOCALAPPDATA"):
        common_install_folders.append(os.path.join(os.environ.get("LOCALAPPDATA"), "Programs"))

    for common_folder_root in common_install_folders:
        if not common_folder_root or not os.path.isdir(common_folder_root):
            continue
        print(f"  INFO: Mencari '{exe_to_search}' di dalam dan sekitar '{common_folder_root}'...")
        potential_path = os.path.join(common_folder_root, exe_to_search)
        if os.path.exists(potential_path) and os.path.isfile(potential_path):
            print(f"    DITEMUKAN: {potential_path}")
            return potential_path
        
        path_in_app_named_folder = os.path.join(common_folder_root, app_name_from_nlu, exe_to_search)
        if os.path.exists(path_in_app_named_folder) and os.path.isfile(path_in_app_named_folder):
            print(f"    DITEMUKAN: {path_in_app_named_folder}")
            return path_in_app_named_folder

        for dirpath, dirnames, filenames in os.walk(common_folder_root):
            current_depth = dirpath.replace(common_folder_root, '').count(os.sep)
            if current_depth > 2: 
                dirnames[:] = [] 
                continue
            if exe_to_search in filenames:
                found_path = os.path.join(dirpath, exe_to_search)
                if os.path.isfile(found_path): 
                     print(f"    DITEMUKAN (os.walk di {common_folder_root}): {found_path}")
                     return found_path
    print(f"  INFO: Tidak ditemukan '{exe_to_search}' di lokasi instalasi umum standar.")

    print(f"INFO: Memulai pencarian menyeluruh untuk '{exe_to_search}' di semua drive (ini bisa memakan waktu cukup lama)...")

    available_drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:")]
    print(f"  Drive yang akan diperiksa: {available_drives}")

    excluded_folders_keywords = [
        "\\windows\\", "\\winnt\\", 
        "\\$recycle.bin\\", "\\system volume information\\",
        "\\recovery\\", "\\config.msi\\",
        "\\drivers\\", "\\temp\\", "\\tmp\\",
        "\\appdata\\roaming\\", 
        "\\program files (x86)\\", "\\program files\\", "\\appdata\\local\\programs\\" 
    ]
    excluded_general_keywords = ["\\steam\\steamapps\\common\\", "\\python\\lib\\site-packages\\"]


    for drive in available_drives:
        print(f"  Mencari di drive: {drive}...")

        for root_dir, dirnames, files in os.walk(drive, topdown=True):
            dirnames[:] = [d for d in dirnames if not any(excluded_keyword in os.path.join(root_dir, d).lower() for excluded_keyword in excluded_folders_keywords + excluded_general_keywords)]
            
            if exe_to_search.lower() in (f.lower() for f in files): 
                for f_actual_case in files:
                    if f_actual_case.lower() == exe_to_search.lower():
                        found_path = os.path.join(root_dir, f_actual_case)
                        if os.path.isfile(found_path):
                            print(f"  DITEMUKAN (pencarian menyeluruh di {drive}): {found_path}")
                            return found_path
        print(f"  Selesai mencari di drive: {drive}")

    print(f"GAGAL AKHIR (find_executable_path): Path untuk '{app_name_from_nlu}' (target: {exe_to_search}) tidak dapat ditemukan setelah semua metode.")
    return None