import argparse
import configparser
import logging
import os
import shutil
import sys
import threading
import time
import traceback
from datetime import datetime, date, timedelta

import ntplib
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_logger = None
target_url = None
default_config = None
apply_data = None

# 常量定義
WAIT_TIMEOUT = 10


def _do_preload_page(driver: WebDriver,url: str, by: By, value: str, timeout: int = WAIT_TIMEOUT):
    """
        預載入指定頁面並等待元素出現

        Args:
            driver: WebDriver實例
            url: 要載入的URL
            by: 元素定位方式
            value: 元素定位值
            timeout: 等待超時時間，預設為WAIT_TIMEOUT

        Returns:
            找到的元素
        """

    driver.get(url)
    return WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
                  and EC.presence_of_element_located((by, value))
    )


def _do_click_button(driver: WebDriver, selector: str, timeout: int = WAIT_TIMEOUT):
    """等待並點擊按鈕"""
    button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    button.click()

    # 等待執行回應
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
                  and "/formResponse" in d.current_url
    )


def _init_log() -> logging.Logger:
    # 設定日誌格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 建立日誌記錄器
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 建立文件處理器
    log_path = os.path.curdir + os.sep + "auto_apply.log"
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    # 建立控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 將處理器添加到日誌記錄器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def _load_config(config_file: str) -> tuple:
    """
    載入配置文件並返回配置數據。
    """
    try:
        _logger.info(f"load config file: {config_file}")
        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        default_config = {key: config.get("default", key) for key in config.options("default")}
        apply_data = {key: config.get("apply_data", key) for key in config.options("apply_data")}
        return default_config, apply_data
    except Exception as e:
        _logger.error(f"Error occurred: {e}")
        _logger.error(traceback.print_exc())
        raise


def _verify_webdriver() -> None:
    """
    驗證webdriver是否正確安裝
    """
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--incognito')
        options.add_argument('--headless')
        service = Service(_find_chromedriver())
        driver = webdriver.Chrome(service=service, options=options)
        driver.quit()
        _logger.info("Webdriver is installed correctly.")
    except Exception as e:
        _logger.error(f"Error occurred: {e}")
        _logger.error(traceback.print_exc())
        raise


def _find_chromedriver():
    """ 在系統中搜尋並定位 ChromeDriver 的可執行文件。"""
    path = shutil.which('chromedriver')
    if path:
        _logger.info(f"Found chromedriver at: {path}")
        return path

    common_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
        os.path.expanduser('~/chromedriver')
    ]
    for common_path in common_paths:
        if os.path.exists(common_path):
            _logger.info(f"Found chromedriver at: {common_path}")
            return common_path

    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        potential_path = os.path.join(path_dir, 'chromedriver')
        if os.path.exists(potential_path):
            _logger.info(f"Found chromedriver at: {potential_path}")
            return potential_path
    return None


def _pre_load_driver(chromedriver_url_str: str = None) -> webdriver:
    """
    載入具有默認配置的webdriver
    """
    _logger.info("Pre-load the webdriver.")
    try:
        options = webdriver.ChromeOptions()
        for option in default_config["browser_options"].split(","):
            options.add_argument(option)

        chrome_log_path = f"{os.curdir}{os.sep}chromedrver-{date.today()}.log"
        driver = webdriver.Remote(chromedriver_url_str, options=options) if chromedriver_url_str else webdriver.Chrome(
            service=Service(_find_chromedriver(), log_output=chrome_log_path), options=options)
    except Exception as e:
        _logger.error(f"Error occurred while initializing the webdriver: {e}")
        _logger.error(traceback.print_exc())
        raise
    return driver


def _do_apply(execute_date: datetime, chromedriver_url_str: str = None) -> None:
    """
    預先載入表單頁面，並在指定時間點擊提交按鈕。
    此函數會創建兩個 WebDriver 實例，並使用多線程在不同時間點擊按鈕。
    """
    global target_url, default_config

    def click_button_action(click_time: datetime, button_selector: str, driver_url: str = None):
        """在指定時間點擊按鈕的任務"""
        driver = None
        try:
            driver = _pre_load_driver(driver_url)
            _do_preload_page(driver,target_url, By.CSS_SELECTOR, button_selector)
            _logger.info(f"執行序 {threading.get_ident()} 已載入頁面")
            
            wait_seconds = (click_time - _get_ntp_time(default_config.get('ntp_server'))).total_seconds()
            
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            _do_click_button(driver, button_selector)

            _logger.info(f"執行緒 {threading.get_ident()} 提交成功")

        except TimeoutException:
            _logger.error(f"執行緒 {threading.get_ident()} 等待元素超時")
        except ElementClickInterceptedException:
            _logger.error(f"執行緒 {threading.get_ident()} 無法點擊提交按鈕")
        except Exception as e:
            _logger.error(f"執行緒 {threading.get_ident()} 發生錯誤: {e}")
            _logger.error(traceback.format_exc())
        finally:
            if driver:
                driver.quit()
            _logger.info(f"執行緒 {threading.get_ident()} 的 WebDriver 已關閉")

    try:
        main_click_time = execute_date
        early_click_time = execute_date - timedelta(milliseconds=500)
        button_selector = default_config["submit_button_id"]

        thread_main = threading.Thread(target=click_button_action, args=(main_click_time, button_selector, chromedriver_url_str))
        thread_early = threading.Thread(target=click_button_action, args=(early_click_time, button_selector, chromedriver_url_str))

        _logger.info(f"啟動主要執行緒，預計點擊時間: {main_click_time}")
        thread_main.start()

        _logger.info(f"啟動提前執行緒，預計點擊時間: {early_click_time}")
        thread_early.start()

        thread_main.join()
        thread_early.join()

        _logger.info("所有點擊任務已完成")

    except Exception as e:
        _logger.error(f"預載入或執行緒設置時發生錯誤：{e}")
        _logger.error(traceback.format_exc())
        raise


def _valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except:
        raise argparse.ArgumentTypeError(f"Not a valid date: '{s}'.")


def _get_ntp_time(ntp_server: str = None) -> datetime:
    """獲取 NTP 時間"""
    try:
        client = ntplib.NTPClient()
        ntp_server_addr = ntp_server or 'pool.ntp.org'
        response = client.request(ntp_server_addr)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as e:
        _logger.warning(f"獲取 NTP 時間失敗: {e}，將使用本地時間")
        return datetime.now()


def _waiting_to_run(execute_date: datetime, chromedriver_url_str: str = None) -> None:
    """
    檢查NTP時間並直接調用表單處理函數。
    """
    current_ntp_time = _get_ntp_time(default_config.get('ntp_server'))
    _logger.info(f"當前 NTP 時間: {current_ntp_time}")

    if current_ntp_time > execute_date:
        _logger.error("指定的執行時間已過期")
        return

    # 计算 NTP 时间与本地时间的差异
    local_time = datetime.now()
    _logger.info(f"本地時間: {local_time}")
    ntp_local_diff = (current_ntp_time - local_time).total_seconds()
    _logger.info(f"[時間差]: {ntp_local_diff} seconds")

    # 调整执行时间，考虑本地时间与 NTP 时间的差异
    adjusted_execute_date = execute_date - timedelta(seconds=ntp_local_diff)

    # 直接調用新的表單處理函數，它內部會處理等待和多線程點擊
    _do_apply(adjusted_execute_date, chromedriver_url_str)


def main():
    global _logger, default_config, apply_data, target_url
    _logger = _init_log()

    parser = argparse.ArgumentParser(
        description='AutoApply - Command line arguments',
        epilog='Version 0.0.6 - A tool to automate leave applications'
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--config", "-c", type=str, help="Path to the configuration file")
    parser.add_argument("--execute_date", "-d", type=_valid_date, help="Date in the format: 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("--version", "-v", action="store_true", help="Show version information")
    parser.add_argument('--driver-url', type=str, help='Remote WebDriver URL')
    parser.add_argument('--driver-port', type=str, help='Remote WebDriver Port')
    args = parser.parse_args()

    if args.version:
        print("AutoApply version 0.0.6")
        sys.exit(0)

    if (args.driver_url is None) != (args.driver_port is None):
        parser.error('the url and port must be provided together')

    config_path = args.config or os.path.join(os.curdir, "config.ini")
    default_config, apply_data = _load_config(config_path)

    if args.dry_run:
        _logger.info("Dry run mode is enabled.")
        _verify_webdriver()
        sys.exit(0)

    target_url = default_config["base_url"] + "/viewform" + "?" + "&".join(
        [f"{key}={value}" for key, value in apply_data.items()]
    )
    _logger.info(f"預計連線至: {target_url}")
    
    chromedriver_url = f"http://{args.driver_url}:{args.driver_port}" if args.driver_url and args.driver_port else None

    try:
        if args.execute_date:
            _waiting_to_run(args.execute_date, chromedriver_url)
        else:
            _logger.info("未指定執行時間，將在2秒後立即執行")
            now_execute_time = _get_ntp_time(default_config.get('ntp_server')) + timedelta(seconds=2)
            _do_apply(now_execute_time, chromedriver_url)
    except Exception as e:
        _logger.error(f"執行過程發生錯誤: {e}")
        _logger.error(traceback.format_exc())

if __name__ == '__main__':
    main()