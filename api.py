import google.generativeai as genai
import config

GEMINI_MODEL_INITIALIZED = False
gemini_chat_session = None

def initialize_gemini():
    global gemini_chat_session, GEMINI_MODEL_INITIALIZED
    
    api_key = config.GEMINI_API_KEY
    if not api_key or "MASUKKAN_API_KEY" in api_key:
        print("KRITIS (api.py): API Key Gemini belum diatur di config.py.")
        GEMINI_MODEL_INITIALIZED = False
        return

    try:
        print("INFO (api.py): Mengkonfigurasi Gemini API...")
        genai.configure(api_key=api_key)
        
        print("INFO (api.py): Membuat model GenerativeModel Gemini...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        initial_history = [
            {'role':'user', 'parts': ["Kamu adalah \"Kanee\", asisten cerdas untuk Windows."]},
            {'role':'model', 'parts': ["Tentu, saya Kanee. Siap membantu."]}
        ]
        gemini_chat_session = model.start_chat(history=initial_history)
        GEMINI_MODEL_INITIALIZED = True
        print("INFO (api.py): Model Gemini dan sesi chat berhasil diinisialisasi.")
    except Exception as e:
        print(f"KRITIS (api.py): Kesalahan saat inisialisasi Gemini: {e}")
        gemini_chat_session = None
        GEMINI_MODEL_INITIALIZED = False

def send_to_gemini(user_prompt):
    global gemini_chat_session
    
    if not GEMINI_MODEL_INITIALIZED or not gemini_chat_session:
        return "Maaf, koneksi ke AI belum siap."
    if not user_prompt:
        return "Tidak ada pertanyaan untuk AI."
    
    try:
        print(f"INFO (api.py): Mengirim ke Gemini: {user_prompt}")
        response = gemini_chat_session.send_message(user_prompt)
        
        if response.parts:
            return response.text
        elif response.prompt_feedback and response.prompt_feedback.block_reason:
            reason = getattr(response.prompt_feedback, 'block_reason_message', str(response.prompt_feedback.block_reason))
            print(f"PERINGATAN (api.py): Permintaan ke Gemini diblokir: {reason}")
            return f"Permintaan Anda ke AI diblokir karena: {reason}."
        else:
            print("PERINGATAN (api.py): Respons Gemini kosong atau tidak valid.")
            return "Hmm, AI tidak memberikan jawaban yang valid."
    except Exception as e:
        print(f"ERROR (api.py): Terjadi kesalahan saat berkomunikasi dengan Gemini: {e}")
        return "Maaf, terjadi masalah saat berkomunikasi dengan AI."