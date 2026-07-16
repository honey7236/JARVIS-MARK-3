import speech_recognition as sr
import os
import mtranslate as mt
from dotenv import dotenv_values
import time

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")
# Get the input language setting from the environment variables.
InputLanguage = env_vars.get("InputLanguage") or "en"

# Initialize speech recognizer
recognizer = sr.Recognizer()
is_mic_muted = False

# Optimize sensitivity and noise thresholds
recognizer.energy_threshold = 1000      # Safe default threshold
recognizer.dynamic_energy_threshold = False  # Disable auto-decay to prevent small noises from triggering

# Set path for assistant status telemetry files
current_dir = os.getcwd()
TempDirPath = rf"{current_dir}/Frontend/Files"
os.makedirs(TempDirPath, exist_ok=True)

# Calibrate microphone for ambient noise floor once on startup
print("[SpeechToText] Calibrating microphone for ambient noise floor...")
try:
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
    # Enforce a minimum threshold floor to ignore small background noises/mouse clicks
    if recognizer.energy_threshold < 1500:
        recognizer.energy_threshold = 1500
    print(f"[SpeechToText] Calibration complete. Energy threshold set to: {recognizer.energy_threshold}")
except Exception as e:
    print(f"[SpeechToText] Microphone calibration skipped: {e}")

# Function to set the assistant's status by writing it to a file and updating Eel.
def SetAssistantStatus(Status):
    try:
        with open(rf'{TempDirPath}/Status.data', "w", encoding='utf-8') as file:
            file.write(Status)
    except Exception:
        pass

    try:
        import eel
        eel.updateStatus(Status)
    except Exception:
        pass

# Function to modify a query to ensure proper punctuation and formatting.
def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    if not query_words:
        return ""
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's", "can you"]
    
    # Check if the query is a question and add a question mark if necessary.
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        # Add a period if the query is not a question.
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()

# Function to translate text into English using the mtranslate library.
def UniversalTranslator(Text):
    english_translation = mt.translate(Text, 'en', "auto")
    return english_translation.capitalize()

# Function to perform speech recognition using the microphone.
def listen():
    global is_mic_muted
    while is_mic_muted:
        SetAssistantStatus("Muted")
        time.sleep(0.5)

    SetAssistantStatus("Listening...")
    
    # Map input language to standard locale strings
    recognize_language = InputLanguage
    if recognize_language == "en":
        recognize_language = "en-IN"
    elif recognize_language == "hi":
        recognize_language = "hi-IN"

    with sr.Microphone() as source:
        try:
            # Capture speech natively without timing out (blocks until input is detected)
            audio = recognizer.listen(source)
        except Exception as mic_err:
            print(f"[SpeechToText] Microphone listen error: {mic_err}")
            SetAssistantStatus("Active")
            time.sleep(1.0)  # Sleep on hardware/mic errors to prevent busy-looping
            return ""

    if is_mic_muted:
        SetAssistantStatus("Muted")
        return ""

    SetAssistantStatus("Thinking...")
    try:
        # Recognize speech using Google Web Speech API
        text = recognizer.recognize_google(audio, language=recognize_language)
        print("You:", text)
        
        if not text:
            SetAssistantStatus("Active")
            return ""
            
        # If the input language is English, return the modified query.
        if InputLanguage.lower() == "en" or "en" in InputLanguage.lower():
            return QueryModifier(text)
        else:
            # If the input language is not English, translate the text and return it.
            SetAssistantStatus("Translating...")
            try:
                return QueryModifier(UniversalTranslator(text))
            except Exception as trans_err:
                print(f"Translation network error: {trans_err}")
                return QueryModifier(text)
                
    except Exception:
        SetAssistantStatus("Active")
        time.sleep(0.2)  # Short cooldown on recognition failures
        return ""

# Main Execution Block.
if __name__ == "__main__":
    while True:
        # Continuously perform speech recognition and print the recognized text.
        Text = listen()