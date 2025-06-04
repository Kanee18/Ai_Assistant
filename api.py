import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyA2KXCsk6Z92gCu8GLeoPrXHvCyT9pP9iw" 

gemini_chat_session = None
GEMINI_MODEL_INITIALIZED = False

"""Menginisialisasi model dan sesi chat Gemini."""
def initialize_gemini():
    global gemini_chat_session, GEMINI_MODEL_INITIALIZED, GEMINI_API_KEY
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "MASUKKAN_API_KEY_GEMINI_ANDA_YANG_VALID":
        print("KRITIS (api.py): API Key Gemini belum diatur dengan benar.")
        GEMINI_MODEL_INITIALIZED = False
        return

    try:
        print("INFO (api.py): Mengkonfigurasi Gemini API...")
        genai.configure(api_key=GEMINI_API_KEY)
        
        print("INFO (api.py): Membuat model GenerativeModel Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest') 
        
        initial_history = [
            {'role':'user', 'parts': ["Kamu adalah \"Asisten Cerdas Kanee\"."]},
            {'role':'model', 'parts': ["Baik, saya Kanee, asisten cerdas Anda."]}
        ]
        gemini_chat_session = model.start_chat(history=initial_history)
        GEMINI_MODEL_INITIALIZED = True
        print("INFO (api.py): Model Gemini dan sesi chat berhasil diinisialisasi.")
    except Exception as e:
        print(f"KRITIS (api.py): Kesalahan saat inisialisasi Gemini: {e}")
        gemini_chat_session = None
        GEMINI_MODEL_INITIALIZED = False

"""Mengirim prompt ke Gemini dan mengembalikan respons teks."""
def send_to_gemini(user_prompt):
    global gemini_chat_session, GEMINI_MODEL_INITIALIZED
    
    if not GEMINI_MODEL_INITIALIZED or not gemini_chat_session:
        print("PERINGATAN (api.py): Gemini belum siap untuk send_to_gemini.")
        return "Maaf, koneksi ke AI belum siap."
    if not user_prompt:
        return "Tidak ada pertanyaan untuk AI."
    
    try:
        print(f"INFO (api.py): Mengirim ke Gemini: {user_prompt}")
        response = gemini_chat_session.send_message(user_prompt)
        
        if response.parts:
            return response.text
        elif response.prompt_feedback and response.prompt_feedback.block_reason:
            block_reason_msg = getattr(response.prompt_feedback, 'block_reason_message', str(response.prompt_feedback.block_reason))
            print(f"PERINGATAN (api.py): Permintaan ke Gemini diblokir: {block_reason_msg}")
            return f"Permintaan Anda ke AI diblokir: {block_reason_msg}."
        else:
            print("PERINGATAN (api.py): Respons Gemini kosong atau tidak valid.")
            return "Hmm, AI tidak memberikan jawaban yang valid atau responsnya kosong."

    except Exception as e:
        print(f"ERROR (api.py): Terjadi kesalahan saat berkomunikasi dengan Gemini: {e}")
        return "Maaf, terjadi masalah saat berkomunikasi dengan AI."
