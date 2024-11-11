import configparser, logging, argparse, os, traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

dry_run_mode = False
logger = None


def init_log() -> logging.Logger:
    # 設定日誌格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 建立日誌記錄器
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # 建立文件處理器
    file_handler = logging.FileHandler(os.path.dirname(__file__) + "/auto_apply.log")
    file_handler.setFormatter(formatter)

    # 建立控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 將處理器添加到日誌記錄器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def load_config(config_file: str) -> tuple:
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
        logger.info(f"load config file: {config_file}")

        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        # load leave application data
        default_config = {key: config.get("default", key) for key in config.options("default")}
        apply_data = {key: config.get("apply_data", key) for key in config.options("apply_data")}

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"default_config: {default_config}")
            logger.debug(f"apply_data: {apply_data}")

        return default_config, apply_data
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        logger.error(traceback.print_exc())
        raise


def verify_webdriver() -> None:
    """
    驗證webdriver是否正確安裝
    """
    try:
        driver = webdriver.Chrome()
        driver.quit()
        logger.info("Webdriver is installed correctly.")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        logger.error(traceback.print_exc())
        raise

def do_apply_leave(default_config: dict, apply_data: dict) -> None:
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

    options = webdriver.ChromeOptions()
    for option in default_config["browser_options"].split(","):
        options.add_argument(option)

    try:
        with webdriver.Chrome(options) as driver:
            driver.get(url)

            form = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, submit_form_id))
            )
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, submit_button_id))
            )

            button.click()

            WebDriverWait(driver, 10).until(
                EC.url_matches(url + "/formResponse")
            )

            params = "\n".join([f"{key}={value}" for key, value in apply_data.items()])
            logger.info(f"Send request successfully with params: \n {params}")
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        logger.error(traceback.print_exc())


def main():
    global dry_run_mode
    global logger
    config_path = None
    logger = init_log()

    # 建立解析器
    parser = argparse.ArgumentParser(description='AutoApply - Command line arguments')

    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--config", type=str, help="Path to the configuration file")

    args = parser.parse_args()

    if args.dry_run:
        logger.setLevel(logging.DEBUG)
        logger.info("Dry run mode is enabled.")
        dry_run_mode = True

    # load config file
    if args.config:
        config_path = args.config
    else:
        config_path = os.path.dirname(__file__) + "\config.ini"

    default_config, apply_data = load_config(config_path)

    if dry_run_mode:
        verify_webdriver()

    # do the auto apply process
    if not dry_run_mode:
        do_apply_leave(default_config, apply_data)


if __name__ == '__main__':
    main()
