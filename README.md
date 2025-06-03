# Windows Assistant "Kanee" (Customizable Name)

Windows Assistant "Kanee" is a virtual assistant project developed in Python. This assistant is designed to help users perform various tasks through voice and text commands, such as opening applications, searching for information, and interacting with a generative AI.

## Key Features (Examples, customize to your actual features)

* **Voice Recognition**: Listens to and understands user voice commands (currently demonstrated with Indonesian language commands).
* **Text-to-Speech (TTS)**: Provides voice responses to the user.
* **Application Control**: Opens applications installed on Windows (e.g., Notepad, Calculator, Chrome).
* **Information Retrieval**: Uses generative AI (Google Gemini) to answer questions and find information.
* **Continuous Interaction**: A conversation mode where the user can issue multiple commands without reactivating the listening mode each time.
* **Settings GUI**: A graphical user interface to configure TTS voice preferences and input microphone.
* **Interactive Desktop Icon**: Displays an icon on the desktop that provides visual feedback (e.g., when the assistant is listening or speaking -- *animation feature is under development*).
* **System Tray Integration**: Runs in the background and can be accessed via an icon in the Windows system tray.

## Technologies Used

* **Python 3**: Main programming language.
* **pystray**: For creating the system tray icon and menu.
* **SpeechRecognition**: For converting audio to text.
* **pyttsx3**: For converting text to speech (TTS).
* **Pygame**: Used for playing TTS audio.
* **Tkinter**: For creating the graphical user interface (GUI) for the settings window and desktop icon.
* **Pillow (PIL Fork)**: For image manipulation (tray icon, desktop icon images).
* **Google Generative AI (Gemini API)**: For generative AI capabilities and advanced natural language processing.
* **spaCy**: For rule-based natural language understanding (NLU) (optional, depending on your final implementation).
* **pygetwindow**: For getting the title of the active window.
* And other standard Python libraries like `os`, `json`, `threading`, `subprocess`, `time`, `re`.

## Installation

1.  **Clone the Repository (Once on GitHub):**
    ```bash
    git clone [YOUR_REPOSITORY_URL]
    cd [YOUR_REPOSITORY_FOLDER_NAME]
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # For Windows
    .\venv\Scripts\activate
    # For macOS/Linux
    # source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file containing all necessary libraries. You can generate it from your active environment with:
    ```bash
    pip freeze > requirements.txt
    ```
    Then, users can install them using:
    ```bash
    pip install -r requirements.txt
    ```
    A likely list of libraries for your `requirements.txt`:
    ```
    pystray
    Pillow
    SpeechRecognition
    pyttsx3
    pygame
    google-generativeai
    # spacy (if you are actively using it)
    # en_core_web_sm (model for spaCy, install via: python -m spacy download en_core_web_sm)
    pygetwindow
    # requests (if you use it for other features, e.g., weather)
    ```

4.  **Configure API Keys:**
    * Open the `windows_assistant.py` file (or a separate configuration file if you have one).
    * Enter your Google Gemini API Key in the `GEMINI_API_KEY` variable:
        ```python
        GEMINI_API_KEY = "YOUR_VALID_GEMINI_API_KEY_HERE"
        ```
    * (Optional) If you implement a weather feature with OpenWeatherMap, also enter your API Key in `OWM_API_KEY`.
    * **Important**: Do not commit your actual API keys to a public GitHub repository. Add the file containing keys to your `.gitignore` or instruct users to add them manually.

5.  **Prepare Desktop Icon Images (If Feature is Active):**
    * Ensure the image file for the idle icon (e.g., `siri_style_icon.png` or `orb_idle.png`) and the speaking animation frames (e.g., `orb_speak_0.png`, `orb_speak_1.png`, etc.) are in the same directory as the `windows_assistant.py` script.
    * Adjust the filenames and lists in the global variables `DESKTOP_ICON_IDLE_PATH` and `DESKTOP_ICON_ANIM_FILENAMES` within the script accordingly.

## How to Run

After all dependencies are installed and configurations are set:

1.  Ensure you are in the project's root directory and your virtual environment (if used) is activated.
2.  Run the Python script:
    ```bash
    python windows_assistant.py
    ```
3.  The assistant's icon will appear in your Windows system tray. Click the icon to see available options like "Start Conversation," "Sound Settings," and "Exit."

## Usage

* **Start Conversation**: Activates the mode where the assistant continuously listens for your voice commands.
* **Stop Conversation**: Deactivates the continuous listening mode.
* **Sound Settings**: Opens a window to select the desired TTS voice and input microphone device.
* **Voice Commands (Examples):**
    * "Kanee, open Notepad."
    * "Kanee, what time is it?"
    * "Kanee, search for information about [topic]."
    * "Kanee, what's your name?"
    * (Adjust "Kanee" to your wake word if you implement one, or use commands directly after activating conversation mode).

## Future Development Plans (Examples)

* Implement MP4 animation playback for the desktop icon.
* Add To-Do List management features.
* Integrate a weather information service.
* Ability to set reminders.
* Support for a wake word (e.g., "Hey Kanee") to initiate interaction without clicks.

## Contributing

If you'd like to contribute to this project, please fork the repository and create a pull request. Suggestions and feedback are also highly welcome via the "Issues" section on GitHub.

## License

(Choose a license if you wish, e.g., MIT, Apache 2.0, or leave blank if it's a personal project.)
Example: This project is licensed under the MIT License - see the `LICENSE.md` file for details.
