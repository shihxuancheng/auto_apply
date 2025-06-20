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
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.date import DateTrigger
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_logger = None
target_url = None

# 常量定義
WAIT_TIMEOUT = 10


def wait_and_find_element(driver: WebDriver, by: By, value: str, timeout: int = WAIT_TIMEOUT):
    """等待並查找元素"""
    return WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
                  and EC.presence_of_element_located((by, value))
    )


def wait_and_click_button(driver: WebDriver, selector: str, timeout: int = WAIT_TIMEOUT):
    """等待並點擊按鈕"""
    button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    button.click()


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
    """ 在系統中搜尋並定位 ChromeDriver 的可執行文件。
        此函數使用三種不同的方法來尋找 ChromeDriver：
        1. 使用 shutil.which() 在系統 PATH 中搜尋
        2. 檢查預定義的常見安裝路徑
        3. 遍歷整個系統 PATH 環境變量

        Returns:
            str | None: 如果找到 ChromeDriver，返回其完整路徑；如果未找到，返回 None
    """

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


def _pre_load_form(default_config: dict, driver: WebDriver) -> None:
    """預先載入表單頁面"""
    try:
        if driver.current_url != target_url:
            _logger.info(f"Currently URL: {driver.current_url}")
            _logger.info(f"預先連線至: {target_url}")
            driver.get(target_url)

        # 確認表單已載入
        wait_and_find_element(driver, By.ID, default_config["submit_form_id"])
        _logger.info("表單預載入成功")

    except TimeoutException:
        _logger.error("等待元素超時")
        raise
    except Exception as e:
        _logger.error(f"預載入表單時發生錯誤：{e}")
        _logger.error(traceback.format_exc())
        raise


def _do_apply_leave(default_config: dict, apply_data: dict, driver: WebDriver) -> None:
    """執行請假申請提交動作"""
    try:
        # 點擊提交按鈕
        wait_and_click_button(driver, default_config["submit_button_id"])

        # 等待頁面跳轉
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
                      and EC.url_changes(target_url + "/formResponse")
        )

        # 記錄成功信息
        params = "\n".join([f"{key}={value}" for key, value in apply_data.items()])
        _logger.info(f"請假申請提交成功，參數：\n{params}")

        time.sleep(1)  # FIXME 若不放delay，有時送出表單不被接受，原因不明

    except TimeoutException:
        _logger.error("等待元素超時")
    except ElementClickInterceptedException:
        _logger.error("無法點擊提交按鈕")
    except Exception as e:
        _logger.error(f"提交表單時發生錯誤：{e}")
        _logger.error(traceback.format_exc())
    finally:
        driver.quit()


def _valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except:
        raise argparse.ArgumentTypeError(f"Not a valid date: '{s}'.")


def _get_ntp_time(ntp_server: None) -> datetime:
    """
    獲取 NTP 時間
    :return: NTP 時間
    """
    try:
        client = ntplib.NTPClient()
        # 從配置文件讀取 NTP 服務器，如果未設置則使用默認值
        ntp_server_addr = 'pool.ntp.org'
        if ntp_server:
            ntp_server_addr = ntp_server
        response = client.request(ntp_server_addr)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as e:
        _logger.error(f"獲取 NTP 時間失敗: {e}")
        _logger.error(traceback.format_exc())
        return datetime.now()


def _waiting_to_run(execute_date: datetime) -> None:
    """
    使用 APScheduler 在指定 NTP 時間執行任務
    :param execute_date: 指定執行時間
    """
    global driver, target_url, default_config, apply_data

    try:
        # 預先載入表單
        _pre_load_form(default_config, driver)
    except Exception as e:
        _logger.error(f"預載入表單失敗: {e}")
        return

    # 獲取當前 NTP 時間
    current_ntp_time = _get_ntp_time(default_config['ntp_server'])

    _logger.info(f"當前 NTP 時間: {current_ntp_time}")
    _logger.info(f"目標 執行時間: {execute_date}")

    # 檢查時間是否已過期
    if current_ntp_time > execute_date:
        _logger.error("指定的執行時間已過期")
        return

    scheduler = BlockingScheduler()

    # 设置全局变量以控制程序退出
    job_done = False

    def scheduled_job():
        nonlocal job_done
        try:
            # 執行請假操作
            _do_apply_leave(default_config, apply_data, driver)
        except Exception as e:
            _logger.error(f"執行任務時發生錯誤: {e}")
            _logger.error(traceback.format_exc())
        finally:
            # 标记任务已完成
            job_done = True

            # 使用单独的线程安全地关闭调度器和退出程序
            def safe_shutdown():
                scheduler.shutdown(wait=False)
                _logger.info("任務已完成，程序結束")
                # 强制退出程序
                os._exit(0)

            # 启动关闭线程
            threading.Thread(target=safe_shutdown).start()

    # 计算 NTP 时间与本地时间的差异
    local_time = datetime.now()
    ntp_local_diff = (current_ntp_time - local_time).total_seconds()

    # 调整执行时间，考虑本地时间与 NTP 时间的差异
    adjusted_execute_date = execute_date - timedelta(seconds=ntp_local_diff)

    # 添加主要任務，使用調整後的執行時間
    job = scheduler.add_job(
        scheduled_job,
        trigger=DateTrigger(run_date=adjusted_execute_date),
        id='apply_leave_job'
    )

    # 每 60 秒重新同步一次 NTP 時間並調整執行時間
    def time_sync_job():
        nonlocal current_ntp_time, adjusted_execute_date
        new_ntp_time = _get_ntp_time()
        time_drift = (new_ntp_time - current_ntp_time).total_seconds()

        if abs(time_drift) > 1:  # 如果時間差異大於1秒，則重新調整
            current_ntp_time = new_ntp_time
            adjusted_execute_date = current_ntp_time + (execute_date - current_ntp_time)

            # 重新計算執行時間，並更新排程任務
            try:
                if job and scheduler.get_job(job.id):  # 檢查任務是否還存在
                    new_time_diff = (execute_date - current_ntp_time).total_seconds()
                    if new_time_diff > 0:
                        job.reschedule(trigger=DateTrigger(run_date=adjusted_execute_date))
                        _logger.info(f"NTP 時間同步: {current_ntp_time}")
                        _logger.info(f"時間漂移: {time_drift:.3f} 秒")
                        _logger.info(f"任務已重新排程至: {adjusted_execute_date}")
                    else:
                        _logger.error("重新排程時發現執行時間已過期")
                        scheduler.shutdown()
            except Exception as e:
                _logger.error(f"重新排程時發生錯誤: {e}")

    # 添加 NTP 時間同步任務
    # scheduler.add_job(
    #     time_sync_job,
    #     'interval',
    #     seconds=60,
    #     id='ntp_sync_job',
    #     next_run_time=datetime.now()
    # )

    try:
        _logger.info(f"任務已排程，將在 {adjusted_execute_date} 執行")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        _logger.info("任務排程已取消")
    except Exception as e:
        _logger.error(f"排程過程中發生錯誤: {e}")
        _logger.error(traceback.format_exc())
        scheduler.shutdown()


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

        chrome_log_path = f"{os.curdir}{os.sep}chromedrver-{date.today()}.log"
        driver = webdriver.Remote(chromedriver_url_str, options=options) if chromedriver_url_str else webdriver.Chrome(
            service=Service(_find_chromedriver(), log_output=chrome_log_path), options=options)
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
    parser = argparse.ArgumentParser(
        description='AutoApply - Command line arguments',
        epilog='Version 0.0.4 - A tool to automate leave applications'
    )

    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--config", "-c", type=str, help="Path to the configuration file")
    parser.add_argument("--execute_date", "-d", type=_valid_date, help="Date in the format: 'YYYY-MM-DD HH:MM:SS'")
    parser.add_argument("--version", "-v", action="store_true", help="Show version information")

    # remote chrome driver
    parser.add_argument('--driver-url', type=str, help='Remote WebDriver URL')
    parser.add_argument('--driver-port', type=str, help='Remote WebDriver Port')

    args = parser.parse_args()

    if args.version:
        print("AutoApply version 0.0.4")
        sys.exit(0)

    if (args.driver_url is None) != (args.driver_port is None):
        parser.error('the url and port must be provided together')

    # load config file
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.curdir + os.sep + "config.ini"

    global default_config, apply_data
    default_config, apply_data = _load_config(config_path)

    if args.dry_run:
        _logger.info("Dry run mode is enabled.")
        _verify_webdriver()
        sys.exit(0)

    # do the auto apply process
    global driver
    if args.driver_url and args.driver_port:
        driver = _pre_load_driver(default_config, f"http://{args.driver_url}:{args.driver_port}")
    else:
        driver = _pre_load_driver(default_config)

    global target_url
    target_url = default_config["base_url"] + "/viewform" + "?" + "&".join(
        [f"{key}={value}" for key, value in apply_data.items()]
    )
    # _logger.info(f"Target URL: {target_url}")

    if args.execute_date:
        # 有指定執行時間，使用排程執行
        _waiting_to_run(args.execute_date)
    else:
        # 沒有指定執行時間，立即執行
        try:
            _logger.info("未指定執行時間，立即執行")
            _pre_load_form(default_config, driver)
            _do_apply_leave(default_config, apply_data, driver)
        except Exception as e:
            _logger.error(f"執行過程發生錯誤: {e}")
            _logger.error(traceback.format_exc())
            if driver:
                driver.quit()


if __name__ == '__main__':
    main()
