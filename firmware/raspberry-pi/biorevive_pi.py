import time
import json
import serial
import requests
import RPi.GPIO as GPIO

# ===== PINS (BCM) - Same as Pi Wiring Image =====
RELAY_PUMP_PIN = 17   # Pin 11 - Water Pump
RELAY_LIGHT_PIN = 27  # Pin 13 - Grow Light

# ===== SETUP GPIO =====
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PUMP_PIN, GPIO.OUT)
GPIO.setup(RELAY_LIGHT_PIN, GPIO.OUT)
GPIO.output(RELAY_PUMP_PIN, GPIO.HIGH)  # OFF - Active LOW relay
GPIO.output(RELAY_LIGHT_PIN, GPIO.HIGH)

# ===== FIREBASE =====
FIREBASE_SENSORS = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/sensors.json"
FIREBASE_CONTROLS = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/controls.json"
FIREBASE_HISTORY = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/history.json"

# ===== ESP32 SERIAL (USB) =====
# Find port: ls /dev/ttyUSB* or /dev/ttyACM*
SERIAL_PORT = "/dev/ttyUSB0"
BAUD = 115200

def check_remote_control():
    try:
        r = requests.get(FIREBASE_CONTROLS, timeout=5)
        data = r.json()
        if not data:
            return
        pump = data.get('pump', 0)
        light = data.get('light', 0)

        # Relay is Active LOW
        GPIO.output(RELAY_PUMP_PIN, GPIO.LOW if pump == 1 else GPIO.HIGH)
        GPIO.output(RELAY_LIGHT_PIN, GPIO.LOW if light == 1 else GPIO.HIGH)
        
        print(f"Controls -> Pump: {'ON' if pump else 'OFF'}, Light: {'ON' if light else 'OFF'}")
    except Exception as e:
        print(f"Control check error: {e}")

def push_to_firebase(ph, temp, moisture):
    payload = {"ph": round(ph,1), "temp": round(temp,1), "moisture": int(moisture)}
    try:
        # Live data (overwrites) -> your live-dashboard.html
        r = requests.put(FIREBASE_SENSORS, json=payload, timeout=5)
        print(f"Pushed LIVE {payload} -> {r.status_code}")
        
        # History for graph (every 60 sec handled in loop)
        return payload
    except Exception as e:
        print(f"Firebase push error: {e}")
        return None

def main():
    print("BIO Revive 360 - Pi Controller Started")
    print(f"Remote: bio-revive-ai-genius.vercel.app/remote-control.html")
    
    last_history = 0
    last_control = 0
    
    # Try to open ESP32 serial
    ser = None
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=2)
        print(f"Connected to ESP32 on {SERIAL_PORT}")
        time.sleep(2)
    except:
        print(f"ESP32 not found on {SERIAL_PORT}, using dummy values (for testing without ESP32)")
    
    # Fallback values (like your screenshot: 7.2, 29.5, 65)
    ph, temp, moisture = 7.2, 29.5, 65
    
    while True:
        # 1. Read from ESP32 if available
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode().strip()
                # Expected from ESP32: {"ph":7.2,"temp":29.5,"moisture":65}
                if line.startswith('{'):
                    data = json.loads(line)
                    ph = data.get('ph', ph)
                    temp = data.get('temp', temp)
                    moisture = data.get('moisture', moisture)
            except:
                pass
        
        # 2. Push live every 5 sec
        push_to_firebase(ph, temp, moisture)
        
        # 3. Check remote control every 3 sec
        if time.time() - last_control > 3:
            check_remote_control()
            last_control = time.time()
        
        # 4. Push history every 60 sec for graph
        if time.time() - last_history > 60:
            try:
                requests.post(FIREBASE_HISTORY, json={"ph":ph,"temp":temp,"moisture":moisture}, timeout=5)
            except:
                pass
            last_history = time.time()
            
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        GPIO.cleanup()
