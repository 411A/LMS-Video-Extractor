# SBU LMS Video Downloader

💡 Note: This repository’s docs, examples, and source code were AI-assisted; engineering, testing, and final integration were done by me.

💡 توجه (فارسی): این مخزن — شامل مستندات، نمونه‌ها و کد منبع — با کمک مدل‌های هوش مصنوعی تولید شده است. مهندسی، تست و ادغام نهایی توسط من انجام شده است.

This production-ready Python script logs into Shahid Beheshti University (SBU) LMS (and other **Moodle**-based LMSs), iterates through available courses, finds offline `.rar` lecture packages, downloads them, and extracts organized `.mp4` files. It includes robust logging, retry logic, and a small JSON database to avoid re-processing already-extracted files.
It also automatically renames and sorts files based on the class session's date and time.

این اسکریپت پایتون آماده، وارد سامانه‌ی آموزشی دانشگاه شهید بهشتی (SBU) — و سایر سامانه‌های مبتنی بر **Moodle** — می‌شود، دروس در دسترس را پیدا کرده و بسته‌های آفلاین با فرمت `.rar` مربوط به جلسات درسی را پیدا می‌کند، آن‌ها را دانلود کرده و فایل‌های `.mp4` استخراج‌شده و سازمان‌یافته را ذخیره می‌کند. این ابزار شامل ثبت لاگ قوی، منطق تلاش مجدد (retry) و یک پایگاه‌داده‌ی کوچک JSON برای جلوگیری از پردازش مجدد فایل‌های از پیش استخراج‌شده است.
این برنامه همچنین به‌صورت خودکار، فایل‌ها را براساس تاریخ و ساعت برگزاری کلاس درس مرتب می‌کند.

**Example Output**:
```
.
├── 5578_داده‌كاوي
│   ├── 01_1404-07-26_15-10.mp4
│   ├── 02_1404-07-27_15-09.mp4
│   ├── 03_1404-08-03_15-10.mp4
│   └── 04_1404-08-04_15-07.mp4
├── 5579_الگوريتم‌هاي_تركيبياتي
│   ├── 01_1404-07-26_10-00.mp4
│   ├── 02_1404-07-28_09-59.mp4
│   ├── 03_1404-08-03_10-03.mp4
│   └── 04_1404-08-05_10-04.mp4
├── 5582_الگوريتم_هاي_پيشرفته
│   ├── 01_1404-07-27_10-11.mp4
│   ├── 02_1404-07-29_10-06.mp4
│   ├── 03_1404-08-04_10-06.mp4
│   └── 04_1404-08-06_10-04.mp4
└── 5585_سمينار

4 directories, 12 files
```

<details>
  <summary>🇬🇧 English</summary>

  ## Overview
  This repository contains `main.py`, an automation tool that:
  - Logs into `https://lms.sbu.ac.ir` using Playwright.
  - Enumerates courses and finds `onlineclass` modules with offline `.rar` recordings.
  - Downloads `.rar` packages, extracts contained `.mp4` files, and saves them into per-course folders.
  - Tracks progress with `downloaded.json` to avoid redundant downloads/extractions.

  ## Features
  - Process all courses or a single course by `course_id`.
  - Organizes MP4s into folders named `"<course_id>_<sanitized_course_name>"`.
  - Resilient downloads with retries and Playwright's download API.
  - Automatic `.rar` extraction (uses `7z` or `unrar` on PATH).
  - Persists state in `downloaded.json` and supports migrating earlier simple formats.
  - Configurable via `.env` or CLI arguments.
  - Reasonable error handling and logging.

  ## Requirements
  - Python 3.8+ (3.10+ recommended and tested).

  ## Quick Setup — Fully Automated (recommended)
  This is the recommended flow: fully automates login, downloading, and extraction.

  ### Prerequisites
  - Python 3.8+ (3.10+ recommended).
  - Install Python packages:
    ```bash
    pip install playwright pydantic-settings
    ```
  - Install Playwright browsers:
    ```bash
    playwright install
    ```
  - Install an extractor tool:
    - Windows: 7-Zip — https://www.7-zip.org/
    - Linux / macOS: `unrar` (install via your package manager, e.g. `sudo apt install unrar`)

  ### Usage examples
  ```bash
  # Process all courses (will prompt for username/password if not provided)
  python main.py --username 404345123 --password 005566778

  # Process a single course
  python main.py --username 404345123 --password 005566778 --course_id 165057

  # Run in headless mode
  python main.py --username 404345123 --password 005566778 --headless true
  ```

  ### CLI options (high level)
  - `--username` — LMS username (overrides .env)
  - `--password` — LMS password (overrides .env)
  - `--course_id` — Process a specific course by id (optional)
  - `--output_dir` — Directory to save extracted MP4 files (default: `extracted`)
  - `--headless` — Run browser in headless mode (true/false)

  - Packages (install with pip):
    ```bash
    pip install playwright pydantic-settings
    ```
    After installing Playwright:
    ```bash
    playwright install
    ```
  - `7z` (p7zip / 7-Zip) or `unrar` available in PATH for extraction.
  - On Windows: install 7-Zip or WinRAR and ensure `7z.exe` or `unrar.exe` is accessible.

  ## Files
  - `main.py` — main script (async, Playwright-based).
  - `.env` — optional environment variables (not included).
  - `downloaded.json` — local DB of processed `rars` and `mp4s`.
  - `downloads/` — temporary download storage (configurable).
  - `extracted/` (or `OUTPUT_DIR`) — output MP4 folders.

  ## Quickstart — Usage
  Basic examples:
  ```bash
  # Process all courses (will prompt for username/password if not provided)
  python main.py --username 404345123 --password 005566778

  # Process a single course
  python main.py --username 404345123 --password 005566778 --course_id 165057

  # Run in headless mode
  python main.py --username 404345123 --password 005566778 --headless true
  ```
  If username/password not passed via CLI, the script uses `.env` (via `pydantic-settings`) or interactively prompts you. Password prompt uses a secure input.

  ## Configuration (example `.env`)
  Create a `.env` in the same folder (UTF-8):
  ```
  LMS_USERNAME=404345123
  LMS_PASSWORD=005566778
  OUTPUT_DIR=extracted
  DOWNLOADS_DIR=downloads
  HEADLESS=False
  TIMEOUT_PAGE_LOAD=180000
  DOWNLOAD_TIMEOUT=3600000
  LOG_LEVEL=INFO
  ```
  Notes:
  - `HEADLESS` accepts boolean values (`True`, `False`, `true`, `false`).
  - Timeouts are in milliseconds.

  ## How it works (high level)
  1. Launch Playwright Chromium context with `accept_downloads=True`.
  2. Log in to LMS via the username/password form.
  3. Navigate to the user's courses page and collect `data-course-id` attributes and the visible course name (sanitizing it).
  4. For each course, open the course page and search for the `onlineclass` module link to get `onlineclass_id`.
  5. Open the recordings page (`action=recording.list`), find list items containing the Persian word `آفلاین` and parse the `.rar` download link and the Persian date/time in parentheses.
  6. Download `.rar` using Playwright download API, save into `downloads/<folder>/`.
  7. Extract `.rar` using `7z` or `unrar` into a temp dir, move the first `.mp4` found into the final `extracted/<folder>/` path.
  8. Append to `downloaded.json` (`rars` and `mp4s`) to avoid re-processing.

  ## Filename generation & parsing
  - Filenames follow the pattern: `NN_YYYY-MM-DD_hh-mm.rar` where `NN` is an index in the recording list.
  - The parser understands Persian month names and periods like `صبح/ظهر/عصر/شب` and applies a simple `PERIOD_OFFSET`.
  - Course folder name sanitized by `sanitize_filename()` to avoid illegal characters and control chars.

  ## `downloaded.json` format
  New format (default):
  ```json
  {
    "12345_Course_Name": {
      "rars": ["01_1404-07-12_10-30.rar", ...],
      "mp4s": ["01_1404-07-12_10-30.mp4", ...],
      "download_folder": "downloads/12345_Course_Name",
      "extract_folder": "extracted/12345_Course_Name"
    }
  }
  ```
  Migration: if an older format `{ "folder": ["mp4s", ...] }` is detected, the script will migrate it to the new richer format.



  ## Manual Steps (Legacy)
  These steps are for legacy/manual workflows, kept for reference.

  1. Read and run `main.py` (legacy script name; primary script now is `main.py`).
  2. Move all `.rar` files into a single folder, e.g. `all/`.
  3. On WSL2/Linux/macOS, run an extractor script (example `extractor.sh`) to extract all RARs to MP4s:
     ```bash
     # Example (replace with the real extractor script if available)
     ./extractor.sh all/ extracted/
     ```
  Note: The fully automated flow (`main.py`) covers these manual steps automatically (download + extract). Use manual flow only if automation is not possible for your environment.


  ## Troubleshooting
  - **Login fails**: check credentials, SBU may require additional MFA or non-standard login flows; the script expects a username/password form available at `/login/index.php`.
  - **Playwright errors / no browsers**: run `playwright install`.
  - **Extraction fails**: ensure `7z` or `unrar` is installed and present in PATH. On Windows, script also tries common install locations.
  - **No `.mp4` found inside RAR**: inspect the rar manually — sometimes package structure varies or they may include nested containers.
  - **Permissions**: ensure the process can write to `downloads` and `extracted` folders.
  - **Timeouts**: increase `TIMEOUT_PAGE_LOAD` or `DOWNLOAD_TIMEOUT` via `.env` or CLI flags.
  - **Duplicate/partial files**: If a download failed mid-extract, remove the incomplete files from `downloads/<folder>` and re-run. `downloaded.json` may need manual edit if inconsistencies occur.

  ## Logging
  - Default logs are output to stdout. Change `LOG_LEVEL` in `.env` (e.g., `DEBUG`) to get more verbose output.

  ## Security & Privacy
  - Credentials: Do not commit `.env` with credentials to version control. The script can accept interactive prompts to avoid storing secrets.
  - Compliance: Confirm you have permission from your institution to download course recordings. Respect copyright and privacy of instructors and classmates.

  ## Improvements & TODOs
  - Support for MFA / SSO if the LMS uses federated login.
  - More robust parsing for non-standard HTML/markup variations.
  - Parallel extraction worker pool (currently extraction is serial per download completion).
  - Option to choose between keeping `.rar` files or deleting them after successful extraction.

  ## Contributing
  - Fixes, improvements, and bug reports are welcome. Please open issues or PRs. Include logs and minimal reproduction steps.

  ## License
  MIT License — adapt as needed.

  ## Contact
  For questions or help, include logs and the output of `python --version` and `pip show playwright pydantic-settings` when reporting issues.

</details>

<details>
  <summary>🇮🇷 فارسی</summary>

  ## خلاصه
  این پروژه شامل `main.py` است که به‌صورت خودکار وارد LMS دانشگاه شهید بهشتی می‌شود، دوره‌ها را پیدا می‌کند، بسته‌های آفلاین (`.rar`) را دانلود و محتوای `mp4.` را استخراج و در فولدرهایی منظم ذخیره می‌کند. وضعیت دانلودها در `downloaded.json` ثبت می‌شود تا از دانلود مجدد جلوگیری شود.

  ## ویژگی‌ها
  - پردازش همه دوره‌ها یا یک دورهٔ مشخص با `course_id`.
  - استخراج خودکار RAR با استفاده از `7z` یا `unrar`.
  - ثبت فایل‌های دانلودشده و استخراج‌شده در `downloaded.json`.
  - پیکربندی از طریق `.env` یا پارامترهای CLI.
  - مدیریت لاگ و امکان بالا بردن سطح لاگ برای دیباگ.

  ## پیش‌نیازها
  - Python 3.10 یا بالاتر.
  - بسته‌ها:
    ```bash
    pip install playwright pydantic-settings
    playwright install
    ```
  - ابزار استخراج: `7z` یا `unrar` در PATH نصب شده باشد. (ویندوز: نصب 7-Zip یا WinRAR و دسترسی به `7z.exe` یا `unrar.exe`)

  ## ساختار فایل‌ها
  - `main.py` — اسکریپت اصلی.
  - `.env` — تنظیمات (اختیاری).
  - `downloaded.json` — پایگاه‌دادهٔ محلی وضعیت دانلودها.
  - `downloads/` — محل دانلود فایل‌های RAR.
  - `extracted/` — محل نهایی فایل‌های MP4.

  ## راه‌اندازی سریع — مثال‌ها
  ```bash
  # پردازش همه دوره‌ها
  python main.py --username 404345123 --password 005566778

  # پردازش یک دوره مشخص
  python main.py --username 404345123 --password 005566778 --course_id 165057

  # اجرای headless
  python main.py --username 404345123 --password 005566778 --headless true
  ```
  اگر نام کاربری/رمز عبور وارد نشوند، اسکریپت ابتدا از `.env` استفاده می‌کند و در صورت لزوم کاربر را به‌صورت تعاملی درخواست می‌کند. ورودی رمز به‌صورت امن (بدون اکو) گرفته می‌شود.

  ## نمونه `.env`
  ```
  LMS_USERNAME=404345123
  LMS_PASSWORD=005566778
  OUTPUT_DIR=extracted
  DOWNLOADS_DIR=downloads
  HEADLESS=False
  TIMEOUT_PAGE_LOAD=180000
  DOWNLOAD_TIMEOUT=3600000
  LOG_LEVEL=INFO
  ```

  ## روند کار (خلاصه)
  1. اجرای Playwright و باز کردن مرورگر با `accept_downloads=True`.
  2. لاگین روی `/login/index.php`.
  3. دریافت لیست دوره‌ها از صفحهٔ دوره‌های کاربر و استخراج `data-course-id` و نام درس (پس از پاک‌سازی).
  4. باز کردن صفحهٔ هر دوره و یافتن ماژول `onlineclass` برای دریافت `onlineclass_id`.
  5. باز کردن صفحهٔ ضبط‌ها (`action=recording.list`) و جستجوی آیتم‌های حاوی `آفلاین`.
  6. دانلود رِر با API دانلود Playwright و ذخیره در `downloads/<folder>/`.
  7. استخراج RAR با `7z` یا `unrar` و انتقال اولین فایل MP4 به `extracted/<folder>/`.
  8. بروزرسانی `downloaded.json` با موارد جدید.

  ## قالب `downloaded.json`
  قالب جدید:
  ```json
  {
    "12345_Course_Name": {
      "rars": ["01_1404-07-12_10-30.rar"],
      "mp4s": ["01_1404-07-12_10-30.mp4"],
      "download_folder": "downloads/12345_Course_Name",
      "extract_folder": "extracted/12345_Course_Name"
    }
  }
  ```

  ## رفع اشکال (Troubleshooting)
  - **خطای لاگین**: اعتبارنامه‌ها را بررسی کنید؛ اگر سامانه از ورود یکپارچه/SSO استفاده می‌کند یا MFA لازم دارد، لازم است روند لاگین افزوده یا دستی انجام شود.
  - **مشکل Playwright / مرورگرها نصب نشده**: `playwright install` را اجرا کنید.
  - **عدم استخراج RAR**: اطمینان حاصل کنید `7z` یا `unrar` نصب و در PATH است. در ویندوز مسیرهای متداول به‌صورت پشتیبانی شده بررسی می‌شوند.
  - **فایل MP4 پیدا نشد**: بسته را دستی باز کنید چون ساختار داخلی ممکن است متفاوت باشد.
  - **مجوزهای فایل**: اطمینان حاصل کنید اسکریپت دسترسی نوشتن در پوشه‌ها را دارد.
  - **تایم‌اوت‌ها**: پارامترهای `TIMEOUT_PAGE_LOAD` و `DOWNLOAD_TIMEOUT` را در `.env` یا CLI افزایش دهید.

  ## نکات امنیتی و حقوقی
  - اطلاعات ورود را در سیستم کنترل نسخه قرار ندهید.
  - قبل از دانلود هر محتوایی از LMS، مطمئن شوید اجازهٔ لازم (قانونی و اخلاقی) را دارید.

  ## توسعه و قابلیت‌های پیشنهادی
  - پشتیبانی از MFA/SSO.
  - بهبود parser برای حالت‌های HTML مختلف.
  - حذف خودکار فایل‌های RAR پس از استخراج یا انتخاب بین نگه داشتن/حذف.
  - worker pool برای استخراج موازی.

  ## مشارکت
  اشکال‌ها و PRها خوش‌آمد هستند؛ لطفاً لاگ‌ها و نسخهٔ پایتون و ورژن بسته‌ها را همراه گزارش قرار دهید.

  ## مجوز
  MIT — در صورت نیاز تغییر دهید.

  ## تماس
  برای کمک، هنگام ارسال issue لاگ‌ها، نسخهٔ Python و خروجی `pip show playwright pydantic-settings` را ضمیمه کنید.

</details>
