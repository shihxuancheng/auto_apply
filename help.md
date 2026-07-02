# 自動請假程式使用說明

## 程式功能簡介
此程式是一個自動化工具，用於在指定時間自動提交 Google 表單的請假申請。程式具有以下主要功能：
- 支援即時執行或預約執行
- 使用 NTP 時間同步，確保執行時間準確性
- 支援遠端或本地 Chrome WebDriver
- 自動處理表單載入和提交
- 完整的日誌記錄功能

## 系統需求
- Python 3.x
- Chrome 瀏覽器
- ChromeDriver
- 網路連線（用於 NTP 時間同步）

## 安裝依賴
使用 uv 安裝與同步所需套件：
```bash
uv sync
```

## 設定檔說明
程式使用 `config.ini` 進行設定，主要包含兩個區段：

### default 區段
```ini
[default]
base_url = Google表單的基礎URL
submit_form_id = 表單提交按鈕的ID
submit_button_id = 提交按鈕的CSS選擇器
browser_options = Chrome瀏覽器的選項設定
```

### apply_data 區段
```ini
[apply_data]
# 在此設定表單填寫所需的參數
entry.xxxxx = 表單欄位值
```

## 使用方式

### 1. 立即執行
直接執行程式，不指定執行時間：
```bash
uv run auto-apply
```

### 2. 預約執行
指定執行時間（格式：YYYY-MM-DD HH:MM:SS）：
```bash
uv run auto-apply --execute_date "2025-06-14 14:30:00"
```

### 3. 其他參數選項
- `--dry-run`: 測試模式，只檢查環境設定
- `--config` / `-c`: 指定設定檔路徑
- `--execute_date` / `-d`: 指定執行時間

## 主要功能說明

### 時間同步機制
- 使用 NTP 伺服器進行時間同步
- 自動補償本地時間與網路時間的誤差
- 定期檢查並調整執行時間

### 表單處理流程
1. 預先載入表單頁面
2. 驗證表單元素是否正確載入
3. 在指定時間執行提交操作
4. 確認提交結果並記錄

### 錯誤處理
- 完整的例外處理機制
- 詳細的錯誤日誌記錄
- 自動重試機制

## 日誌記錄
程式執行時會產生 `auto_apply.log` 檔案，記錄：
- 程式執行狀態
- 時間同步資訊
- 表單操作過程
- 錯誤和異常情況

## 注意事項
1. 請確保設定檔中的 URL 和表單參數正確
2. 執行時間建議預留緩衝時間
3. 需要正確安裝和配置 ChromeDriver
4. 建議先使用 `--dry-run` 測試環境設定

## 疑難排解
1. ChromeDriver 找不到：
   - 確認 ChromeDriver 已安裝
   - 檢查系統 PATH 設定
   
2. 表單提交失敗：
   - 檢查網路連線
   - 確認表單參數正確
   - 查看錯誤日誌

3. 時間同步問題：
   - 確認能夠連接 NTP 伺服器
   - 檢查系統時間設定

## 程式架構
主要模組和功能：
- 表單處理（_pre_load_form, _do_apply_leave）
- 時間管理（_get_ntp_time, _waiting_to_run）
- 設定管理（_load_config）
- WebDriver 管理（_pre_load_driver）
- 日誌系統（_init_log）

## 開發資訊
- 語言：Python
- 主要依賴：
  - playwright：網頁自動化
  - apscheduler：任務排程
  - ntplib：時間同步
  - configparser：設定檔處理

