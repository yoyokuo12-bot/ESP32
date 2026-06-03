# firmware/src

## 使用方式

1. 複製 `config.example.h` 為 `config.h`
2. 在 `config.h` 填入你的 Wi-Fi 名稱和密碼
3. `config.h` 已被 `.gitignore` 排除，不會上傳到 GitHub

## 接線

| 感測器 | 腳位 | GPIO |
|--------|------|------|
| 土壤濕度 AOUT | P34 | GPIO34 |
| KY-018 光照 S | P35 | GPIO35 |
| 所有感測器 VCC | 3V3 | - |
| 所有感測器 GND | GND | - |
