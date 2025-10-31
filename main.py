'''
Complete automation script for downloading and extracting offline videos from Shahid Beheshti University (SBU) LMS.
This script automates login, navigation, downloading .rar files, and extracting them to .mp4 files.
Production-ready with error handling, logging, and minimal manual intervention.

Features:
- Processes all courses or a specific course
- Organizes MP4 files in folders named after course names
- Prevents redundant downloads using a JSON database

Usage:
    python main.py --username 404345123 --password 005566778 --course_id 165057
    python main.py --username 404345123 --password 005566778  # Process all courses

If course_id is not provided, it will process all courses.
'''

import re
import asyncio
import argparse
import logging
import tempfile
import subprocess
import shutil
import platform
import json
from typing import Optional
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page
from pydantic_settings import BaseSettings



BASE_URL = "https://lms.sbu.ac.ir"
LOGIN_URL = f"{BASE_URL}/login/index.php"


PERIOD_OFFSET = {
    'صبح': 0,
    'ظهر': 12,
    'عصر': 12,
    'شب': 12
}

PERSIAN_MONTHS = {
    'فروردین': '01',
    'اردیبهشت': '02',
    'خرداد': '03',
    'تیر': '04',
    'مرداد': '05',
    'شهریور': '06',
    'مهر': '07',
    'آبان': '08',
    'آذر': '09',
    'دی': '10',
    'بهمن': '11',
    'اسفند': '12',
}

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Settings loader using pydantic
class Settings(BaseSettings):
    LMS_USERNAME: Optional[str] = None
    LMS_PASSWORD: Optional[str] = None
    OUTPUT_DIR: str = "extracted"
    HEADLESS: bool = False
    DOWNLOADS_DIR: str = "downloads"
    TIMEOUT_PAGE_LOAD: int = 180000
    DOWNLOAD_TIMEOUT: int = 3600000
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def prompt_if_none(val, prompt_text, is_password=False):
    if val:
        return val
    if is_password:
        import getpass
        return getpass.getpass(prompt_text)
    return input(prompt_text)


async def login(page: Page, username: str, password: str) -> None:
    """Automate login."""
    logger.info("Navigating to login page...")
    await page.goto(LOGIN_URL, timeout=TIMEOUT_PAGE_LOAD)
    
    # Wait for login form
    await page.wait_for_selector('input[name="username"]', timeout=10000)
    
    # Fill credentials
    await page.fill('input[name="username"]', username)
    await page.fill('input[name="password"]', password)
    
    # Click the login button
    await page.click('#loginbtn')
    
    # Wait for navigation or check if login successful
    await page.wait_for_load_state('networkidle', timeout=TIMEOUT_PAGE_LOAD)
    
    # Check if login failed
    if "login" in page.url.lower():
        raise Exception("Login failed. Please check credentials.")
    
    logger.info("Login successful.")


async def get_course_ids(page: Page) -> list[tuple[str, str, str]]:
    """Get list of (course_id, course_name, onlineclass_id) from the courses page."""
    courses_url = f"{BASE_URL}/my/courses.php"
    logger.info(f"Navigating to courses page: {courses_url}")
    await page.goto(courses_url, timeout=TIMEOUT_PAGE_LOAD)
    await page.wait_for_load_state('networkidle', timeout=TIMEOUT_PAGE_LOAD)

    logger.info("Querying course elements on courses page...")
    course_elements = await page.query_selector_all('div[data-course-id]')
    logger.info(f"Found {len(course_elements)} course elements.")
    
    # First, collect course_id and course_name without navigating
    course_list = list()
    for idx, elem in enumerate(course_elements, 1):
        try:
            course_id = await elem.get_attribute('data-course-id')
            logger.info(f"[{idx}] Extracted course_id: {course_id}")
            if course_id:
                # Find the anchor with class 'aalink coursename'
                anchor = await elem.query_selector('a.aalink.coursename')
                if anchor:
                    # Get all child nodes, ignore sr-only spans
                    # Get all spans with class 'sr-only' inside anchor
                    sr_only_spans = await anchor.query_selector_all('span.sr-only')
                    sr_only_texts = set()
                    for span in sr_only_spans:
                        txt = (await span.text_content()) or ""
                        sr_only_texts.add(txt.strip())
                    # Get all child nodes (text nodes and spans)
                    # Use regex to extract all text nodes not inside sr-only spans
                    # This is robust for Playwright, but if you want to use JSHandle, you can use anchor.evaluate
                    # For now, let's use text_content and remove unwanted phrases
                    anchor_text = (await anchor.text_content()) or ""
                    anchor_text = anchor_text.strip()
                    # Remove all sr-only texts and unwanted phrases
                    for unwanted in list(sr_only_texts) + ["درس ستاره‌دار شده است", "نام درس"]:
                        anchor_text = anchor_text.replace(unwanted, "")
                    # Remove parentheses and their contents
                    course_name = re.sub(r'\([^)]*\)', '', anchor_text)
                    # Remove all digits
                    course_name = re.sub(r'\d+', '', course_name)
                    # Remove extra whitespace
                    course_name = re.sub(r'\s+', ' ', course_name).strip()
                    # Replace spaces with underscores
                    course_name = course_name.replace(' ', '_')
                    course_name = sanitize_filename(course_name)
                    logger.info(f"[{idx}] Extracted course_name: '{course_name}'")
                else:
                    course_name = f"Course_{course_id}"
                    logger.warning(f"[{idx}] Could not find anchor for course name, using fallback: {course_name}")
                # Format folder name as course_id_course_name
                folder_name = f"{course_id}_{course_name}"
                logger.info(f"[{idx}] Folder name: {folder_name}")
                course_list.append((course_id, folder_name))
        except Exception as e:
            logger.error(f"[{idx}] Error extracting course info: {e}")
    
    # Now, for each course, navigate to get onlineclass_id
    courses = list()
    for idx, (course_id, course_name) in enumerate(course_list, 1):
        try:
            course_page_url = f"{BASE_URL}/course/view.php?id={course_id}"
            logger.info(f"[{idx}] Navigating to course page: {course_page_url}")
            await page.goto(course_page_url, timeout=TIMEOUT_PAGE_LOAD)
            await page.wait_for_load_state('networkidle', timeout=TIMEOUT_PAGE_LOAD)
            onlineclass_link = await page.query_selector('a[href*="/mod/onlineclass/view.php?id="]')
            onlineclass_id = None
            if onlineclass_link:
                href = await onlineclass_link.get_attribute('href')
                logger.info(f"[{idx}] Found onlineclass link: {href}")
                if href:
                    m = re.search(r'/mod/onlineclass/view\.php\?id=(\d+)', href)
                    if m:
                        onlineclass_id = m.group(1)
                        logger.info(f"[{idx}] Extracted onlineclass_id: {onlineclass_id}")
            if onlineclass_id:
                courses.append((course_id, course_name, onlineclass_id))
            else:
                logger.warning(f"[{idx}] No onlineclass module found for course {course_id} ({course_name})")
        except Exception as e:
            logger.error(f"[{idx}] Error extracting onlineclass_id for course {course_id}: {e}")
    
    logger.info(f"Found {len(courses)} courses with onlineclass modules.")
    return courses


async def process_course(context: BrowserContext, course_id: str, downloads_dir: Path, course_dir: Path, downloaded: dict, folder_name: str, onlineclass_id: str) -> None:
    """Process recordings for a single course."""
    logger.info(f"Processing course {course_id} ({folder_name})...")
    
    # Initialize downloaded entry for the course if not present
    if folder_name not in downloaded:
        downloaded[folder_name] = {
            "rars": [],
            "mp4s": [],
            "download_folder": str(downloads_dir / folder_name),
            "extract_folder": str(course_dir)
        }
        save_downloaded(downloaded)
    
    page = await context.new_page()
    try:
        # Use the correct onlineclass_id for recordings
        recording_url = f"{BASE_URL}/mod/onlineclass/view.php?id={onlineclass_id}&action=recording.list"
        logger.info(f"Navigating to recording list: {recording_url}")
        await page.goto(recording_url, timeout=TIMEOUT_PAGE_LOAD)
        await page.wait_for_load_state('networkidle', timeout=TIMEOUT_PAGE_LOAD)

        # Locate list
        logger.info("Locating recording list...")
        await page.wait_for_selector("ul:has(li:nth-child(3))", timeout=10000)
        uls = await page.query_selector_all("ul:has(li:nth-child(3))")
        if len(uls) < 2:
            logger.warning(f"Recording list not found for course {course_id}.")
            return
        lis = await uls[1].query_selector_all('li')
        # Filter only lis that contain an offline link
        valid_lis = list()
        for li in lis:
            li_html = await li.inner_html()
            if 'آفلاین' in li_html:
                valid_lis.append(li)
        logger.info(f"Found {len(valid_lis)} valid offline recordings to process for course {course_id}.")

        if not valid_lis:
            logger.warning(f"No offline recordings found for course {course_id}. Skipping.")
            return

        # Process each valid recording
        tasks = list()
        for idx, li in enumerate(valid_lis, start=1):
            li_html = await li.inner_html()
            result = await parse_li(li_html, idx)
            if not result:
                continue
            href, filename = result
            mp4_filename = filename.replace('.rar', '.mp4')
            if mp4_filename in downloaded[folder_name]["mp4s"]:
                logger.info(f"Already extracted: {mp4_filename}")
                continue
            tasks.append(download_and_extract(context, href, filename, downloads_dir, course_dir, downloaded, folder_name, mp4_filename))

        # Run downloads concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Completed processing course {course_id}.")

    except Exception as e:
        logger.error(f"Error processing course {course_id}: {e}")
    finally:
        await page.close()


async def parse_li(li_html: str, idx: int) -> Optional[tuple[str, str]]:
    """Extract offline link, index, and datetime from li HTML."""
    logger.debug(f"Parsing item #{idx}...")
    href_m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>[^<]*آفلاین', li_html)
    if not href_m:
        logger.warning(f"No offline link in item #{idx}.")
        return None
    href = href_m.group(1)

    # find the datetime parentheses containing a Persian month
    all_parens = re.findall(r"\(([^)]+)\)", li_html)
    dt_parts = None
    for part in all_parens:
        if any(mon in part for mon in PERSIAN_MONTHS):
            dt_parts = [p.strip() for p in part.split('،')]
            break
    if not dt_parts or len(dt_parts) < 3:
        logger.warning(f"Could not find valid datetime in item #{idx}, parens={all_parens}")
        return None
    date_part, time_part = dt_parts[1], dt_parts[2]

    # parse date
    d_m = re.search(r"(\d+)\s+(\S+)\s+(\d+)", date_part)
    if not d_m:
        logger.warning(f"Date parse failed in #{idx}, date_part={date_part}")
        return None
    day, mon_name, year = d_m.groups()
    mon = PERSIAN_MONTHS.get(mon_name, '00')

    # parse time
    t_m = re.search(r"(\d+):(\d+)\s+(\S+)", time_part)
    if not t_m:
        logger.warning(f"Time parse failed in #{idx}, time_part={time_part}")
        return None
    hour, minute, period = t_m.groups()
    h = (int(hour) % 12) + PERIOD_OFFSET.get(period, 0)

    idx_str = f"{idx:02d}"
    date_str = f"{year}-{mon}-{int(day):02d}"
    time_str = f"{h:02d}-{int(minute):02d}"
    filename = f"{idx_str}_{date_str}_{time_str}.rar"
    logger.debug(f"href={href}, filename={filename}")
    return href, filename


def extract_rar(rar_path: Path, output_dir: Path) -> Path:
    """Extract .rar file to output directory and return the .mp4 file path."""
    base_name = rar_path.stem
    expected_mp4 = output_dir / f"{base_name}.mp4"
    
    if expected_mp4.exists():
        logger.info(f"MP4 already exists: {expected_mp4}")
        return expected_mp4
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"Extracting {rar_path} to temp dir...")
        system = platform.system()
        success = False
        if system == "Windows":
            seven_zip = shutil.which("7z") or (r"C:\\Program Files\\7-Zip\\7z.exe" if Path(r"C:\\Program Files\\7-Zip\\7z.exe").exists() else None)
            unrar_exe = shutil.which("unrar") or (r"C:\\Program Files\\WinRAR\\WinRAR.exe" if Path(r"C:\\Program Files\\WinRAR\\WinRAR.exe").exists() else None)
            if seven_zip:
                if subprocess.run([seven_zip, "x", str(rar_path), f"-o{tmpdir}", "-y"], capture_output=True).returncode == 0:
                    success = True
            if not success and unrar_exe:
                if subprocess.run([unrar_exe, "x", "-y", str(rar_path), tmpdir], capture_output=True).returncode == 0:
                    success = True
        else:
            # Unix-like: try 7z and unrar from PATH
            seven_zip = shutil.which("7z")
            unrar_exe = shutil.which("unrar")
            if seven_zip:
                if subprocess.run([seven_zip, "x", str(rar_path), f"-o{tmpdir}", "-y"], capture_output=True).returncode == 0:
                    success = True
            if not success and unrar_exe:
                # On Unix, unrar syntax: unrar x -y rarfile destdir
                if subprocess.run([unrar_exe, "x", "-y", str(rar_path), tmpdir], capture_output=True).returncode == 0:
                    success = True
        if not success:
            raise Exception(f"Failed to extract {rar_path}. Ensure 7z or unrar is installed and in PATH.")
        # Find the .mp4 file
        mp4_files = list(Path(tmpdir).rglob('*.mp4'))
        if not mp4_files:
            raise Exception(f"No .mp4 file found in {rar_path}")
        if len(mp4_files) > 1:
            logger.warning(f"Multiple MP4 files found in {rar_path}, using first: {mp4_files[0]}")
        mp4_path = mp4_files[0]
        shutil.move(mp4_path, expected_mp4)
        logger.info(f"Extracted and renamed to: {expected_mp4}")
        return expected_mp4


async def download_and_extract(context: BrowserContext, href: str, filename: str, downloads_dir: Path, extracted_dir: Path, downloaded: dict, folder_name: str, mp4_filename: str) -> None:
    """Download a .rar file and extract it."""
    (downloads_dir / folder_name).mkdir(parents=True, exist_ok=True)
    rar_path = downloads_dir / folder_name / filename
    
    if (extracted_dir / mp4_filename).exists():
        logger.info(f"MP4 already exists for {filename}, skipping.")
        if mp4_filename not in downloaded[folder_name]["mp4s"]:
            downloaded[folder_name]["mp4s"].append(mp4_filename)
            save_downloaded(downloaded)
        return
    
    logger.info(f"Downloading {filename}...")
    max_retries = 3
    for attempt in range(max_retries):
        dl_page = await context.new_page()
        try:
            async with dl_page.expect_download(timeout=DOWNLOAD_TIMEOUT) as download_info:
                await dl_page.goto(href, timeout=TIMEOUT_PAGE_LOAD)
                await dl_page.click("a:has-text('MP4')")
            download = await download_info.value
            await download.save_as(rar_path)
            logger.info(f"Downloaded to: {rar_path}")
            break  # Success
        except Exception as e:
            logger.warning(f"Download attempt {attempt + 1} failed for {filename}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to download {filename} after {max_retries} attempts.")
                raise
        finally:
            await dl_page.close()
    
    # Update downloaded.json with RAR download
    if filename not in downloaded[folder_name]["rars"]:
        downloaded[folder_name]["rars"].append(filename)
        save_downloaded(downloaded)
    
    # Extract immediately
    extract_rar(rar_path, extracted_dir)
    
    # Add to downloaded if successful
    if (extracted_dir / mp4_filename).exists():
        if mp4_filename not in downloaded[folder_name]["mp4s"]:
            downloaded[folder_name]["mp4s"].append(mp4_filename)
            save_downloaded(downloaded)


def sanitize_filename(name: str) -> str:
    """Sanitize string to be a valid filename/directory name."""
    # Replace invalid characters for Windows filenames
    invalid_chars = '<>:"|?*\\'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Remove control characters (ASCII 0-31)
    name = ''.join(c for c in name if ord(c) >= 32)
    # Replace multiple whitespace with single space
    name = re.sub(r'\s+', ' ', name.strip())
    return name


def load_downloaded() -> dict:
    """Load downloaded files database."""
    path = Path('downloaded.json')
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Migrate old format {folder: [mp4s]} to new {folder: {"rars": [], "mp4s": mp4s, ...}}
        if data and isinstance(next(iter(data.values()), None), list):
            migrated = dict()
            for folder, mp4s in data.items():
                migrated[folder] = {
                    "rars": [],  # Assume rars downloaded if mp4s exist
                    "mp4s": mp4s,
                    "download_folder": "",
                    "extract_folder": ""
                }
            return migrated
        return data
    return {}


def save_downloaded(downloaded: dict) -> None:
    """Save downloaded files database."""
    path = Path('downloaded.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(downloaded, f, ensure_ascii=False, indent=2)


def str_to_bool(v):
    """Convert string to boolean for argparse."""
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


async def main() -> None:
    # Load settings from .env and allow override by CLI
    settings = Settings()
    parser = argparse.ArgumentParser(description="Download and extract SBU LMS videos.")
    parser.add_argument('--username', help='Your LMS username (overrides .env)')
    parser.add_argument('--password', help='Your LMS password (overrides .env)')
    parser.add_argument('--course_id', help='Course ID for recordings (optional, if not provided, process all courses)')
    parser.add_argument('--output_dir', default=settings.OUTPUT_DIR, help='Output directory for MP4 files')
    parser.add_argument('--headless', type=str_to_bool, default=settings.HEADLESS, help='Run browser in headless mode (true/false)')

    args = parser.parse_args()

    # Use CLI args if provided, else .env, else prompt
    username = args.username or settings.LMS_USERNAME
    password = args.password or settings.LMS_PASSWORD
    username = prompt_if_none(username, 'Enter your LMS username: ')
    password = prompt_if_none(password, 'Enter your LMS password: ', is_password=True)

    # Use .env or CLI for custom directories and timeouts
    downloads_dir = Path(getattr(settings, 'DOWNLOADS_DIR', 'downloads'))
    downloads_dir.mkdir(parents=True, exist_ok=True)
    output_dir = Path(args.output_dir or getattr(settings, 'OUTPUT_DIR', 'extracted'))
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = load_downloaded()

    # Set timeouts from settings
    global TIMEOUT_PAGE_LOAD, DOWNLOAD_TIMEOUT
    TIMEOUT_PAGE_LOAD = getattr(settings, 'TIMEOUT_PAGE_LOAD', 180000)
    DOWNLOAD_TIMEOUT = getattr(settings, 'DOWNLOAD_TIMEOUT', 3600000)

    # Set log level from settings
    import logging
    log_level = getattr(settings, 'LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))


    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            await login(page, username, password)

            course_infos = await get_course_ids(page)

            if args.course_id:
                # Process single course
                found = False
                for cid, cname, onlineclass_id in course_infos:
                    if cid == args.course_id:
                        course_dir = output_dir / cname
                        course_dir.mkdir(parents=True, exist_ok=True)
                        await process_course(context, cid, downloads_dir, course_dir, downloaded, cname, onlineclass_id)
                        found = True
                        break
                if not found:
                    raise Exception(f"Course {args.course_id} not found")
            else:
                # Process all courses
                for course_id, course_name, onlineclass_id in course_infos:
                    course_dir = output_dir / course_name
                    course_dir.mkdir(parents=True, exist_ok=True)
                    await process_course(context, course_id, downloads_dir, course_dir, downloaded, course_name, onlineclass_id)

            save_downloaded(downloaded)
            logger.info("All downloads and extractions completed.")

        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
