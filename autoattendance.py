from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key, dotenv_values
import getpass
import os
import datetime
import yaml
from pathlib import Path
import time


KEY_FILE = "secret.key"
ENV_FILE = Path(".env")
CLASSROOM_FILE = "classroom_schedule.yaml"
CONFIG_FILE = "config.yaml"


def generate_key():
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def load_key():
    if not os.path.exists(KEY_FILE):
        return generate_key()
    with open(KEY_FILE, "rb") as f:
        return f.read()


def encrypt_password(password, key):
    return Fernet(key).encrypt(password.encode()).decode()


def decrypt_password(encrypted_password, key):
    return Fernet(key).decrypt(encrypted_password.encode()).decode()


def load_config(path=CONFIG_FILE):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_attendance_windows(config):
    windows = {}

    start_hour = config["period_config"]["start_hour"]
    period_duration = config["period_config"]["period_duration_minutes"]
    buffer = config["period_config"]["attendance_buffer_minutes"]
    period_count = config["period_config"]["period_count"]

    for i in range(period_count):
        period_number = i + 1
        start_minutes = start_hour * 60 + i * period_duration
        window_start = start_minutes - buffer
        window_end = start_minutes + buffer
        windows[period_number] = (window_start, window_end)

    return windows


def load_schedule_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_current_period_by_attendance_window(config):
    now = datetime.datetime.now()
    minutes_now = now.hour * 60 + now.minute
    attendance_windows = generate_attendance_windows(config)

    for period, (start, end) in attendance_windows.items():
        if start <= minutes_now <= end:
            return period
    return None


def get_current_class(schedule, config):
    now = datetime.datetime.now()
    weekday = now.strftime("%a")
    period = get_current_period_by_attendance_window(config)

    if period is None:
        return None

    today_classes = schedule.get(weekday, [])
    for cls in today_classes:
        if period in cls["periods"]:
            return cls
    return None


def login_by_selenium(username, password, classroom):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 5)

    try:
        driver.get(
            "https://attendance.is.it-chiba.ac.jp/attendance/class_room/" + classroom
        )

        username_field = wait.until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="userid"]'))
        )
        password_field = wait.until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="password"]'))
        )

        username_field.send_keys(username)
        password_field.send_keys(password)

        login_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/form/div/div/button"))
        )
        login_button.click()

        try:
            already_attended_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div/div/form/button[@disabled]")
                )
            )
            if already_attended_button:
                print("You have already attended this class.")
                time.sleep(5)
                return

        except TimeoutException:
            pass

        attendance_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="attend"]'))
        )
        attendance_button.click()

        confirm_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="ok_confirmModal"]'))
        )
        confirm_button.click()

        wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="close_completeModal"]'))
        )
        print("Now you are attending the class.")

    finally:
        driver.quit()


if __name__ == "__main__":
    load_dotenv(dotenv_path=ENV_FILE)
    key = load_key()
    config = load_config(CONFIG_FILE)
    current_env = dotenv_values(dotenv_path=ENV_FILE)

    username = os.getenv("USERNAME")
    encrypted_password = os.getenv("PASSWORD")

    schedule = load_schedule_yaml(CLASSROOM_FILE)
    current_class = get_current_class(schedule, config)

    if not username:
        username = input("Enter your username: ")
        set_key(ENV_FILE, "USERNAME", username)

    raw_password = None
    if encrypted_password:
        try:
            raw_password = decrypt_password(encrypted_password, key)
        except Exception:
            print("Failed to decrypt saved password. Please enter it again.")

    if not raw_password:
        raw_password = getpass.getpass(prompt="Enter your password: ")
        encrypted_password = encrypt_password(raw_password, key)
        set_key(ENV_FILE, "PASSWORD", encrypted_password)

    if current_class:
        default_classroom = current_class.get("classroom", "")
        user_input = input(
            f"Classroom: [{default_classroom}] (press Enter to accept or type to override): "
        )
        classroom = user_input.strip() if user_input.strip() else default_classroom
    else:
        classroom = input("Could not detect classroom. Please enter manually: ").strip()

    login_by_selenium(username, raw_password, classroom)
