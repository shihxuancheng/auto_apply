# Auto Apply

## Installation

1. 下載 & 安裝 [python 3.11.9 for windows](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)

驗證python runtime 是否正確安裝? 輸入以下指令:

```shell 
   python --version
  
   Python 3.11.1
```

2. 下載 & 安裝 [auto-apply.zip](https://github.com/shihxuancheng/auto_apply/releases/download/v0.0.2/auto-apply.zip)
，下載後請解壓縮至本機路徑，例如c:\auto-applyru, 接著執行以下指令:

```shell
   c:\auto-apply> pip install auto_apply-0.0.2-py3-none-any.whl
```
驗證安裝否正確？請開啟command window，輸入以下指令:
``` shell
   c:\autoa-pply> auto-apply --help
   
   usage: auto-apply [-h] [--dry-run] [--config CONFIG] [--execute_date EXECUTE_DATE]

   AutoApply - Command line arguments

   options:
     -h, --help            show this help message and exit
     --dry-run             Dry run mode
     --config CONFIG, -c CONFIG
                           Path to the configuration file
     --execute_date EXECUTE_DATE, -d EXECUTE_DATE
                           Date in the format: 'YYYY-MM-DD HH:MM:SS'   
```

## Configuration
`config.ini` - 內含請假相關資料，請填寫必要欄位

```ini
[default]
browser_options=--incognito, --headless
submit_form_id = mG61Hd
submit_button_id = div[aria-label='Submit']
base_url= https://docs.google.com/forms/d/1hHHrf19cWw0Nn8C0RIgOwXwhcUQJSuNpqMoQCERuQVI

[apply_data];以下為填入google form的欄位資料
entry.1181820941= ;請填入姓名
entry.70409162= ;請填入員工編號
entry.319914732=特休
;請填入休假起始日期
entry.1500043702_year= 2024
entry.1500043702_month= 10
entry.1500043702_day= 1
;請填入休假終止日期
entry.877270293_year= 2024
entry.877270293_month= 10
entry.877270293_day= 10
entry.126777822=長假
entry.1012076469= 無
entry.1660152178= 我確認了
entry.1288315452= ;請填入請假密碼
```

## Execution

程式必須透過commandline執行，請先請開啟command window，方式：(開始 -> 執行 -> cmd)

1. 測試auto-apply是否安裝正確?

```shell
    c:\auto-apply> auto-apply --dry-run
```

2. 立即執行auto-apply

```shell
    c:\auto-apply> auto-apply
```

3. 在指定的日期時間執行auto-apply

```shell
    c:\auto-apply> auto-apply -d "2024-12-05 10:00:00" #程式會在2024年12月5日早上10點執行
```

## reference
- https://developer.chrome.com/docs/chromedriver/get-started?hl=zh-tw
- [webdriver for new chrome version](https://googlechromelabs.github.io/chrome-for-testing/)
- [webdriver for old chrome version](https://developer.chrome.com/docs/chromedriver/downloads?hl=zh-tw)