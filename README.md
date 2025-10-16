# Blind_Assist
A real-time Indian currency detection and announcement system for the visually impaired, using a Raspberry Pi Zero 2W, camera, and the Gemini API.
This project is a real-time currency detection system designed to assist visually impaired individuals. It runs on a Raspberry Pi Zero 2 W, uses an OV5647 camera to capture images of banknotes, and leverages the Google Gemini Vision API to identify the currency and its denomination. The result is then announced aloud using a text-to-speech engine, with output directed to a connected Bluetooth speaker.



## ✨ Features

- *Live Capture:* Continuously captures images for real-time analysis.
- *AI-Powered Detection:* Uses the powerful Gemini 1.5 Flash model for fast and accurate currency identification from images.
- *Voice Feedback:* Announces the detected currency and denomination clearly using text-to-speech.
- *Bluetooth Audio:* Automatically routes audio output to a connected Bluetooth device.
- *Optimized for Pi Zero 2W:* Designed to be lightweight and efficient for embedded systems.

## Hardware Requirements

- Raspberry Pi Zero 2 W
- OV5647 Camera Module (or compatible Pi camera)
- A reliable 5V power supply
- MicroSD Card (16GB or larger recommended)
- A Bluetooth speaker or headphones

## ⚙ Setup and Installation

1.  *Flash Raspberry Pi OS:* Start with a fresh installation of Raspberry Pi OS Lite (64-bit recommended).

2.  *Clone the Repository:*
    bash
    git clone <your-repository-url>
    cd <your-repository-name>
    

3.  *Run the Setup Script:* The provided script will install all system and Python dependencies.
    bash
    chmod +x setup.sh
    ./setup.sh
    

4.  *Set Up Google Gemini API Key:*
    - Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    - Set it as an environment variable to keep it secure. Add the following line to the end of your ~/.bashrc file:
      bash
      export GOOGLE_API_KEY="YOUR_API_KEY_HERE"
      
    - Replace YOUR_API_KEY_HERE with your actual key.
    - Reload the shell for the change to take effect: source ~/.bashrc

5.  *Configure Bluetooth:*
    - Pair and connect your Bluetooth speaker or headphones using the bluetoothctl command-line tool. Make sure it is trusted and connected before running the script.

## ▶ How to Run

Execute the main script using Python:

```bash
python3 blind_assist_ver1.py
