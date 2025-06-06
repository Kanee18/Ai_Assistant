# Windows Voice Assistant "Kanee"

"Kanee" is a Python-based virtual assistant designed to enhance productivity on the Windows operating system. It leverages voice commands to perform a variety of tasks, including application control, information retrieval via generative AI, and media playback control.

## Key Features

* **Voice-Activated Commands**: Listens to and processes voice commands in Indonesian.
* **Text-to-Speech (TTS) Feedback**: Provides clear, spoken responses.
* **Application Control**: Opens and closes applications installed on Windows (e.g., Notepad, Chrome, Calculator).
* **Spotify Integration**:
    * Finds and plays songs on Spotify using voice commands.
    * Intelligently handles both **Premium** and **Free** accounts. For Free users, it opens the song directly in the desktop app.
    * Can switch songs by restarting the Spotify client with the new track.
* **Generative AI Chat**: Integrates with the Google Gemini API to answer complex questions and hold conversations.
* **System Interaction**: Can identify and report the title of the currently active window.
* **Configurable Settings**: A graphical user interface (GUI) to easily select the TTS voice and input microphone.
* **System Tray Operation**: Runs conveniently in the system tray, providing easy access to start/stop the assistant, open settings, or exit the application.
* **Visual Desktop Icon**: An optional on-screen icon provides visual feedback when the assistant is active.

## Technologies Used

* **Python 3**: The core programming language.
* **SpeechRecognition**: For converting user speech to text.
* **pyttsx3**: For text-to-speech synthesis.
* **Pygame**: Used for audio playback to prevent blocking.
* **Tkinter**: For the settings and desktop icon GUI.
* **pystray** & **Pillow (PIL)**: For system tray icon creation and management.
* **spotipy**: A Python client for the Spotify Web API.
* **google-generativeai**: The official Python SDK for the Google Gemini API.
* **pygetwindow**: For window management and interaction.
* **python-dotenv**: For securely managing environment variables and API keys.
* Standard libraries: `os`, `re`, `subprocess`, `json`, `threading`, `time`.

## Installation Guide

Follow these steps to set up and run the assistant on your local machine.

#### 1. Clone the Repository

First, clone this repository to your local machine.
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
cd YOUR_REPOSITORY_NAME
2. Create and Activate a Virtual Environment
It is highly recommended to use a virtual environment to manage project dependencies.

Bash

# Create the virtual environment
python -m venv venv

# Activate it on Windows
.\venv\Scripts\activate
3. Install Dependencies
Install all the required Python libraries using the requirements.txt file.

Bash

pip install -r requirements.txt
A minimal requirements.txt file for this project would look like this:

SpeechRecognition
pyttsx3
pygame
pystray
Pillow
spotipy
google-generativeai
pygetwindow
python-dotenv
4. API Key and Configuration Setup
This project requires API keys to function. We use a .env file to handle them securely.

In the project directory, find the example file named .env.example.

Create a copy of this file and rename it to .env.

Open and edit the .env file with your personal keys:

# .env file

# Get your Gemini API Key from Google AI Studio
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"

# Get your Spotify credentials from the Spotify Developer Dashboard
SPOTIPY_CLIENT_ID="YOUR_SPOTIFY_CLIENT_ID_HERE"
SPOTIPY_CLIENT_SECRET="YOUR_SPOTIFY_CLIENT_SECRET_HERE"
The .gitignore file is already configured to ignore the .env file, so your keys will not be uploaded to GitHub.

How to Run
Once the setup is complete, you can run the assistant.

Make sure you are in the project's root directory.
Ensure your virtual environment is activated.
Run the main script:
Bash

python main.py
The assistant's icon will appear in your Windows system tray. Right-click the icon for options.
Usage Examples
After activating the conversation mode from the system tray menu, you can use commands like:

General Commands:
"Buka Notepad"
"Tutup Kalkulator"
"Jam berapa sekarang?"
Spotify Commands:
"Putar lagu Lampu Merah di Spotify"
"Mainkan lagu Hati-Hati di Jalan di Spotify"
AI Interaction:
"Jelaskan tentang relativitas umum"
"Beri aku ide untuk makan malam"
Contributing
Contributions are welcome! If you have ideas for new features or improvements, please feel free to fork the repository and submit a pull request. You can also open an issue to report bugs or suggest enhancements.

License
This project is licensed under the MIT License. See the LICENSE file for more details.