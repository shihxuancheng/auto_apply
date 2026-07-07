## Project Overview

This project is a Python command-line tool named "Auto Apply" that automates the process of filling out and submitting a Google Form. It is designed to be used for tasks such as applying for leave, where the form submission needs to happen at a specific time. The tool uses Playwright for web automation, `ntplib` for accurate time synchronization, and `apscheduler` for scheduling the submission.

The application is configured through a `config.ini` file, which stores details about the Google Form, user data, and other settings. It can be executed immediately or scheduled to run at a future date and time.

## Building and Running

### Dependencies

The project's dependencies are managed using `uv` (with `pyproject.toml` and `uv.lock`).

**Main Dependencies:**
*   `playwright`: For browser automation.
*   `tqdm`: For progress bars.
*   `ntplib`: For network time protocol synchronization.
*   `apscheduler`: For scheduling tasks.
*   `typer`: For command-line argument parsing.

**Development Dependencies:**
*   `pytest`, `pytest-asyncio`, `pytest-mock`: For testing.
*   `ruff`: For linting and formatting.

### Setup and Building

First, synchronize the dependencies and set up the virtual environment:

```bash
uv sync
```

To install the Playwright chromium browser driver:

```bash
uv run playwright install chromium
```

The project can be built into a wheel package using `uv build` or the `build` tool:

```bash
uv build
```

### Running

The tool is run using `uv run`.

*   **Show Help:**

    ```bash
    uv run auto-apply --help
    ```

*   **Dry Run (to verify Playwright browser logic):**

    ```bash
    uv run auto-apply --dry-run
    ```

*   **Immediate Execution:**

    ```bash
    uv run auto-apply
    ```

*   **Scheduled Execution:**

    ```bash
    uv run auto-apply -d "YYYY-MM-DD HH:MM:SS"
    ```

*   **Custom Configuration Path:**

    ```bash
    uv run auto-apply -c /path/to/config.ini
    ```

## Development Conventions

*   **Configuration:** The application uses a `config.ini` file for configuration. A `config-sample.ini` is provided as a template.
*   **Logging:** The script uses the `logging` module to log information to both the console and a file (`auto_apply.log`).
*   **Command-line Arguments:** The `typer` library is used to handle command-line arguments (e.g., `--dry-run`, `--config`/`-c`, `--execute_date`/`-d`, `--version`/`-v`).
*   **Schedules:** The `schedule/` directory contains OS-specific scheduler templates for long-term scheduling (macOS launchd, Windows Task Scheduler, and Linux Cron).
*   **Testing:** The project uses `pytest` for testing. Run tests with `uv run pytest`. Unit tests are marked as `unit` and integration tests (which run the real browser) are marked as `integration`.
