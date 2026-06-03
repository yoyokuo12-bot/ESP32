// ================================================================
// config.example.h — 設定範例（這個會上傳到 GitHub）
// ================================================================
// 使用方式：
//   1. 複製此檔案，命名為 config.h
//   2. 填入你自己的 Wi-Fi 名稱和密碼
//   3. config.h 已被 .gitignore 排除，不會上傳到 GitHub

// Wi-Fi 設定
#define WIFI_SSID        "你的WiFi名稱"
#define WIFI_PASSWORD    "你的WiFi密碼"

// MQTT Broker（預設使用免費公用 HiveMQ，可換成本機 Mosquitto IP）
#define MQTT_BROKER      "broker.hivemq.com"
#define MQTT_PORT        1883
#define MQTT_CLIENT_ID   "esp32_plant_01"
