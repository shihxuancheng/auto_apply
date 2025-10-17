import argparse
import asyncio
import configparser
import logging
import ast
import os
import sys
import traceback
from datetime import datetime, date, timedelta

import ntplib
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from playwright.async_api import async_playwright, Playwright, Browser, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

_logger = None

# 常數
WAIT_TIMEOUT = 10000  # Playwright 使用毫秒


async def wait_and_find_element(page: Page, selector: str, timeout: int = WAIT_TIMEOUT):
    """等待並找到一個元素"""
    return await page.wait_for_selector(selector, timeout=timeout)


async def wait_and_click_button(page: Page, selector: str, timeout: int = WAIT_TIMEOUT):
    """等待並點擊一個按鈕"""
    button = await page.wait_for_selector(selector, state='visible', timeout=timeout)
    await button.click()


def _init_log() -> logging.Logger:
    # 設定日誌格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 建立 logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 建立檔案處理器
    log_path = os.path.join(os.path.curdir, "auto_apply.log")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    # 建立控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 將處理器新增至 logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def _load_config(config_file: str) -> tuple:
    """
    載入設定檔並返回設定資料。
    """
    try:
        _logger.info(f"載入設定檔: {config_file}")
        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        default_config = dict(config.items("default"))
        apply_data = dict(config.items("apply_data"))
        return default_config, apply_data
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        _logger.error(f"讀取設定檔錯誤: {e}")
        sys.exit(1)
    except Exception as e:
        _logger.error(f"發生錯誤: {e}")
        _logger.error(traceback.format_exc())
        raise


async def _verify_playwright() -> None:
    """
    驗證 Playwright 是否安裝正確。
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
        _logger.info("Playwright 安裝正確。")
    except Exception as e:
        _logger.error(f"發生錯誤: {e}")
        _logger.error(traceback.format_exc())
        raise


async def _pre_load_form(page: Page, target_url: str, submit_form_id: str) -> None:
    """預先載入表單頁面"""
    try:
        current_url = page.url
        if current_url != target_url:
            _logger.info(f"目前網址: {current_url}")
            _logger.info(f"導覽至: {target_url}")
            await page.goto(target_url)

        # 確認表單已載入
        await wait_and_find_element(page, f"#{submit_form_id}")
        _logger.info("表單預載成功")

    except PlaywrightTimeoutError:
        _logger.error("等待元素超時")
        raise
    except Exception as e:
        _logger.error(f"預載表單錯誤: {e}")
        _logger.error(traceback.format_exc())
        raise


async def _do_apply_leave(page: Page, base_url: str, submit_button_id: str, apply_data: dict) -> None:
    """執行請假申請提交"""
    try:
        # 點擊提交按鈕
        await wait_and_click_button(page, f"{submit_button_id}")

        # 等待頁面導覽
        await page.wait_for_url(f"{base_url.split('?')[0]}/formResponse", timeout=WAIT_TIMEOUT)

        # 記錄成功訊息
        params = "\n".join([f"{key}={value}" for key, value in apply_data.items()])
        _logger.info(f"請假申請提交成功，參數:\n{params}")

        await asyncio.sleep(1)  # 延遲以確保表單提交被處理

    except PlaywrightTimeoutError:
        _logger.error("等待元素超時")
    except Exception as e:
        _logger.error(f"提交表單錯誤: {e}")
        _logger.error(traceback.format_exc())


def _valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise argparse.ArgumentTypeError(f"不是有效的日期: '{s}'.")


def _get_ntp_time(ntp_server: str = None) -> datetime:
    """
    取得 NTP 時間。
    """
    try:
        client = ntplib.NTPClient()
        ntp_server_addr = ntp_server or 'pool.ntp.org'
        response = client.request(ntp_server_addr)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as e:
        _logger.error(f"取得 NTP 時間失敗: {e}")
        _logger.error(traceback.format_exc())
        return datetime.now()


async def scheduled_job(job_done_event: asyncio.Event, page: Page, target_url: str, submit_button_id: str, apply_data: dict):
    """由排程器呼叫的作業，僅執行提交動作。"""
    try:
        await _do_apply_leave(page, target_url, submit_button_id, apply_data)
    except Exception as e:
        _logger.error(f"排程工作期間發生錯誤: {e}")
        _logger.error(traceback.format_exc())
    finally:
        job_done_event.set()


async def setup_scheduled_run(page: Page, target_url: str, execute_date: datetime, default_config: dict, apply_data: dict) -> None:
    """
    設定 APScheduler 在指定的 NTP 時間執行任務。
    """
    pre_launch_time = float(default_config.get('prelaunch_time', 0.1))

    # 取得目前 NTP 時間
    current_ntp_time = _get_ntp_time(default_config.get('ntp_server'))
    _logger.info(f"目標執行時間: {execute_date}")
    _logger.info(f"目前 NTP 時間: {current_ntp_time}")

    # 檢查時間是否已過
    if current_ntp_time > execute_date:
        _logger.error("指定的執行時間已過。")
        return

    # 計算 NTP 時間與本地時間的差異
    local_time = datetime.now()
    ntp_local_diff = (current_ntp_time - local_time).total_seconds()
    _logger.info(f"時間差異 (NTP - 本地): {ntp_local_diff:.3f} 秒")

    # 考慮差異調整執行時間
    adjusted_execute_date = execute_date - timedelta(seconds=ntp_local_diff) - timedelta(
        seconds=pre_launch_time)

    job_done_event = asyncio.Event()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_job,
        trigger=DateTrigger(run_date=adjusted_execute_date),
        id='apply_leave_job',
        args=[job_done_event, page, target_url, default_config["submit_button_id"], apply_data]
    )

    scheduler.start()
    _logger.info(
        f"任務已排程，預先啟動: {pre_launch_time} 秒，將於 {adjusted_execute_date} 執行。等待任務完成...")

    try:
        await job_done_event.wait()
        _logger.info("排程任務已執行完畢。")
    except (KeyboardInterrupt, SystemExit):
        _logger.info("收到中斷訊號，取消任務排程。")
    finally:
        scheduler.shutdown()
        _logger.info("排程器已關閉。")


async def _pre_load_browser(playwright: Playwright, browser_options: dict) -> Browser:
    """
    使用預設設定載入瀏覽器。
    """
    _logger.info("預先載入瀏覽器。")
    try:
        browser = await playwright.chromium.launch(**browser_options)
    except Exception as e:
        _logger.error(f"初始化瀏覽器時發生錯誤: {e}")
        _logger.error(traceback.format_exc())
        raise

    return browser


async def main():
    global _logger
    _logger = _init_log()

    parser = argparse.ArgumentParser(
        description='AutoApply - Command line arguments',
        epilog='Version 0.0.8 - A tool to automate leave applications with Playwright'
    )

    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--config", "-c", type=str, help="Path to the configuration file")
    parser.add_argument("--execute_date", "-d", type=_valid_date,
                        help="Date in 'YYYY-MM-DD HH:MM:SS' format")
    parser.add_argument("--version", "-v", action="store_true", help="Show version information")

    args = parser.parse_args()

    if args.version:
        print("AutoApply version 0.0.8")
        sys.exit(0)

    config_path = args.config or os.path.join(os.path.curdir, "config.ini")
    if not os.path.exists(config_path):
        _logger.error(f"Config file not found at: {config_path}")
        sys.exit(1)
    default_config, apply_data = _load_config(config_path)

    if args.dry_run:
        _logger.info("Dry run mode is enabled.")
        await _verify_playwright()
        sys.exit(0)

    browser_options = {}
    browser_args = list()
    if "browser_options" in default_config:
        browser_options['headless'] = False
        for option in default_config["browser_options"].split(","):
            option = option.strip()
            if option == "--headless":
                browser_options["headless"] = True
            elif option == "--no-sandbox":
                # Playwright does not need this option
                pass
            elif "=" in option:
                key, value = option.split("=", 1)
                browser_options[key.strip()] = ast.literal_eval(value.strip())
            else:
                browser_args.append(option)
        browser_options["args"] = browser_args

    base_url = default_config["base_url"]
    target_url = f"{base_url}/viewform?{'&'.join([f'{k}={v}' for k, v in apply_data.items()])}"

    async with async_playwright() as p:
        browser = await _pre_load_browser(p, browser_options)
        page = await browser.new_page()
        try:
            # 無論何種模式，都先載入頁面
            await _pre_load_form(page, target_url, default_config["submit_form_id"])

            if args.execute_date:
                # 對於排程執行，傳入已載入的 page 物件
                await setup_scheduled_run(page, base_url, args.execute_date, default_config, apply_data)
            else:
                # 對於立即執行，直接提交
                _logger.info("未指定執行時間，立即執行。")
                await _do_apply_leave(page, base_url, default_config["submit_button_id"], apply_data)
        except Exception as e:
            _logger.error(f"執行期間發生錯誤: {e}")
            _logger.error(traceback.format_exc())
        finally:
            _logger.info("所有任務完成，關閉瀏覽器。")
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
