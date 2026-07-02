import os
import subprocess
import re

def patch_chromedriver(driver_path):
    try:
        with open(driver_path, 'rb') as f:
            content = f.read()
        patched = content.replace(b'cdc_', b'dog_')
        if patched != content:
            with open(driver_path, 'wb') as f:
                f.write(patched)
    except Exception:
        pass

def setup_chrome_options(headless=True):
    from selenium.webdriver.chrome.options import Options
    options = Options()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--window-position=-32000,-32000')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage') # Memory Leak countermeasure
    options.add_argument('--disable-gpu')
    options.add_argument('--js-flags="--max-old-space-size=256"') # Limit V8 JS engine memory
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--hide-crash-restore-bubble')
    options.add_argument('--disable-crash-reporter')
    options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Disable Google Smart Lock, Password Manager, and Sign-in popups
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "signin.allowed_on_next_startup": False,
        "profile.exit_type": "Normal"
    }
    options.add_experimental_option("prefs", prefs)
    
    return options

def kill_zombie_chromes():
    try:
        # Only kill chromedriver processes to avoid killing user's personal chrome.exe
        subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], capture_output=True)
        subprocess.run(['taskkill', '/F', '/IM', 'chromedriver_patched.exe'], capture_output=True)
    except Exception:
        pass
