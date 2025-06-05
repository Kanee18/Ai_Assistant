import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
import time
import threading

import config
import utils
from main import apply_settings_tk, toggle_continuous_listening, new_quit_action, get_listening_status_text

def _destroy_settings_window():
    try:
        if config.settings_window and config.settings_window.winfo_exists():
            print("  _destroy_settings_window: Mencoba menghancurkan jendela pengaturan yang ada.")
            try:
                config.settings_window.grab_release()
                print("    Settings window: grab_release() berhasil.")
            except tk.TclError as e_grab:
                print(f"    Settings window: Error saat grab_release: {e_grab}")
            try:
                config.settings_window.destroy()
                print("    Settings window: Jendela berhasil dihancurkan.")
            except tk.TclError as e_destroy:
                print(f"    Settings window: Error saat destroy: {e_destroy}")
        elif config.settings_window:
            print("  _destroy_settings_window: settings_window ada tapi winfo_exists() false.")
        else:
            print("  _destroy_settings_window: Tidak ada settings_window untuk dihancurkan.")
            
    except Exception as e_outer:
        print(f"  _destroy_settings_window: Error tak terduga selama proses destroy: {e_outer}")
    finally:
        config.settings_window = None
        print("  Variabel global settings_window DIJAMIN di-reset ke None (dalam blok finally).")

def _create_actual_settings_gui():
    if not config.main_tk_root:
        print("Error (_create_actual_settings_gui): Root Tkinter utama belum siap.")
        return

    if config.settings_window is not None and config.settings_window.winfo_exists():
        print("Jendela pengaturan sudah ada (menurut .winfo_exists()), mencoba memulihkan.")
        revived_successfully = False
        try:
            current_state = config.settings_window.state()
            is_mapped = config.settings_window.winfo_ismapped()
            geom = "N/A"
            try: geom = config.settings_window.geometry()
            except tk.TclError: geom = "Error saat ambil geometri"

            print(f"  Info Jendela Saat Ini: ID={config.settings_window}, State='{current_state}', Terpetakan='{is_mapped}', Geometri='{geom}'")

            if current_state == 'withdrawn' or not is_mapped:
                print(f"    Jendela dalam kondisi '{current_state}' atau tidak terpetakan. Mencoba 'deiconify'.")
                config.settings_window.deiconify()
            
            config.settings_window.lift()
            config.settings_window.focus_set()
            
            config.settings_window.update_idletasks()
            win_width = config.settings_window.winfo_width()
            win_height = config.settings_window.winfo_height()

            if win_width <= 1 or geom.startswith("1x1"): win_width = 650 
            if win_height <= 1 or geom.startswith("1x1"): win_height = 300
            
            scr_width = config.settings_window.winfo_screenwidth()
            scr_height = config.settings_window.winfo_screenheight()
            new_x = (scr_width // 2) - (win_width // 2)
            new_y = (scr_height // 2) - (win_height // 2)
            
            print(f"    Mengatur ulang geometri ke: {win_width}x{win_height}+{new_x}+{new_y}")
            config.settings_window.geometry(f"{win_width}x{win_height}+{new_x}+{new_y}")
            
            config.settings_window.grab_set()

            config.settings_window.update_idletasks() 
            if config.settings_window.winfo_ismapped() and config.settings_window.state() == 'normal':
                revived_successfully = True
                print("    Jendela pengaturan berhasil dipulihkan dan ditampilkan.")
            else:
                print(f"  PERINGATAN SETELAH PEMULIHAN: State='{config.settings_window.state()}', Terpetakan='{config.settings_window.winfo_ismapped()}'")
                print("  Gagal memulihkan jendela pengaturan agar terlihat sepenuhnya.")

        except tk.TclError as e:
            print(f"    Error Tcl saat memulihkan jendela pengaturan yang ada: {e}")
        
        if not revived_successfully:
            print("    Upaya pemulihan gagal. Memaksa penghancuran jendela pengaturan yang bermasalah.")
            _destroy_settings_window() 
        else:
            return 

    if config.settings_window is None: 
        print("Membuat instance BARU untuk jendela pengaturan...")
        
        config.available_voices_display.clear()
        config.available_voice_ids_settings_cache.clear()
        config.mic_map_display_to_index.clear()
        config.mic_map_display_to_index["Default Sistem"] = None

        if not config.TTS_ENGINE:
            print("TTS Engine N/A, batal buka pengaturan baru.")
            if config.main_tk_root and config.main_tk_root.winfo_exists():
                messagebox.showerror("Error TTS", "Mesin TTS tidak aktif. Pengaturan tidak bisa dibuka.", 
                                     parent=config.main_tk_root if config.main_tk_root.winfo_exists() else None)
            return

        config.settings_window = tk.Toplevel(config.main_tk_root)
        config.settings_window.title("Pengaturan Suara & Mikrofon")
        config.settings_window.geometry("650x300") 
        config.settings_window.resizable(False, False)

        main_frame = ttk.Frame(config.settings_window, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        tts_frame = ttk.LabelFrame(main_frame, text="Output Suara (TTS)", padding="10")

        tts_frame.pack(pady=10, fill=tk.X)
        ttk.Label(tts_frame, text="Pilih Suara:").pack(side=tk.LEFT, padx=5, pady=5, anchor='w')
        if config.TTS_ENGINE:
            voices_props = config.TTS_ENGINE.getProperty('voices')
            for voice in voices_props:
                lang_str = ", ".join([lang.decode('utf-8', 'ignore') for lang in voice.languages]) if voice.languages else "N/A"
                display_name = f"{voice.name} (Lang: {lang_str})"
                config.available_voices_display.append(display_name)
                config.available_voice_ids_settings_cache.append(voice.id)
        selected_voice_display_str = tk.StringVar() 
        voice_dropdown = ttk.Combobox(tts_frame, textvariable=selected_voice_display_str, values=config.available_voices_display, state="readonly", width=60)
        if config.TTS_ENGINE:
            current_voice_id_tts = config.TTS_ENGINE.getProperty('voice')
            try:
                current_voice_idx_in_list = config.available_voice_ids_settings_cache.index(current_voice_id_tts)
                selected_voice_display_str.set(config.available_voices_display[current_voice_idx_in_list])
            except (ValueError, IndexError):
                if config.available_voices_display: selected_voice_display_str.set(config.available_voices_display[0])
                else: selected_voice_display_str.set("Tidak ada suara"); voice_dropdown.config(state="disabled")
        else: selected_voice_display_str.set("TTS tidak aktif"); voice_dropdown.config(state="disabled")
        voice_dropdown.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

        mic_frame = ttk.LabelFrame(main_frame, text="Input Audio (Mikrofon)", padding="10")
        mic_frame.pack(pady=10, fill=tk.X)
        ttk.Label(mic_frame, text="Pilih Mikrofon:").pack(side=tk.LEFT, padx=5, pady=5, anchor='w')
        mic_display_list = ["Default Sistem"]
        try:
            import speech_recognition as sr
            mic_list_from_sr = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(mic_list_from_sr):
                display_name = f"{idx}: {name[:55]}"
                mic_display_list.append(display_name)
                config.mic_map_display_to_index[display_name] = idx
        except Exception as e: print(f"Gagal dapat daftar mic: {e}")
        selected_mic_display_str = tk.StringVar() 
        mic_dropdown = ttk.Combobox(mic_frame, textvariable=selected_mic_display_str, values=mic_display_list, state="readonly", width=60)
        current_mic_set_display = "Default Sistem"
        if config.MIC_INDEX is not None:
            for display_name_key, idx_val_map in config.mic_map_display_to_index.items():
                if idx_val_map == config.MIC_INDEX: current_mic_set_display = display_name_key; break
        selected_mic_display_str.set(current_mic_set_display)
        mic_dropdown.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5, pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20, side=tk.BOTTOM, fill=tk.X)
        cancel_btn = ttk.Button(button_frame, text="Batal", command=_destroy_settings_window)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 5))
        apply_btn = ttk.Button(button_frame, text="Terapkan & Tutup",
            command=lambda: apply_settings_tk(selected_voice_display_str.get(),selected_mic_display_str.get(),config.settings_window))
        apply_btn.pack(side=tk.RIGHT, padx=(0,10))

        def on_closing_settings_via_x():
            print("Tombol X jendela pengaturan ditekan.")
            _destroy_settings_window()
        
        config.settings_window.protocol("WM_DELETE_WINDOW", on_closing_settings_via_x)
        
        print("Mencoba deiconify jendela pengaturan yang baru dibuat...")
        config.settings_window.deiconify() 
        
        try:
            config.settings_window.grab_set()
            config.settings_window.focus_set() 
            print("Jendela pengaturan baru berhasil di-grab dan fokus di-set.")
        except tk.TclError as e:
            print(f"Error saat grab_set/focus_set pada jendela pengaturan baru: {e}")
        
        print(f"Status jendela baru setelah dibuat: State='{config.settings_window.state()}', Terpetakan='{config.settings_window.winfo_ismapped()}'")

    else: 
        print("Kondisi tidak terduga: settings_window bukan None tapi juga tidak winfo_exists(). Memanggil _destroy_settings_window.")
        _destroy_settings_window()

def _create_desktop_icon_window():
    try:
        root = tk.Tk()
        config.desktop_icon_window = root 
        root.title("Tes Ikon Asisten - KOTAK MERAH") 
        root.withdraw()

        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)

        DEBUG_FRAME_COLOR = "red" 
        debug_width = 150  
        debug_height = 150 

        root.config(bg=DEBUG_FRAME_COLOR) 

        try:
            pil_image = Image.open(config.DESKTOP_ICON_IMAGE_PATH)
            config.desktop_icon_photo = ImageTk.PhotoImage(pil_image)
        except FileNotFoundError:
            print(f"ERROR: Desktop icon image not found at {config.DESKTOP_ICON_IMAGE_PATH}")
            from main import speak_with_pygame
            speak_with_pygame(f"Icon image not found.") 
            config.desktop_icon_shutdown_event.set() 
            return
        except Exception as e:
            print(f"ERROR: Could not load desktop icon image: {e}")
            config.desktop_icon_shutdown_event.set()
            return

        root.config(bg=config.MACOS_LIKE_ICON_BG_COLOR)
        root.attributes("-transparentcolor", config.MACOS_LIKE_ICON_BG_COLOR)

        config.desktop_icon_label = tk.Label(root, image=config.desktop_icon_photo, bg=config.MACOS_LIKE_ICON_BG_COLOR)
        config.desktop_icon_label.pack()

        root.update_idletasks() 
        
        window_width = debug_width
        window_height = debug_height

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_pos = (screen_width // 2) - (window_width // 2)
        y_pos = screen_height - window_height - 100 
        root.geometry(f'{window_width}x{window_height}+{x_pos}+{y_pos}')

        print("Jendela ikon (DEBUG KOTAK MERAH) dibuat dan diposisikan.") 

        while not config.desktop_icon_shutdown_event.is_set():
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
        if config.desktop_icon_window and config.desktop_icon_window.winfo_exists():
            try:
                config.desktop_icon_window.destroy()
            except tk.TclError:
                pass 
        config.desktop_icon_window = None 
        print("Thread ikon desktop (DEBUG KOTAK MERAH) selesai.") 

def create_desktop_icon_tk(parent_root):
    if not parent_root:
        print("ERROR (create_desktop_icon_tk): Root Tkinter utama (parent_root) tidak ada.")
        return

    if config.desktop_icon_window and config.desktop_icon_window.winfo_exists():
        print("INFO (create_desktop_icon_tk): Jendela ikon desktop lama ditemukan, menghancurkan...")
        config.desktop_icon_window.destroy()
        config.desktop_icon_window = None

    config.desktop_icon_window = tk.Toplevel(parent_root)
    config.desktop_icon_window.withdraw() 

    config.desktop_icon_window.overrideredirect(True) 
    config.desktop_icon_window.wm_attributes("-topmost", True) 

    try:
        print(f"INFO (create_desktop_icon_tk): Mencoba memuat gambar dari '{config.DESKTOP_ICON_IMAGE_PATH}'")
        pil_image = Image.open(config.DESKTOP_ICON_IMAGE_PATH)
        print(f"  Gambar dimuat: Ukuran={pil_image.size}, Mode={pil_image.mode}")

        config.desktop_icon_photo = ImageTk.PhotoImage(pil_image)
    
    except FileNotFoundError:
        print(f"KRITIS (create_desktop_icon_tk): File gambar ikon '{config.DESKTOP_ICON_IMAGE_PATH}' tidak ditemukan.")
        if config.main_tk_root and config.main_tk_root.winfo_exists():
            config.main_tk_root.after(0, lambda: messagebox.showerror("Error Gambar Ikon Desktop", f"File gambar '{config.DESKTOP_ICON_IMAGE_PATH}' tidak ditemukan. Ikon tidak akan tampil.", parent=config.main_tk_root))
        if config.desktop_icon_window and config.desktop_icon_window.winfo_exists(): config.desktop_icon_window.destroy()
        config.desktop_icon_window = None
        return
    except Exception as e:
        print(f"KRITIS (create_desktop_icon_tk): Tidak bisa memuat atau memproses gambar ikon: {e}")
        if config.main_tk_root and config.main_tk_root.winfo_exists():
            config.main_tk_root.after(0, lambda: messagebox.showerror("Error Gambar Ikon Desktop", f"Tidak bisa memuat gambar ikon: {e}", parent=config.main_tk_root))
        if config.desktop_icon_window and config.desktop_icon_window.winfo_exists(): config.desktop_icon_window.destroy()
        config.desktop_icon_window = None
        return

    config.desktop_icon_window.config(bg=config.MACOS_LIKE_ICON_BG_COLOR)
    config.desktop_icon_window.attributes("-transparentcolor", config.MACOS_LIKE_ICON_BG_COLOR)

    if config.desktop_icon_label and config.desktop_icon_label.winfo_exists():
        config.desktop_icon_label.destroy()
        
    config.desktop_icon_label = tk.Label(config.desktop_icon_window, image=config.desktop_icon_photo, bg=config.MACOS_LIKE_ICON_BG_COLOR)
    config.desktop_icon_label.pack() 

    config.desktop_icon_window.update_idletasks()
    
    print(f"INFO (create_desktop_icon_tk): Objek Toplevel ikon desktop telah dibuat (tersembunyi). Ukuran awal dari gambar: {config.desktop_icon_window.winfo_width()}x{config.desktop_icon_window.winfo_height()}")


def _set_icon_position():
    if config.desktop_icon_window and config.desktop_icon_window.winfo_exists():
        config.desktop_icon_window.update_idletasks() 
        
        window_width = config.desktop_icon_window.winfo_width()
        window_height = config.desktop_icon_window.winfo_height()
        
        if window_width <= 1 or window_height <= 1:
            print(f"PERINGATAN (_set_icon_position): Ukuran jendela ikon tidak valid ({window_width}x{window_height}). Mungkin gambar gagal render. Ikon tidak akan diposisikan/ditampilkan dengan benar.")
            return 

        screen_width = config.desktop_icon_window.winfo_screenwidth()
        screen_height = config.desktop_icon_window.winfo_screenheight()
        
        x_pos = (screen_width // 2) - (window_width // 2)
        y_pos = screen_height - window_height - 100 
        
        config.desktop_icon_window.geometry(f'+{x_pos}+{y_pos}') 
        print(f"INFO (_set_icon_position): Posisi ikon desktop diatur ke X:{x_pos}, Y:{y_pos} (Ukuran jendela: {window_width}x{window_height})")
    else:
        print("PERINGATAN (_set_icon_position): Jendela ikon desktop tidak ada untuk diatur posisinya.")

def show_desktop_icon():
    def _show():
        print("DEBUG (show_desktop_icon._show): Dipanggil.")
        if config.desktop_icon_window and config.desktop_icon_window.winfo_exists():
            print(f"  Jendela ikon ada. State awal: {config.desktop_icon_window.state()}, Terpetakan: {config.desktop_icon_window.winfo_ismapped()}")
            _set_icon_position() 
            config.desktop_icon_window.deiconify() 
            config.desktop_icon_window.lift() 
            print(f"  Ikon desktop di-deiconify dan lift. State akhir: {config.desktop_icon_window.state()}, Terpetakan: {config.desktop_icon_window.winfo_ismapped()}")
            if not config.desktop_icon_window.winfo_ismapped():
                print("  PERINGATAN (_show): Ikon desktop MASIH tidak terpetakan setelah deiconify/lift.")
        elif not config.desktop_icon_window:
            print("ERROR (_show): Tidak bisa menampilkan ikon, objek jendela ikon adalah None (mungkin gagal dibuat).")
        else: 
            print("ERROR (_show): Tidak bisa menampilkan ikon, jendela ikon sudah dihancurkan.")

    if config.main_tk_root:
        config.main_tk_root.after(0, _show)
    else:
        print("KRITIS (show_desktop_icon): main_tk_root tidak tersedia.")

def hide_desktop_icon():
    def _hide():
        print("DEBUG (hide_desktop_icon._hide): Dipanggil.")
        if config.desktop_icon_window and config.desktop_icon_window.winfo_exists():
            config.desktop_icon_window.withdraw() 
            print(f"  Ikon desktop di-withdraw. State: {config.desktop_icon_window.state()}, Terpetakan: {config.desktop_icon_window.winfo_ismapped()}")
        else:
            print("  Tidak ada jendela ikon desktop untuk disembunyikan atau sudah dihancurkan.")
            
    if config.main_tk_root:
        config.main_tk_root.after(0, _hide)
    else:
        print("KRITIS (hide_desktop_icon): main_tk_root tidak tersedia.")

def open_settings_window_tk(icon=None, item=None): 
    if config.main_tk_root:
        config.main_tk_root.after(0, _create_actual_settings_gui)
    else:
        print("Error: main_tk_root belum siap saat mencoba membuka pengaturan.")

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

def setup_pystray_icon_thread(app_root):
    import pystray
    try:
        icon_image = create_tray_icon_image()
    except Exception as e:
        print(f"Gagal membuat gambar ikon tray: {e}")
        icon_image = None

    menu = pystray.Menu(
        pystray.MenuItem(get_listening_status_text, toggle_continuous_listening, default=True,
                         checked=lambda item: config.is_continuous_mode_active),
        pystray.MenuItem("Pengaturan Suara", open_settings_window_tk), 
        pystray.MenuItem("Keluar", new_quit_action) 
    )

    config.tray_icon_object = pystray.Icon(
        "windows_assistant",
        icon_image,
        "Asisten Kanee",
        menu
    )

    print("Menjalankan ikon tray di thread terpisah...")
    
    def run_icon_detached():
        config.tray_icon_object.run()
        print("Thread pystray.Icon.run() telah berhenti.")
        if config.main_tk_root and config.main_tk_root.winfo_exists():
             print("Pystray berhenti, memberi tahu main_tk_root untuk keluar jika masih ada.")
             if not config.main_tk_root.quit_called: 
                 config.main_tk_root.after(100, config.main_tk_root.destroy)

    config.tray_icon_thread = threading.Thread(target=run_icon_detached, daemon=True, name="PystrayThread")
    config.tray_icon_thread.start()