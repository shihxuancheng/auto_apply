import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

# 將 src 目錄加入 sys.path 以便 import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from auto_apply import main as auto_apply_main

CONFIG_CONTENT = """
[default]
;browser_options=--incognito,--headless
browser_options=--incognito, --verbose, --headless
submit_form_id = mG61Hd
submit_button_id = div[aria-label='Submit'], div[aria-label='提交']
base_url=https://docs.google.com/forms/d/e/1FAIpQLSfD0hmBHbgzWdwh2gbSoWkZxbzAxpbiXEIyy_yaMk_bTNYGQg
prelaunch_time=0.2
ntp_server=

[apply_data]
entry.497400789=劉韋忻
entry.364080156= 781541
entry.1790867136= 特休
;請假起始日期
entry.184210529_year= 2025
entry.184210529_month= 06
entry.184210529_day= 07
;請假終止日期
entry.1203553174_year= 2025
entry.1203553174_month= 06
entry.1203553174_day= 07
entry.774510678= 近假
entry.384652859= 無
entry.208788989= 我確認了
entry.11260725=k0xukPId
"""


@pytest.fixture(scope="module")
def config_file(tmp_path_factory):
    """一個 module scope 的 fixture，建立一個共用的測試設定檔"""
    config_path = tmp_path_factory.mktemp("data") / "test-config.ini"
    config_path.write_text(CONFIG_CONTENT, encoding="utf-8")
    yield str(config_path)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.description("測試立即執行模式 - 驗證瀏覽器自動化申請流程")
async def test_immediate_execution(mocker, config_file):
    """
    測試立即執行模式。
    使用 Mock Logger 攔截訊息。
    """
    print("\nRunning test_immediate_execution with pytest...")
    mocker.patch('sys.exit')
    mocker.patch.object(sys, 'argv', ['auto_apply.py', '--config', config_file])
    
    # 模擬 _init_log 以便回傳我們的 mock_logger
    mock_logger = MagicMock()
    mocker.patch('auto_apply._init_log', return_value=mock_logger)

    await auto_apply_main()

    # 驗證是否有記錄成功的訊息
    success_called = any("請假申請提交成功" in str(call) for call in mock_logger.info.call_args_list)
    assert success_called, "應記錄 '請假申請提交成功' 訊息"
    print("test_immediate_execution finished.")


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.description("測試排程測試模式 - 驗證瀏覽器自動化申請流程")
async def test_scheduled_execution(mocker, config_file):
    """
    測試排程執行模式。
    使用 Mock Logger 攔截訊息。
    """
    print("\nRunning test_scheduled_execution with pytest...")
    
    # 固定目前時間以便 Mock
    now = datetime.now()
    # 設定 5 秒後執行，給予足夠的瀏覽器啟動時間
    execute_time = now + timedelta(seconds=5)
    execute_time_str = execute_time.strftime("%Y-%m-%d %H:%M:%S")

    mocker.patch('sys.exit')
    mocker.patch.object(sys, 'argv', ['auto_apply.py', '-c', config_file, '-d', execute_time_str])
    
    # 模擬 NTP 時間，避免網路延遲導致過期
    mocker.patch('auto_apply._get_ntp_time', return_value=now)
    
    # 模擬 _init_log 以便回傳我們的 mock_logger
    mock_logger = MagicMock()
    mocker.patch('auto_apply._init_log', return_value=mock_logger)

    await auto_apply_main()

    # 驗證排程與執行訊息
    log_messages = [str(call) for call in mock_logger.info.call_args_list]
    assert any("任務已排程" in msg for msg in log_messages)
    assert any("排程任務已執行完畢" in msg for msg in log_messages)
    assert any("請假申請提交成功" in msg for msg in log_messages)
    print("test_scheduled_execution finished.")
