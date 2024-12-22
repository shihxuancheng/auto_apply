#!/bin/bash

# 顯示使用說明
show_usage() {
    echo "用法: $0 <日期時間> <shell script 路徑>"
    echo "日期時間格式: HH:MM YYYY-MM-DD"
    echo "例如: $0 '2024-12-31 23:59' '/path/to/your/script.sh'"
    exit 1
}

# 檢查參數數量
if [ $# -ne 2 ]; then
    show_usage
fi

# 取得日期時間和腳本路徑
datetime="$1"
script_path="$2"

# 檢查腳本是否存在且可執行
if [ ! -f "$script_path" ]; then
    echo "錯誤：腳本檔案不存在：$script_path"
    exit 1
fi

if [ ! -x "$script_path" ]; then
    echo "錯誤：腳本檔案沒有執行權限：$script_path"
    echo "請執行：chmod +x $script_path"
    exit 1
fi

# 驗證日期時間格式
if ! date -d "$datetime" >/dev/null 2>&1; then
    echo "錯誤：無效的日期時間格式"
    show_usage
fi

# 檢查是否為過去的時間
current_timestamp=$(date +%s)
target_timestamp=$(date -d "$datetime" +%s)
duration=$((target_timestamp - current_timestamp))

if [ $duration -le 0 ]; then
    echo "錯誤：請指定未來的時間"
    exit 1
fi

# 顯示排程資訊
echo "排程資訊："
echo "執行時間: $datetime"
echo "執行腳本: $script_path"
echo "等待時間: $(($duration / 86400)) 天 $(($duration % 86400 / 3600)) 小時 $((($duration % 3600) / 60)) 分鐘"

# 建立 at 指令內容（使用完整路徑）
at_command="$script_path"

# 設定 at 指令
echo "$at_command" | at "$datetime"
if [ $? -ne 0 ]; then
    echo "錯誤：無法設定 at 排程"
    exit 1
fi

echo "已成功設定 at 排程"

# 執行 systemd-inhibit
echo "啟動 systemd-inhibit 保持系統運作..."
sudo systemd-inhibit --what="sleep:idle" \
                --who="schedule_keeper" \
                --why="等待執行排程腳本：$script_path 於 $datetime" \
                /bin/bash -c "sleep $duration && echo '目標時間已到，釋放系統限制'"

# 檢查最終執行狀態
if [ $? -eq 0 ]; then
    echo "腳本執行完成"
else
    echo "警告：systemd-inhibit 異常結束"
fi