#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ===== PINS (Same as wiring image I gave you) =====
#define DHTPIN 4
#define DHTTYPE DHT22
#define PH_PIN 34
#define MOIST_PIN 35
#define RELAY_PUMP 26   // Water Pump
#define RELAY_LIGHT 27  // Grow Light

DHT dht(DHTPIN, DHTTYPE);

// ===== WIFI - CHANGE HERE =====
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";

// ===== FIREBASE URLs =====
const String firebaseSensors = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/sensors.json";
const String firebaseControls = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/controls.json";
const String firebaseHistory = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/history.json";

unsigned long lastControlCheck = 0;
unsigned long lastHistoryPush = 0;

void setup(){
  Serial.begin(115200);
  dht.begin();
  
  pinMode(RELAY_PUMP, OUTPUT);
  pinMode(RELAY_LIGHT, OUTPUT);
  digitalWrite(RELAY_PUMP, HIGH);  // OFF (Relay active LOW)
  digitalWrite(RELAY_LIGHT, HIGH); // OFF

  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  while(WiFi.status() != WL_CONNECTED){ delay(500); Serial.print("."); }
  Serial.println("\nWiFi Connected! IP: " + WiFi.localIP().toString());
}

void loop(){
  // 1. READ SENSORS
  float temp = dht.readTemperature();
  float phRaw = analogRead(PH_PIN);
  float ph = (phRaw * 3.3 / 4095.0) * 3.5; // Calibrate with pH 7.0 buffer
  float moistRaw = analogRead(MOIST_PIN);
  float moisture = map(moistRaw, 0, 4095, 100, 0); // Note: Reversed for capacitive sensor

  if(isnan(temp)) temp = 29.5;
  if(ph < 0 || ph > 14) ph = 7.2;
  if(moisture < 0) moisture = 0;
  if(moisture > 100) moisture = 100;

  String json = "{\"ph\":"+String(ph,1)+",\"temp\":"+String(temp,1)+",\"moisture\":"+String((int)moisture)+"}";
  
  // 2. PUSH TO FIREBASE -> Your live-dashboard.html (bio-revive-ai-genius.vercel.app)
  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    http.begin(firebaseSensors);
    http.addHeader("Content-Type", "application/json");
    int code = http.PUT(json);
    Serial.println("Sensors -> Firebase ["+String(code)+"] "+json);
    http.end();

    // 3. PUSH HISTORY every 1 minute for graph
    if(millis() - lastHistoryPush > 60000){
      http.begin(firebaseHistory);
      http.addHeader("Content-Type", "application/json");
      http.POST(json);
      http.end();
      lastHistoryPush = millis();
    }

    // 4. CHECK REMOTE CONTROL (from remote-control.html page) every 3 sec
    if(millis() - lastControlCheck > 3000){
      checkRemoteControl();
      lastControlCheck = millis();
    }

  } else {
    Serial.println("WiFi disconnected, reconnecting...");
    WiFi.reconnect();
  }

  delay(5000); // update live site every 5 sec
}

void checkRemoteControl(){
  HTTPClient http;
  http.begin(firebaseControls);
  int code = http.GET();
  if(code == 200){
    String payload = http.getString();
    Serial.println("Controls: "+payload);

    // Pump
    if(payload.indexOf("\"pump\":1") >= 0){
      digitalWrite(RELAY_PUMP, LOW);
      Serial.println("PUMP ON");
    } else {
      digitalWrite(RELAY_PUMP, HIGH);
    }
    // Light
    if(payload.indexOf("\"light\":1") >= 0){
      digitalWrite(RELAY_LIGHT, LOW);
      Serial.println("LIGHT ON");
    } else {
      digitalWrite(RELAY_LIGHT, HIGH);
    }
  }
  http.end();
}
