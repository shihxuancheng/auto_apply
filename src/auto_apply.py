import argparse
import asyncio
import configparser
import logging
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
target_url = None

# Constants
WAIT_TIMEOUT = 10000  # Playwright uses milliseconds


async def wait_and_find_element(page: Page, selector: str, timeout: int = WAIT_TIMEOUT):
    """Wait and find an element"""
    return await page.wait_for_selector(selector, timeout=timeout)


async def wait_and_click_button(page: Page, selector: str, timeout: int = WAIT_TIMEOUT):
    """Wait and click a button"""
    button = await page.wait_for_selector(selector, state='visible', timeout=timeout)
    await button.click()


def _init_log() -> logging.Logger:
    # Set log format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create file handler
    log_path = os.path.join(os.path.curdir, "auto_apply.log")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def _load_config(config_file: str) -> tuple:
    """
    Load configuration file and return config data.
    """
    try:
        _logger.info(f"Loading config file: {config_file}")
        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        default_config = dict(config.items("default"))
        apply_data = dict(config.items("apply_data"))
        return default_config, apply_data
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        _logger.error(f"Error reading config file: {e}")
        sys.exit(1)
    except Exception as e:
        _logger.error(f"Error occurred: {e}")
        _logger.error(traceback.format_exc())
        raise


async def _verify_playwright() -> None:
    """
    Verify if Playwright is installed correctly.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
        _logger.info("Playwright is installed correctly.")
    except Exception as e:
        _logger.error(f"Error occurred: {e}")
        _logger.error(traceback.format_exc())
        raise


async def _pre_load_form(page: Page, submit_form_id: str) -> None:
    """Pre-load the form page"""
    try:
        current_url = page.url
        if current_url != target_url:
            _logger.info(f"Currently URL: {current_url}")
            _logger.info(f"Navigating to: {target_url}")
            await page.goto(target_url)

        # Confirm the form has loaded
        await wait_and_find_element(page, f"#{submit_form_id}")
        _logger.info("Form pre-loaded successfully")

    except PlaywrightTimeoutError:
        _logger.error("Timeout waiting for element")
        raise
    except Exception as e:
        _logger.error(f"Error pre-loading form: {e}")
        _logger.error(traceback.format_exc())
        raise


async def _do_apply_leave(page: Page, submit_button_id: str, apply_data: dict) -> None:
    """Execute the leave application submission"""
    try:
        # Click the submit button
        await wait_and_click_button(page, f"#{submit_button_id}")

        # Wait for page navigation
        await page.wait_for_url(f"{target_url.split('?')[0]}/formResponse", timeout=WAIT_TIMEOUT)

        # Log success message
        params = "\n".join([f"{key}={value}" for key, value in apply_data.items()])
        _logger.info(f"Leave application submitted successfully, parameters:\n{params}")

        await asyncio.sleep(1)  # Delay to ensure form submission is processed

    except PlaywrightTimeoutError:
        _logger.error("Timeout waiting for element")
    except Exception as e:
        _logger.error(f"Error submitting form: {e}")
        _logger.error(traceback.format_exc())
    finally:
        await page.browser.close()


def _valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid date: '{s}'.")


def _get_ntp_time(ntp_server: str = None) -> datetime:
    """
    Get NTP time.
    """
    try:
        client = ntplib.NTPClient()
        ntp_server_addr = ntp_server or 'pool.ntp.org'
        response = client.request(ntp_server_addr)
        return datetime.fromtimestamp(response.tx_time)
    except Exception as e:
        _logger.error(f"Failed to get NTP time: {e}")
        _logger.error(traceback.format_exc())
        return datetime.now()


async def scheduled_job(p: Playwright, browser_options: dict, driver_url: str, default_config: dict, apply_data: dict):
    browser = await _pre_load_browser(p, browser_options, driver_url)
    page = await browser.new_page()
    try:
        await _pre_load_form(page, default_config["submit_form_id"])
        await _do_apply_leave(page, default_config["submit_button_id"], apply_data)
    except Exception as e:
        _logger.error(f"Error during scheduled job: {e}")
        _logger.error(traceback.format_exc())
    finally:
        await browser.close()


async def _waiting_to_run(execute_date: datetime, default_config, apply_data, browser_options, driver_url) -> None:
    """
    Use APScheduler to execute the task at the specified NTP time.
    """
    pre_launch_time = float(default_config.get('prelaunch_time', 0.1))

    # Get current NTP time
    current_ntp_time = _get_ntp_time(default_config.get('ntp_server'))
    _logger.info(f"Target execution time: {execute_date}")
    _logger.info(f"Current NTP time: {current_ntp_time}")

    # Check if the time has already passed
    if current_ntp_time > execute_date:
        _logger.error("The specified execution time has already passed.")
        return

    # Calculate the difference between NTP time and local time
    local_time = datetime.now()
    ntp_local_diff = (current_ntp_time - local_time).total_seconds()
    _logger.info(f"Time difference (NTP - local): {ntp_local_diff:.3f} seconds")

    # Adjust execution time considering the difference
    adjusted_execute_date = execute_date - timedelta(seconds=ntp_local_diff) - timedelta(
        seconds=pre_launch_time)

    scheduler = AsyncIOScheduler()
    async with async_playwright() as p:
        scheduler.add_job(
            scheduled_job,
            trigger=DateTrigger(run_date=adjusted_execute_date),
            id='apply_leave_job',
            args=[p, browser_options, driver_url, default_config, apply_data]
        )

        try:
            _logger.info(
                f"Task scheduled, pre-launching: {pre_launch_time} seconds, will run at {adjusted_execute_date}")
            scheduler.start()
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            _logger.info("Task scheduling cancelled.")
        except Exception as e:
            _logger.error(f"Error during scheduling: {e}")
            _logger.error(traceback.format_exc())
            scheduler.shutdown()


async def _pre_load_browser(playwright: Playwright, browser_options: dict, driver_url: str = None) -> Browser:
    """
    Load the browser with default configurations.
    """
    _logger.info("Pre-loading the browser.")
    try:
        if driver_url:
            browser = await playwright.chromium.connect(driver_url, **browser_options)
        else:
            browser = await playwright.chromium.launch(**browser_options)
    except Exception as e:
        _logger.error(f"Error occurred while initializing the browser: {e}")
        _logger.error(traceback.format_exc())
        raise

    return browser


async def main():
    global _logger, target_url
    _logger = _init_log()

    parser = argparse.ArgumentParser(
        description='AutoApply - Command line arguments',
        epilog='Version 0.0.7 - A tool to automate leave applications with Playwright'
    )

    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--config", "-c", type=str, help="Path to the configuration file")
    parser.add_argument("--execute_date", "-d", type=_valid_date,
                        help="Date in 'YYYY-MM-DD HH:MM:SS' format")
    parser.add_argument("--version", "-v", action="store_true", help="Show version information")
    parser.add_argument('--driver-url', type=str, help='Remote WebDriver URL')
    parser.add_argument('--driver-port', type=str, help='Remote WebDriver Port')

    args = parser.parse_args()

    if args.version:
        print("AutoApply version 0.0.7")
        sys.exit(0)

    if (args.driver_url is None) != (args.driver_port is None):
        parser.error('the url and port must be provided together')

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
    if "browser_options" in default_config:
        for option in default_config["browser_options"].split(","):
            option = option.strip()
            if option == "--headless":
                browser_options["headless"] = True
            elif option == "--no-sandbox":
                # Playwright does not need this option
                pass
            elif "=" in option:
                key, value = option.split("=", 1)
                browser_options[key.strip()] = value.strip()

    driver_url = f"http://{args.driver_url}:{args.driver_port}" if args.driver_url and args.driver_port else None

    target_url = f"{default_config['base_url']}/viewform?{'&'.join([f'{k}={v}' for k, v in apply_data.items()])}"

    if args.execute_date:
        await _waiting_to_run(args.execute_date, default_config, apply_data, browser_options, driver_url)
    else:
        _logger.info("No execution time specified, running immediately.")
        async with async_playwright() as p:
            browser = await _pre_load_browser(p, browser_options, driver_url)
            page = await browser.new_page()
            try:
                await _pre_load_form(page, default_config["submit_form_id"])
                await _do_apply_leave(page, default_config["submit_button_id"], apply_data)
            except Exception as e:
                _logger.error(f"Error during execution: {e}")
                _logger.error(traceback.format_exc())
            finally:
                await browser.close()


if __name__ == '__main__':
    asyncio.run(main())