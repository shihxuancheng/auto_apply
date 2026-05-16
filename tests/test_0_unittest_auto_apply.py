import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
import asyncio
import argparse
from datetime import datetime
import configparser
import logging
import os
import sys

# 將 src 目錄新增到 sys.path 以便 import auto_apply
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# 匯入需要測試的函式
from auto_apply import (
    _init_log,
    _load_config,
    _verify_playwright,
    _pre_load_form,
    _do_apply_leave,
    _valid_date,
    _get_ntp_time,
    scheduled_job,
    setup_scheduled_run,
    _pre_load_browser,
    main,
    cli_main
)

# 關閉測試期間的日誌輸出
logging.disable(logging.CRITICAL)

@pytest.fixture(scope="module")
def event_loop():
    """為整個測試模組提供一個事件循環。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.mark.unit
def test_init_log():
    """測試日誌設定函式。"""
    logger = _init_log()
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO
    # 檢查是否同時設定了檔案和控制台的 handler
    assert len(logger.handlers) >= 2

@pytest.mark.unit
def test_load_config_success(mocker):
    """測試成功載入設定檔。"""
    mock_config = MagicMock()
    # 模擬 config.items() 的回傳值
    mock_config.items.side_effect = [
        [('url', 'http://test.com')],
        [('username', 'testuser')]
    ]
    mocker.patch('configparser.ConfigParser').return_value = mock_config
    mocker.patch('auto_apply._logger') # 模擬 logger

    default_config, apply_data = _load_config('dummy_config.ini')

    assert default_config == {'url': 'http://test.com'}
    assert apply_data == {'username': 'testuser'}

@pytest.mark.unit
def test_load_config_fail(mocker):
    """測試載入設定檔失敗。"""
    # 模擬讀取時發生區段錯誤
    mocker.patch('configparser.ConfigParser.read', side_effect=configparser.NoSectionError('default'))
    mock_logger = mocker.patch('auto_apply._logger')

    with pytest.raises(SystemExit):
        _load_config('dummy_config.ini')
    
    # 驗證是否有錯誤日誌被記錄
    mock_logger.error.assert_called()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_playwright(mocker):
    """測試 Playwright 環境驗證。"""
    mock_playwright = mocker.patch('auto_apply.async_playwright')
    # Ensure launch is an AsyncMock so it can be awaited
    mock_p = mock_playwright.return_value.__aenter__.return_value
    mock_p.chromium.launch = AsyncMock(return_value=AsyncMock())
    
    mock_logger = mocker.patch('auto_apply._logger')

    await _verify_playwright()

    mock_logger.info.assert_called_with("Playwright 安裝正確。")

@pytest.mark.unit
@pytest.mark.asyncio
async def test_pre_load_form(mocker):
    """測試表單預載入功能。"""
    mock_page = AsyncMock()
    mock_page.url = "http://initial.url"
    mock_wait_and_find = mocker.patch('auto_apply.wait_and_find_element', new_callable=AsyncMock)
    mock_logger = mocker.patch('auto_apply._logger')

    await _pre_load_form(mock_page, "http://target.url", "submit_id")

    mock_page.goto.assert_called_once_with("http://target.url")
    mock_wait_and_find.assert_called_once_with(mock_page, "#submit_id")
    mock_logger.info.assert_called_with("表單預載成功")

@pytest.mark.unit
@pytest.mark.asyncio
async def test_do_apply_leave(mocker):
    """測試執行請假申請的提交邏輯。"""
    mock_page = AsyncMock()
    mock_wait_and_click = mocker.patch('auto_apply.wait_and_click_button', new_callable=AsyncMock)
    mock_logger = mocker.patch('auto_apply._logger')

    await _do_apply_leave(mock_page, "http://base.url?p=1", "#submit_id", {'data': 'test'})

    mock_wait_and_click.assert_called_once_with(mock_page, "#submit_id")
    mock_page.wait_for_url.assert_called_once_with("http://base.url/formResponse", timeout=10000)
    assert "請假申請提交成功" in mock_logger.info.call_args[0][0]

@pytest.mark.unit
def test_valid_date_success():
    """測試有效的日期字串解析。"""
    date_str = "2025-10-18 10:00:00"
    expected = datetime(2025, 10, 18, 10, 0, 0)
    assert _valid_date(date_str) == expected

@pytest.mark.unit
def test_valid_date_fail():
    """測試無效的日期字串解析。"""
    with pytest.raises(argparse.ArgumentTypeError, match="不是有效的日期"):     
        _valid_date("invalid-date-format")

@pytest.mark.unit
def test_get_ntp_time_success(mocker):
    """測試成功獲取 NTP 時間。"""
    mock_response = MagicMock()
    # 設定一個固定的時間戳
    mock_response.tx_time = datetime(2025, 1, 1, 12, 0, 0).timestamp()
    mock_ntp_client = mocker.patch('ntplib.NTPClient').return_value
    mock_ntp_client.request.return_value = mock_response

    ntp_time = _get_ntp_time()
    
    assert ntp_time == datetime(2025, 1, 1, 12, 0, 0)

@pytest.mark.unit
def test_get_ntp_time_fail(mocker):
    """測試獲取 NTP 時間失敗時，回退到本地時間。"""
    mocker.patch('ntplib.NTPClient', side_effect=Exception("NTP Error"))
    mock_logger = mocker.patch('auto_apply._logger')
    
    # 模擬 datetime.now() 以得到可預測的結果
    fixed_now = datetime(2024, 1, 1)
    mocker.patch('auto_apply.datetime').now.return_value = fixed_now

    fallback_time = _get_ntp_time()

    mock_logger.error.assert_called()
    assert fallback_time == fixed_now

@pytest.mark.unit
@pytest.mark.asyncio
async def test_scheduled_job(mocker):
    """測試排程執行的核心工作函式。"""
    mock_do_apply = mocker.patch('auto_apply._do_apply_leave', new_callable=AsyncMock)
    mock_event = AsyncMock()
    mock_event.set = MagicMock() # set 是同步方法

    await scheduled_job(mock_event, MagicMock(), "http://url", "#id", {})

    mock_do_apply.assert_called_once()
    mock_event.set.assert_called_once()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_scheduled_run(mocker):
    """測試設定排程任務的邏輯。"""
    mock_scheduler = mocker.patch('auto_apply.AsyncIOScheduler').return_value
    mocker.patch('auto_apply._get_ntp_time', return_value=datetime(2025, 10, 18, 9, 0, 0))
    
    # 模擬 asyncio.Event 來避免測試掛起
    mock_event = mocker.patch('asyncio.Event').return_value
    mock_event.wait = AsyncMock()
    
    mocker.patch('auto_apply._logger')
    
    execute_date = datetime(2025, 10, 18, 10, 0, 0)
    default_config = {'prelaunch_time': '0.1', 'submit_button_id': 'submit'}

    await setup_scheduled_run(MagicMock(), "http://url", execute_date, default_config, {})

    mock_scheduler.add_job.assert_called_once()
    mock_scheduler.start.assert_called_once()
    mock_event.wait.assert_awaited_once()
    mock_scheduler.shutdown.assert_called_once()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_pre_load_browser(mocker):
    """測試預先載入瀏覽器。"""
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser
    mocker.patch('auto_apply._logger')

    browser = await _pre_load_browser(mock_playwright, {'headless': True})

    assert browser == mock_browser
    mock_playwright.chromium.launch.assert_called_once_with(headless=True)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_main_dry_run(mocker):
    """測試主函式 --dry-run 模式。"""
    mocker.patch('sys.argv', ['auto_apply.py', '--dry-run'])
    mocker.patch('auto_apply._load_config', return_value=({}, {}))
    mock_verify = mocker.patch('auto_apply._verify_playwright', new_callable=AsyncMock)
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('auto_apply._init_log')

    with pytest.raises(SystemExit) as e:
        await main()
    
    assert e.value.code == 0
    mock_verify.assert_called_once()

@pytest.mark.unit
@pytest.mark.asyncio
async def test_main_immediate_run(mocker):
    """測試主函式立即執行模式。"""
    mocker.patch('sys.argv', ['auto_apply.py'])
    mocker.patch('auto_apply._load_config', return_value=(
        {'base_url': 'http://test', 'submit_button_id': 'submit', 'submit_form_id': 'form'}, {'p': '1'}
    ))
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('auto_apply._init_log')

    # 模擬 playwright context manager
    mock_p = mocker.patch('auto_apply.async_playwright').return_value.__aenter__.return_value
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    
    # Ensure launch is an AsyncMock
    mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_browser.new_page.return_value = mock_page

    mock_pre_load_form = mocker.patch('auto_apply._pre_load_form', new_callable=AsyncMock)
    mock_do_apply = mocker.patch('auto_apply._do_apply_leave', new_callable=AsyncMock)

    await main()

    mock_pre_load_form.assert_called_once()
    mock_do_apply.assert_called_once()
    mock_browser.close.assert_awaited_once()

@pytest.mark.unit
def test_cli_main(mocker):
    """測試同步的命令列入口點。"""
    # 模擬 asyncio.run
    mock_run = mocker.patch('asyncio.run')
    
    # 強制使用 MagicMock 而非 AsyncMock，確保 main() 直接回傳字串
    from unittest.mock import MagicMock
    mocker.patch('auto_apply.main', new=MagicMock(return_value='dummy_coro_object'))

    cli_main()

    # 斷言 asyncio.run 是否被呼叫，且參數是我們設定的虛擬物件
    mock_run.assert_called_once_with('dummy_coro_object')