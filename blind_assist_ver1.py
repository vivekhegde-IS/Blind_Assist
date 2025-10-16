#!/usr/bin/env python3
"""
currency_assist_live_ov5647.py

Optimized for Raspberry Pi Zero 2 W with OV5647 Camera.
Captures image every INTERVAL seconds via rpicam-still/libcamera-still,
passes to Gemini if available, announces results with TTS,
handles BT audio out, and saves debug images.
"""

import os
import sys
import time
import json
import logging
import subprocess
from io import BytesIO
import shutil
from PIL import Image
import pyttsx3
import google.generativeai as genai

# ----- Gemini Client Setup -----
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    gemini_client = genai
    logging.info("Gemini client initialized")
except Exception:
    gemini_client = None
    logging.exception("Gemini init failed")

# ----- Configuration -----
CAPTURE_DIR = "/home/pi/captures"
TEMP_IMAGE_FILE = "/tmp/capture.jpg"
INTERVAL = 5  # seconds between captures
CAM_WIDTH = 1280
CAM_HEIGHT = 720
CAM_TIMEOUT_MS = 1400  # milliseconds
GEMINI_MODEL = "models/gemini-1.5-flash-image-preview"
BT_CARD_PREFIX = "bluez_card"
A2DP_PROFILE = "a2dp-sink"
LOGFILE = "/home/pi/currency_assist_live.log"

# ----- Logging -----
logging.basicConfig(
    filename=LOGFILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

# ----- Text-to-Speech -----
def init_tts():
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 130)
        logging.info("pyttsx3 initialized")
        return engine
    except Exception:
        logging.exception("TTS init failed")
        return None

tts_engine = init_tts()

def speak(text, block=True):
    logging.info("TTS -> %s", text)
    if not tts_engine:
        return
    try:
        tts_engine.say(text)
        if block:
            tts_engine.runAndWait()
        else:
            import threading
            threading.Thread(target=tts_engine.runAndWait, daemon=True).start()
    except Exception:
        logging.exception("TTS speak failed")

# ----- Gemini Image Analysis -----
def call_gemini_for_image(im):
    """Send an image to Gemini and get detection result."""
    if not gemini_client:
        return None

    prompt = (
        "You are an expert currency detection system optimized for low-quality images.\n"
        "Analyze the image and return exactly a JSON object:\n"
        "{\"currency\":\"<string>\",\"denomination\":<number>,\"confidence\":\"high|medium|low\"}"
    )

    try:
        b = BytesIO()
        im.save(b, format="JPEG")
        image_bytes = b.getvalue()

        model = gemini_client.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            contents=[
                {"mime_type": "image/jpeg", "data": image_bytes},
                prompt
            ]
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[len("json"):].strip()

        return json.loads(raw)

    except Exception:
        logging.exception("Gemini call failed or returned invalid JSON")
        return None

# ----- Bluetooth Audio Helpers -----
def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
    except Exception:
        return None

def find_bt_card():
    out = run_cmd(["pactl", "list", "short", "cards"]) or ""
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("bluez_card"):
            return parts[1]
    return None

def set_card_profile(card, profile, wait=0.6):
    try:
        rc = subprocess.run(
            ["pactl", "set-card-profile", card, profile],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if rc.returncode == 0:
            logging.info("Card %s -> %s", card, profile)
            time.sleep(wait)
            sinks = run_cmd(["pactl", "list", "short", "sinks"]) or ""
            for l in sinks.splitlines():
                if card in l:
                    sink = l.split()[1]
                    subprocess.run(["pactl", "set-default-sink", sink])
                    break
            return True
    except Exception:
        logging.exception("Set profile failed")
    return False

# ----- Camera Helpers -----
def get_camera_command(out, w=CAM_WIDTH, h=CAM_HEIGHT, t=CAM_TIMEOUT_MS):
    for prog in ("rpicam-still", "libcamera-still", "raspistill"):
        path = shutil.which(prog)
        if not path:
            continue
        logging.info("Using camera: %s", prog)
        if prog == "rpicam-still":
            return [path, "-o", out, "-t", str(t), "--width", str(w), "--height", str(h), "-n"]
        if prog == "libcamera-still":
            return [path, "-o", out, "--timeout", str(t), "--width", str(w), "--height", str(h), "--nopreview"]
        return [path, "-o", out, "-t", str(t), "-w", str(w), "-h", str(h)]
    return None

def capture_image():
    cmd = get_camera_command(TEMP_IMAGE_FILE)
    if not cmd:
        logging.error("No camera binary found")
        return None, "no_camera", None
    try:
        if os.path.exists(TEMP_IMAGE_FILE):
            os.remove(TEMP_IMAGE_FILE)
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=18)
        err = proc.stderr.decode(errors="ignore").strip()
        if proc.returncode != 0:
            logging.error("Camera rc=%d err=%s", proc.returncode, err)
            return None, "camera_failed", err
        if not os.path.exists(TEMP_IMAGE_FILE):
            logging.error("File missing after capture")
            return None, "file_missing", err
        return Image.open(TEMP_IMAGE_FILE), None, err
    except subprocess.TimeoutExpired:
        return None, "timeout", None
    except Exception:
        return None, "exception", None

# ----- Main Loop -----
def ensure_dir():
    os.makedirs(CAPTURE_DIR, exist_ok=True)

def main_loop():
    ensure_dir()
    bt_card = find_bt_card()
    logging.info("BT card: %s", bt_card or "none")
    speak("System ready. Starting live capture.", block=False)

    count = 0
    try:
        while True:
            count += 1
            logging.info("Capture #%d", count)
            im, err, stderr = capture_image()
            ts = int(time.time())
            fname = os.path.join(CAPTURE_DIR, f"capture_{ts}.jpg")

            if im is None:
                logging.error("Capture failed: %s", err)
                speak(f"Capture failed: {err}", block=False)
            else:
                im.save(fname)
                logging.info("Saved %s", fname)

                det = call_gemini_for_image(im)
                if isinstance(det, dict):
                    curr = det.get("currency", "unknown")
                    den = det.get("denomination", "unknown")
                    conf = det.get("confidence", "low")
                    text = f"Detected {den} {curr} with {conf} confidence."
                else:
                    text = "Detection unavailable."

                logging.info("Speak: %s", text)
                if bt_card:
                    set_card_profile(bt_card, A2DP_PROFILE)
                speak(text, block=False)

            slept = 0.0
            while slept < INTERVAL:
                time.sleep(0.25)
                slept += 0.25

    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        speak("Stopping capture. Goodbye.", block=True)
    except Exception:
        logging.exception("Main loop error")
    finally:
        if bt_card:
            set_card_profile(bt_card, A2DP_PROFILE)
        logging.info("Exiting")

# ----- Entry Point -----
if __name__ == "__main__":
    logging.info("Starting currency_assist_live_ov5647")
    main_loop()

