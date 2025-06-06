# Windows Voice Assistant "Kanee"

"Kanee" is a Python-based virtual assistant designed to enhance productivity on the Windows operating system. It leverages voice commands to perform various tasks, such as opening applications, searching for information, interacting with a generative AI, and controlling media playback.

## Key Features

* **Voice Recognition**: Listens to and understands user voice commands in Indonesian.
* **Text-to-Speech (TTS)**: Provides clear voice responses to the user.
* **Application Control**: Opens and closes applications installed on Windows (e.g., Notepad, Calculator, Chrome).
* **Spotify Integration**: Finds and plays songs on Spotify using voice commands. It intelligently handles both **Premium** and **Free** accounts; for Free users, it opens the song directly in the desktop app, even restarting it if necessary to change tracks.
* **Information Retrieval**: Uses generative AI (Google Gemini) to answer questions and find information.
* **Continuous Interaction**: A conversation mode where the user can issue multiple commands without reactivating the listening mode each time.
* **Settings GUI**: A graphical user interface to configure TTS voice preferences and input microphone.
* **System Tray Integration**: Runs in the background and can be accessed via an icon in the Windows system tray for easy control.
* **Interactive Desktop Icon**: Displays an icon on the desktop that provides visual feedback when the assistant is active.

## Technologies Used

* **Python 3**: Main programming language.
* **pystray** & **Pillow**: For creating the system tray icon and menu.
* **SpeechRecognition**: For converting audio to text.
* **pyttsx3**: For converting text to speech (TTS).
* **Pygame**: Used for playing TTS audio without blocking the main thread.
* **Tkinter**: For creating the graphical user interface (GUI).
* **spotipy**: A Python client for the Spotify Web API.
* **google-generativeai**: The official Python SDK for the Google Gemini API.
* **pygetwindow**: For window management and interaction.
* **python-dotenv**: For securely managing environment variables and API keys.
* Standard Python libraries like `os`, `json`, `threading`, `subprocess`, `time`, and `re`.

## Installation

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
    cd YOUR_REPOSITORY_NAME
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # For Windows
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Install all required libraries using the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```
    *A minimal `requirements.txt` for this project:*
    ```
    pystray
    Pillow
    SpeechRecognition
    pyttsx3
    pygame
    google-generativeai
    spotipy
    pygetwindow
    python-dotenv
    ```

4.  **Configure API Keys:**
    This project uses a `.env` file for secure API key management.
    * Create a copy of the `.env.example` file and rename it to `.env`.
    * Open the `.env` file and enter your personal API keys.
        ```
        # .env file
        GEMINI_API_KEY="YOUR_VALID_GEMINI_API_KEY_HERE"
        SPOTIPY_CLIENT_ID="YOUR_SPOTIFY_CLIENT_ID_HERE"
        SPOTIPY_CLIENT_SECRET="YOUR_SPOTIFY_CLIENT_SECRET_HERE"
        ```
    * **Important**: The `.gitignore` file ensures that your `.env` file with your secret keys will **not** be uploaded to GitHub.

## How to Run

After all dependencies are installed and configurations are set:

1.  Ensure you are in the project's root directory and your virtual environment is activated.
2.  Run the main Python script:
    ```bash
    python main.py
    ```
3.  The assistant's icon will appear in your Windows system tray. Right-click the icon to see available options like "Start Conversation," "Sound Settings," and "Exit."

## Usage

* **Start/Stop Conversation**: Use the system tray menu to activate or deactivate the continuous listening mode.
* **Voice Commands (Examples):**
    * `"Buka Notepad"`
    * `"Jam berapa sekarang?"`
    * `"Putar lagu Hati-Hati di Jalan di Spotify"`
    * `"Jelaskan tentang sejarah Buleleng"`

## Future Development Plans

* Implement a wake word (e.g., "Hey Kanee") to initiate interaction without clicks.
* Add To-Do List and reminder management features.
* Integrate a weather information service.
* Enhance the desktop icon with speaking animations.

## Contributing

If you'd like to contribute to this project, please fork the repository and create a pull request. Suggestions and feedback are also highly welcome via the "Issues" section on GitHub.

## License

This project is licensed under the MIT License - see the `LICENSE.md` file for details.