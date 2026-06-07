/**
 * @file main.cpp
 * @brief L1 邊緣感測層 — 擬人化盆栽幽默日記系統
 *
 * 功能：
 *   F-A1: 讀取 GPIO34 土壤濕度（10 次取樣取中位數）
 *   F-A2: temp_c / humidity_pct 以模擬值填入（MVP 期間，BME280 到貨後改真實讀值）
 *   F-A3: 依 contracts/telemetry.schema.json 打包 JSON，經 MQTT publish
 *   F-A4: 編譯旗標 USE_REAL_BME280 一鍵切換真實 ↔ 模擬感測來源
 *
 * 硬體接線（Pin Mapping）:
 *   GPIO 34  → 土壤濕度感測模組 AO（DO 不使用）
 *   GPIO 35  → KY-018 光敏電阻模組 S
 *   GPIO 21  → BME280 SDA（BME280 到貨後啟用）
 *   GPIO 22  → BME280 SCL（BME280 到貨後啟用）
 *   3V3      → 感測器 VCC
 *   GND      → 感測器 GND
 *
 * 所需函式庫（Arduino IDE 函式庫管理員安裝）:
 *   - PubSubClient  (MQTT)
 *   - ArduinoJson   (JSON 序列化)
 *   - Adafruit BME280 Library（USE_REAL_BME280 時需要）
 *   - Adafruit Unified Sensor（BME280 相依）
 *
 * MQTT Topic: plants/{NODE_ID}/telemetry
 */

// ─── 編譯旗標：設為 1 時啟用真實 BME280，0 時使用模擬值 ────────────
#ifndef USE_REAL_BME280
#define USE_REAL_BME280  0   // BME280 到貨後改成 1，或由 platformio.ini 的 build_flags 設定
#endif

// ─── Wi-Fi / MQTT 設定 ── 請見 config.h（複製 config.example.h 填入）────

// ─── 感測器 / 節點設定 ──────────────────────────────────────────────
#define NODE_ID          "plant_01"           // 要符合 schema: ^plant_[0-9]{2,}$
#define SOIL_ADC_PIN     34                   // 土壤濕度感測器類比腳位（接 P34/GPIO34）
#define LIGHT_ADC_PIN    35                   // KY-018 光照類比腳位（接 P35/GPIO35）
#define SAMPLE_COUNT     10                   // 中位數濾波取樣次數
#define PUBLISH_INTERVAL 30000UL              // 發布間隔（ms）：30000 = 30 秒（除錯用）
//                                              MVP 除錯建議改成 30000（30秒）

// ─── 函式庫 ─────────────────────────────────────────────────────────
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <algorithm>   // std::sort
#include "config.h"    // Wi-Fi / MQTT 個人設定（已加入 .gitignore）

#if USE_REAL_BME280
  #include <Wire.h>
  #include <Adafruit_BME280.h>
  Adafruit_BME280 bme;
  bool bmeReady = false;
#endif

// ─── 全域物件 ────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

char mqttTopic[64];   // "plants/plant_01/telemetry"

// ─── 工具函數：中位數濾波 ────────────────────────────────────────────
/**
 * 從指定 ADC 腳位讀取 SAMPLE_COUNT 次原始值，
 * 排序後取中位數，去除毛刺雜訊。
 * @param pin  ADC GPIO 編號
 * @return     中位數 ADC 值（0–4095）
 */
int readMedian(int pin) {
  // 診斷：先印出單次直接讀值
  int rawSingle = analogRead(pin);
  Serial.printf("[ADC 診斷] GPIO%d 單次讀值: %d\n", pin, rawSingle);

  int samples[SAMPLE_COUNT];
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    samples[i] = analogRead(pin);
    delay(5);  // 每次取樣間隔 5ms，避免 ADC 自干擾
  }
  std::sort(samples, samples + SAMPLE_COUNT);
  return samples[SAMPLE_COUNT / 2];
}

// ─── Wi-Fi 連線 ──────────────────────────────────────────────────────
void connectWiFi() {
  Serial.printf("[WiFi] 連線中... SSID: %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WiFi] 已連線，IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\n[WiFi] 連線失敗，重啟...");
    ESP.restart();
  }
}

// ─── MQTT 連線 ───────────────────────────────────────────────────────
void connectMQTT() {
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  while (!mqttClient.connected()) {
    Serial.printf("[MQTT] 連線至 %s:%d ...\n", MQTT_BROKER, MQTT_PORT);
    if (mqttClient.connect(MQTT_CLIENT_ID)) {
      Serial.println("[MQTT] 已連線！");
    } else {
      Serial.printf("[MQTT] 失敗，rc=%d，5 秒後重試\n", mqttClient.state());
      delay(5000);
    }
  }
}

// ─── 模擬溫濕度（MVP 期間 BME280 未到貨時使用）─────────────────────
/**
 * 以正弦函數模擬日夜溫度變化（22–28°C），
 * 濕度以隨機值模擬（55–70%）。
 */
void getSimulatedTempHumidity(float &temp_c, float &humidity_pct) {
  unsigned long t = millis() / 1000UL;
  // 24 小時週期正弦：模擬溫度在 22–28°C 間變化
  temp_c       = 25.0f + 3.0f * sin(2.0f * 3.14159f * t / 86400.0f);
  // 濕度：55–70%，輕微隨機
  humidity_pct = 62.5f + (float)(random(-75, 75)) / 10.0f;
}

// ─── 讀取並發布感測數據 ───────────────────────────────────────────────
void publishTelemetry() {
  // 確保 MQTT 連線
  if (!mqttClient.connected()) connectMQTT();
  mqttClient.loop();

  // 1. 讀取土壤濕度（GPIO34，10 次中位數）
  int moisture_raw = readMedian(SOIL_ADC_PIN);

  // 2. 讀取光照（KY-018，GPIO35）
  int light_raw = readMedian(LIGHT_ADC_PIN);

  // 3. 溫濕度
  float temp_c = 0.0f, humidity_pct = 0.0f;
  bool  simFlag = false;

#if USE_REAL_BME280
  if (bmeReady) {
    temp_c       = bme.readTemperature();
    humidity_pct = bme.readHumidity();
    simFlag      = false;
  } else {
    getSimulatedTempHumidity(temp_c, humidity_pct);
    simFlag = true;
  }
#else
  getSimulatedTempHumidity(temp_c, humidity_pct);
  simFlag = true;
#endif

  // 4. 取得 Unix 時間戳（WiFi 連線後 ESP32 沒有 NTP，以 millis 秒數替代）
  //    若需精確時戳，請加入 configTime() / NTPClient 取 NTP 時間。
  long ts = (long)(millis() / 1000UL);

  // 5. 組裝 JSON（ArduinoJson v6）
  StaticJsonDocument<256> doc;
  doc["node"]         = NODE_ID;
  doc["ts"]           = ts;
  doc["moisture_raw"] = moisture_raw;
  doc["light_raw"]    = light_raw;
  doc["temp_c"]       = round(temp_c * 100.0f) / 100.0f;
  doc["humidity_pct"] = round(humidity_pct * 100.0f) / 100.0f;
  if (simFlag) doc["sim"] = true;

  char payload[256];
  size_t len = serializeJson(doc, payload, sizeof(payload));

  // 6. Publish（PubSubClient 預設 QoS 0，retain=false）
  bool ok = mqttClient.publish(mqttTopic, (uint8_t*)payload, len, false);

  Serial.printf("[Publish] Topic: %s\n", mqttTopic);
  Serial.printf("[Payload] %s\n", payload);
  Serial.printf("[Result ] %s\n\n", ok ? "OK ✓" : "FAIL ✗");
}

// ─── setup() ─────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== 擬人化盆栽 IoT — L1 韌體啟動 ===");

  // 設定 ADC 解析度（ESP32 預設 12-bit，最大值 4095）
  // GPIO34 為 input-only ADC 腳位，直接讀取即可（不需要額外設定）
  analogReadResolution(12);

  // 設定 MQTT Topic
  snprintf(mqttTopic, sizeof(mqttTopic), "plants/%s/telemetry", NODE_ID);

#if USE_REAL_BME280
  Wire.begin(21, 22);  // SDA=21, SCL=22
  if (!bme.begin(0x76)) {
    // 若位址 0x76 不通，嘗試 0x77（視模組 SDO 接腳決定）
    if (!bme.begin(0x77)) {
      Serial.println("[BME280] 初始化失敗！確認接線與位址。");
      bmeReady = false;
    } else {
      Serial.println("[BME280] 初始化成功（位址 0x77）");
      bmeReady = true;
    }
  } else {
    Serial.println("[BME280] 初始化成功（位址 0x76）");
    bmeReady = true;
  }
#else
  Serial.println("[模式] 溫濕度使用模擬資料（USE_REAL_BME280=0）");
#endif

  connectWiFi();
  connectMQTT();

  Serial.printf("[設定] 發布間隔：%lu 秒\n", PUBLISH_INTERVAL / 1000UL);
  Serial.println("========================================\n");

  // 啟動後立即發一次
  publishTelemetry();
}

// ─── loop() ──────────────────────────────────────────────────────────
void loop() {
  static unsigned long lastPublish = 0;

  // 保持 MQTT 心跳
  if (!mqttClient.connected()) connectMQTT();
  mqttClient.loop();

  // 到達發布間隔時才發布（always-on 模式，MVP 除錯用）
  if (millis() - lastPublish >= PUBLISH_INTERVAL) {
    lastPublish = millis();
    publishTelemetry();
  }
}

/*
 * ─── 深度睡眠版本（完整目標，MVP 後啟用）────────────────────────────
 *
 * 若要改成深度睡眠（F-A5，節省電力）：
 *
 *   1. 在 setup() 末尾（publishTelemetry() 之後）加入：
 *
 *      const uint64_t SLEEP_US = 4ULL * 3600ULL * 1000000ULL;  // 4 小時
 *      Serial.printf("[Sleep] 進入深度睡眠 %llu 秒\n", SLEEP_US / 1000000ULL);
 *      Serial.flush();
 *      WiFi.disconnect(true);
 *      esp_deep_sleep(SLEEP_US);
 *
 *   2. loop() 可保留空迴圈，深度睡眠後每次喚醒都會重跑 setup()。
 *
 * ──────────────────────────────────────────────────────────────────── */
