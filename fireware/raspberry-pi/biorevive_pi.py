# biorevive_pi.py - Improved version
import requests
import time
import json
import random

# Works in 2 modes:
# MODE 1: With ESP32 via USB (your current)
# MODE 2: Without ESP32 - Direct testing / simulation

USE_ESP32 = False  # Change to True if ESP32 connected to Pi via USB

if USE_ESP32:
    import serial
    ser = serial.Serial('/dev/ttyUSB0', 115200)

FIREBASE_URL = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/sensors.json"
AI_URL = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/ai_prediction.json"
HISTORY_URL = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/history.json"

def push_to_firebase(data):
    r = requests.put(FIREBASE_URL, json=data)
    print(f"Pushed {data} -> {r.status_code}")
    # also save history
    requests.post(HISTORY_URL, json={**data, "timestamp": time.time()})

def ai_predict(temp, ph, moisture):
    if ph < 6.0: return "Add lime, soil too acidic"
    if moisture < 30: return "Water needed urgently"
    if temp > 35: return "High temp stress"
    return "Soil Healthy - Optimal"

while True:
    try:
        if USE_ESP32:
            line = ser.readline().decode().strip()
            data = json.loads(line) if line.startswith('{') else {"ph": float(line.split(',')[0]), "temp": float(line.split(',')[1]), "moisture": float(line.split(',')[2])}
        else:
            # Simulation / direct sensors - replace with real GPIO reading later
            data = {
                "ph": round(random.uniform(6.5, 7.5), 1),
                "temp": round(random.uniform(28, 32), 1),
                "moisture": random.randint(55, 75)
            }
            print("Simulated:", data)

        push_to_firebase(data)
        pred = ai_predict(data['temp'], data['ph'], data['moisture'])
        requests.put(AI_URL, json={"prediction": pred, "timestamp": time.time()})
        print("AI:", pred)

    except Exception as e:
        print("Error:", e)
    time.sleep(10) # push every 10 sec
