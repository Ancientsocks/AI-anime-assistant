import os
import threading
import webbrowser
import pyautogui
import pyttsx3
import speech_recognition as sr
import datetime
import pywhatkit as wk
import wikipedia
import json
import websocket
import time

VTUBE_STUDIO_API_URL = "ws://localhost:8001"
AUTH_TOKEN_FILE = "vtube_auth_token.txt"
AUTH_TOKEN = None
ws_ready = False
listening_mode = False
hotkey_map = {}
engine = pyttsx3.init("sapi5")
voices = engine.getProperty("voices")
female_voice_index = 1
engine.setProperty("voice", voices[female_voice_index].id)
engine.setProperty("rate", 150)

def save_auth_token(token):
    with open(AUTH_TOKEN_FILE, "w") as file:
        file.write(token)

def load_auth_token():
    if os.path.exists(AUTH_TOKEN_FILE):
        with open(AUTH_TOKEN_FILE, "r") as file:
            return file.read().strip()

def send_message_to_vtube_studio(ws, hotkey_id):
    if not AUTH_TOKEN:
        print("Authentication is required to send messages to VTube Studio.")
        return
    payload = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "messageType": "HotkeyTriggerRequest",
        "requestID": f"trigger_{hotkey_id}",
        "authenticationToken": AUTH_TOKEN,
        "data": {
            "hotkeyID": hotkey_id,
        },
    }
    print(f"Triggering hotkey: {hotkey_id}")
    ws.send(json.dumps(payload))

def get_hotkeys(ws):
    if AUTH_TOKEN is None:
        print("Authentication required. Please authenticate first.")
        return
    payload = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "messageType": "HotkeysInCurrentModelRequest",
        "requestID": "get_hotkeys",
        "authenticationToken": AUTH_TOKEN,
    }
    print("Requesting hotkeys for the current model...")
    ws.send(json.dumps(payload))

def speak(audio):
    global listening_mode
    print(f"Speaking: {audio}")
    if listening_mode:
        print("Currently listening, skipping speak action.")
        return
    engine.say(audio)
    engine.runAndWait()

def authenticate(ws):
    global AUTH_TOKEN
    AUTH_TOKEN = load_auth_token()
    if AUTH_TOKEN:
        print(f"Using saved authentication token: {AUTH_TOKEN}")
        auth_request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "messageType": "AuthenticationRequest",
            "requestID": "complete_auth",
            "data": {
                "pluginName": "Saara Integration",
                "pluginDeveloper": "Abdul Rahman",
                "authenticationToken": AUTH_TOKEN,
            },
        }
        ws.send(json.dumps(auth_request))
    else:
        print("Requesting new authentication token.")
        auth_request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "messageType": "AuthenticationTokenRequest",
            "requestID": "saara_auth",
            "data": {
                "pluginName": "Saara Integration",
                "pluginDeveloper": "Abdul Rahman",
            },
        }
        ws.send(json.dumps(auth_request))

def trigger_expression(ws, hotkey_id):
    if not hotkey_id:
        print("No valid hotkey ID provided.")
        return
    payload = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "messageType": "HotkeyTriggerRequest",
        "requestID": f"trigger_{hotkey_id}",
        "authenticationToken": AUTH_TOKEN,
        "data": {
            "hotkeyID": hotkey_id,
        },
    }
    print(f"Triggering hotkey: {hotkey_id}")
    ws.send(json.dumps(payload))

def on_message(ws, message):
    global hotkey_map, AUTH_TOKEN, ws_ready
    response = json.loads(message)
    print(f"Received WebSocket message: {response}")
    if response.get("messageType") == "HotkeysInCurrentModelResponse":
        hotkeys = response["data"].get("availableHotkeys", [])
        if hotkeys:
            hotkey_map = {hk["name"].lower(): hk["hotkeyID"] for hk in hotkeys}
            print("Available Hotkeys:")
            for hk in hotkeys:
                print(f"Name: {hk['name']}, ID: {hk['hotkeyID']}")
        else:
            print("No hotkeys found for the current model.")
    elif "authenticationToken" in response.get("data", {}):
        AUTH_TOKEN = response["data"]["authenticationToken"]
        save_auth_token(AUTH_TOKEN)
        print("Authentication token received and saved.")
        authenticate(ws)
    elif response.get("messageType") == "AuthenticationResponse":
        if response["data"].get("authenticated"):
            print("Successfully authenticated with VTube Studio!")
            ws_ready = True
        else:
            print("Authentication failed. Please check your setup.")
    elif response.get("messageType") == "APIError":
        error_id = response["data"].get("errorID")
        error_message = response["data"].get("message", "Unknown error")
        print(f"API Error {error_id}: {error_message}")

def on_open(ws):
    print("WebSocket connected...")
    authenticate(ws)

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed. Reconnecting...")

def wishMe():
    global ws_ready
    while not ws_ready:
        print("Waiting for WebSocket to be ready...")
        time.sleep(0.5)
    hour = int(datetime.datetime.now().hour)
    if hour >= 0 and hour < 12:
        speak("Good Morning,sir")
    elif hour >= 12 and hour < 18:
        speak("Good Afternoon,sir")
    else:
        speak("Good Evening,sir")
    speak("I am your saara. Please tell me how may I help you")

def listen_for_commands(ws):
    global listening_mode
    while True:
        listening_mode = True
        query = takeCommand()
        listening_mode = False
        if query and query != "None":
            process_command(query, ws)

def takeCommand():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")
            audio = r.listen(source, timeout=5)
        print("Recognizing...")
        query = r.recognize_google(audio, language="en-in")
        print(f"User said: {query}")
        return query
    except sr.UnknownValueError:
        print("Speech Recognition could not understand audio.")
    except sr.RequestError as e:
        print(f"Speech Recognition service error: {e}")
    except Exception as e:
        print(f"An error occurred during recognition: {e}")
    return "None"

def process_command(query, ws=None):
    query = query.lower()
    print(f"Processing command: {query}")
    if "hello sara" in query:
        speak("Yes, sir. How can I help you?")
    elif "how are you" in query:
        speak("I am fine . what about you")
    elif "smile" in query:
        trigger_expression(ws, "90d8df9dde3f4a3c96053ec8f39ee58f")
        speak("smile")
    elif "wink" in query:
        trigger_expression(ws, "15258419e127472db911d2676f7d4f31")
        speak("wink")
    elif "trigger animation 3" in query:
        trigger_expression(ws, "4a15ee5d9afa47138eb68cb34e0bc9da")
        speak("Animation 3 triggered.")
    elif "who are you" in query:
        speak("I am Saara, your personal assistant.")
    elif "who created you" in query:
        speak("I am created by Abdul rahman.")
    elif "what is" in query:
        speak("Searching Wikipedia...")
        query = query.replace("what is", "")
        result = wikipedia.summary(query, sentences=1)
        speak("According to Wikipedia")
        print(result)
        speak(result)
    elif "wikipedia" in query:
        speak("Searching from Wikipedia...")
        result = wikipedia.summary(query, sentences=1)
        speak("According to Wikipedia")
        print(result)
        speak(result)
        send_message_to_vtube_studio(ws, result)
    elif "sara open google" in query:
        speak("Opening Google")
        speak("what should i search")
        qrry = takeCommand().lower()
        webbrowser.open(f"{qrry}")
        result = wikipedia.summary(qrry,sentences=1)
        speak(result)
    elif "sara open youtube" in query:
        speak("What would you like to watch?")
        qrry = takeCommand().lower()
        wk.playonyt(f"{qrry}")
    elif "search on youtube" in query:
        query=query.replace("search on youtube","")
        webbrowser.open(f"www.youtube.com/results?search_query={query}")
    elif "close browser" in query:
        os.system("taskkill /f /im msedge.exe")
        speak("browser has been closed.")
    elif "close chrome " in query:
        os.system("taskkill /f /im chrome.exe")
        speak("chrome has been closed.")
    elif "open paint" in query:
        npath = "C:\\Users\\sam\\OneDrive\\Desktop\\Paint.lnk"
        os.startfile(npath)
    elif "close paint" in query:
        os.system("taskkill /f /im mspaint.exe")
        speak("Paint has been closed.")
    elif "sara type something" in query:
        query = query.replace("sara type something", "").strip()
        pyautogui.typewrite(query, interval=0.1)
    elif "sara open notepad" in query:
        npath ="C:\\Windows\\notepad.exe"
        os.startfile(npath)
    elif "close notepad" in query:
        os.system("taskkill/f /im notepad.exe")
        speak("notepad has been closed.")
    elif "play wild robot" in query:
        npath = "C:\\Users\sam\Videos\\the.wild.robot.mkv"
        os.startfile(npath)
    elif "close the video" in query:
        os.system("taskkill /f /im AnyDVD.exe")
    elif "sara what is the time" in query:
        strtime = datetime.datetime.now().strftime("%H:%M:%S")
        speak(f"sir, the time is {strtime}")
    else:
        speak("Command not recognized. Please try again.")
        send_message_to_vtube_studio(ws, "Command not recognized. Please try again.")

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        VTUBE_STUDIO_API_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    wishMe()
    time.sleep(2)
    get_hotkeys(ws)
    listen_for_commands(ws)
