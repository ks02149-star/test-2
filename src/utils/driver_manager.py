import os
import subprocess

def setup_chrome_options():
    from selenium.webdriver.chrome.options import Options
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage') # Memory Leak countermeasure
    options.add_argument('--disable-gpu')
    options.add_argument('--js-flags="--max-old-space-size=256"') # Limit V8 JS engine memory
    options.add_argument('--window-size=1920x1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return options

def kill_zombie_chromes():
    try:
        # Only kill chromedriver processes to avoid killing user's personal chrome.exe
        subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], capture_output=True)
    except Exception:
        pass
