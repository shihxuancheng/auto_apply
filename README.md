# Auto Apply

## Installation

1. 安裝python runtime

    [python 3.11.9 for windows](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)


2. 安裝python dependencies
3. 建立windows schedule job

    ${date} => 

    ${time} =>

    ${command} =>

``` commandline
    C:\Users\xxxx> schtasks /create /tn "AutoApplyTask" /tr "${command}" /sc once /st ${time} /sd ${date}
```

## Configuration
`config.ini` - 必須放在與主程式相同目錄下

```ini
[default]
browser_options=--incognito, --headless
submit_form_id = mG61Hd
submit_button_id = div[aria-label='Submit']
base_url= ;google form 網址

[apply_data];以下為填入google form的欄位資料
entry.1181820941= ;姓名
entry.70409162= ;員工編號
entry.319914732=特休
;請假起始日期
entry.1500043702_year= 2024
entry.1500043702_month= 10
entry.1500043702_day= 1
;請假終止日期
entry.877270293_year= 2024
entry.877270293_month= 10
entry.877270293_day= 10
entry.126777822=長假
entry.1012076469= 無
entry.1660152178= 我確認了
entry.1288315452= ;請假密碼
```