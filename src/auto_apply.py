import argparse
import configparser
import shutil
import logging
import os
import sys
import time
import traceback
import ntplib
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from tqdm import tqdm
from time import ctime

_logger = None


def _init_log() -> logging.Logger:
    # 設定日誌格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 建立日誌記錄器
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 建立文件處理器
    log_path = os.path.curdir + os.sep + "auto_apply.log"
    # print(f"Log: {log_path}")
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

    參數:
    config_file (str): 配置文件的路徑。

    返回:
    tuple: 包含兩個字典的元組，第一個字典是默認配置，第二個字典是申請數據。

    默認配置字典的鍵值對來自配置文件中的 "default" 部分。
    申請數據字典的鍵值對來自配置文件中的 "apply_data" 部分。
    """
    try:
        _logger.info(f"load config file: {config_file}")

        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        # load leave application data
        default_config = {key: config.get("default", key) for key in config.options("default")}
        apply_data = {key: config.get("apply_data", key) for key in config.options("apply_data")}

        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug(f"default_config: \n{pprint.pformat(default_config)}")
        #     logger.debug(f"apply_data: \n{pprint.pformat(apply_data)}")

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
    # 方法1：使用 shutil.which()
    path = shutil.which('chromedriver')
    if path:
        _logger.info(f"Found chromedriver at: {path}")
        return path

    # 方法2：檢查常見路徑
    common_paths = [
        '/usr/bin/chromedriver',
        '/usr/local/bin/chromedriver',
        os.path.expanduser('~/chromedriver')
    ]

    for common_path in common_paths:
        if os.path.exists(common_path):
            _logger.info(f"Found chromedriver at: {common_path}")
            return common_path

    # 方法3：遍歷 PATH
    for path in os.environ.get('PATH', '').split(os.pathsep):
        potential_path = os.path.join(path, 'chromedriver')
        if os.path.exists(potential_path):
            _logger.info(f"Found chromedriver at: {potential_path}")
            return potential_path

    return None


def _do_apply_leave(default_config: dict, apply_data: dict, driver: WebDriver) -> None:
    """
    根據提供的默認配置和申請數據，自動提交請假申請。

    參數:
    default_config (dict): 包含默認配置的字典。
    apply_data (dict): 包含申請數據的字典。

    返回:
    None
    """
    submit_form_id = default_config["submit_form_id"]
    submit_button_id = default_config["submit_button_id"]
    base_url = default_config["base_url"]

    url = base_url + "/viewform" + "?" + "&".join([f"{key}={value}" for key, value in apply_data.items()])

    # options = webdriver.ChromeOptions()
    # for option in default_config["browser_options"].split(","):
    #     options.add_argument(option)

    try:
        # with webdriver.Chrome(options) as driver:
        driver.get(url)

        form = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, submit_form_id))
        )
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, submit_button_id))
        )

        button.click()

        WebDriverWait(driver, 10).until(
            EC.url_changes(url + "/formResponse")
        )

        params = "\n".join([f"{key}={value}" for key, value in apply_data.items()])
        _logger.info(f"Send request successfully with params: \n {params}")
    except Exception as e:
        _logger.error(f"Error occurred: {e}")
        _logger.error(traceback.print_exc())
    finally:
        driver.quit()


def _valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except:
        raise argparse.ArgumentTypeError(f"Not a valid date: '{s}'.")


def _waiting_to_run(execute_date: datetime) -> None:
    """
    等待到指定的執行日期
    :param 日期:
    :return:
    """

    def get_ntp_time():
        """
        Get the NTP time
        :return: NTP time
        """
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org')
        return datetime.strptime(ctime(response.tx_time), "%a %b %d %H:%M:%S %Y")

    now = get_ntp_time()
    delta = (execute_date - now).total_seconds()

    if delta <= 0:
        print(f"Target date is expired: {execute_date}")
        return

    for i in tqdm(range(int(delta)), desc="Waiting time for auto-apply execution", unit="s",
                  bar_format="{desc}: {remaining}"):
        time.sleep(1)


def _pre_load_driver(default_config: dict, chromedriver_url_str: str = None) -> webdriver:
    """
    載入具有默認配置的webdriver
    參數:
    default_config (dict): 默認配置字典
    返回:
    webdriver.Chrome: 已初始化的webdriver對象
    """
    _logger.info("Pre-load the webdriver.")

    try:
        options = webdriver.ChromeOptions()
        for option in default_config["browser_options"].split(","):
            options.add_argument(option)

        driver = webdriver.Remote(chromedriver_url_str, options=options) if chromedriver_url_str else webdriver.Chrome(
            service=Service(_find_chromedriver()), options=options)
    except Exception as e:
        _logger.error(f"Error occurred while initializing the webdriver: {e}")
        _logger.error(traceback.print_exc())
        raise

    return driver


def main():
    global _logger
    config_path = None
    _logger = _init_log()

    # 建立解析器
    parser = argparse.ArgumentParser(description='AutoApply - Command line arguments')

    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--config", "-c", type=str, help="Path to the configuration file")
    parser.add_argument("--execute_date", "-d", type=_valid_date, help="Date in the format: 'YYYY-MM-DD HH:MM:SS'")

    # remote chrome driver
    parser.add_argument('--driver-url', type=str, help='Remote WebDriver URL')
    parser.add_argument('--driver-port', type=str, help='Remote WebDriver Port')

    args = parser.parse_args()

    if (args.driver_url is None) != (args.driver_port is None):
        parser.error('the url and port must be provided together')

    # load config file
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.curdir + os.sep + "config.ini"

    default_config, apply_data = _load_config(config_path)

    if args.dry_run:
        _logger.info("Dry run mode is enabled.")
        _verify_webdriver()
        sys.exit(0)

    # do the auto apply process
    if args.driver_url and args.driver_port:
        driver = _pre_load_driver(default_config, f"http://{args.driver_url}:{args.driver_port}")
    else:
        driver = _pre_load_driver(default_config)

    if args.execute_date:
        _waiting_to_run(args.execute_date)

    _do_apply_leave(default_config, apply_data, driver)


if __name__ == '__main__':
    main()
