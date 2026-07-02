# Auto Apply

本工具使用 Playwright 自動化填寫與提交 Google 表單，並支援 NTP 時間同步與排程功能。

## Installation

### 1. 安裝 Python 3.11+
請前往 [Python 官網](https://www.python.org/downloads/) 下載並安裝。

驗證安裝：
```shell 
python --version
# 輸出應為 Python 3.11.x 或更高版本
```

### 2. 安裝專案
在專案根目錄下執行：
```shell
uv sync
```
這會建立虛擬環境 `.venv` 並自動安裝所有必要套件與開發/測試依賴。

### 3. 安裝 Playwright 瀏覽器
```shell
uv run playwright install chromium
```

### 4. 驗證安裝
```shell
uv run auto-apply --help
```

## Configuration

請參考 `config-sample.ini` 建立您自己的 `config.ini`。

```ini
[default]
; 瀏覽器選項 (例如：--headless, --incognito)
browser_options = --incognito, --headless
; 表單提交按鈕的 CSS Selector (Google 表單通常為 mG61Hd 或特定的 Submit div)
submit_form_id = mG61Hd
submit_button_id = div[aria-label='Submit'], div[aria-label='提交']
; 表單基礎網址
base_url = https://docs.google.com/forms/d/e/...
; 預先啟動時間 (秒)
prelaunch_time = 0.2
; NTP 伺服器 (留空則使用預設 pool.ntp.org)
ntp_server =

[apply_data]
; Google 表單欄位 ID 與其對應的值
entry.497400789 = 姓名
entry.364080156 = 工號
entry.1790867136 = 特休
; 日期範例
entry.184210529_year = 2025
entry.184210529_month = 06
entry.184210529_day = 07
```

## Execution

### 1. 測試環境 (Dry Run)
驗證瀏覽器是否能正常啟動並預載表單：
```shell
uv run auto-apply --dry-run
```

### 2. 立即執行
```shell
uv run auto-apply
```

### 3. 排程執行
在指定時間點自動執行：
```shell
uv run auto-apply -d "2025-06-07 08:00:00"
```

## Testing

本專案使用 `pytest` 進行測試：
```shell
# 執行所有測試
uv run pytest

# 執行單元測試
uv run pytest -m unit

# 執行整合測試 (會啟動真實瀏覽器)
uv run pytest -m integration
```

## Advanced Scheduling

如果您需要透過作業系統層級（如 macOS Launchd, Windows Task Scheduler, Linux Crontab）來管理長期排程，可以參考 `schedule/` 目錄下的範例：
- `macos/`: 包含 `.plist` 設定檔範例。
- `windows/`: 包含 `.xml` 任務排程器匯入檔與 `.bat` 執行檔。
- `linux/`: 包含 shell 腳本範例。

## Reference
- [Playwright Python Documentation](https://playwright.dev/python/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)