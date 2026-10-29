#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT22
#define PH_PIN 34
#define MOIST_PIN 35

DHT dht(DHTPIN, DHTTYPE);
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const String firebaseURL = "https://biorevive-360-default-rtdb.asia-southeast1.firebasedatabase.app/biorevive360/sensors.json";

void setup(){
  Serial.begin(115200);
  dht.begin();
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  while(WiFi.status() != WL_CONNECTED){ delay(500); Serial.print("."); }
  Serial.println("Connected!");
}

void loop(){
  float temp = dht.readTemperature();
  float phRaw = analogRead(PH_PIN);
  float ph = (phRaw * 3.3 / 4095.0) * 3.5; // calibrate with buffer
  float moistRaw = analogRead(MOIST_PIN);
  float moisture = map(moistRaw, 0, 4095, 0, 100); // calibrate

  if(isnan(temp)) temp = 29.5; // fallback

  String json = "{\"ph\":"+String(ph,1)+",\"temp\":"+String(temp,1)+",\"moisture\":"+String(moisture,0)+"}";
  
  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    http.begin(firebaseURL);
    http.addHeader("Content-Type", "application/json");
    int code = http.PUT(json); // PUT overwrites live data
    Serial.println("Firebase Response: " + String(code) + " " + json);
    http.end();
  }
  delay(5000); // update your Vercel site every 5 sec
}
