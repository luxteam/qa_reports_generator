import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from jenkins_export import get_wml_report_link
from PIL import Image


JENKINS_HOST = os.getenv("JENKINS_HOST", "rpr.cis.luxoft.com")
JENKINS_USERNAME = os.environ["JENKINS_USERNAME"]
JENKINS_TOKEN = os.environ["JENKINS_PASSWORD"]


def login(driver: webdriver.Firefox, wml_rep_url: str):
    driver.get(wml_rep_url)
    driver.find_element(By.ID, "j_username").send_keys(JENKINS_USERNAME)
    driver.find_element(By.ID, "j_password").send_keys(JENKINS_TOKEN)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    # waiting for report page to load
    while not driver.find_elements(By.XPATH, "//span[text()='Allure']"):
        sleep(1)


def _save_chart_screenshot(driver):
    # # check wheter chart is available
    chart_is_available = driver.find_elements(
        By.XPATH,
        "//div[@class='widgets-grid__col']"
    )

    if not chart_is_available:
        return None

    # find chart
    chart_el = driver.find_element(
        By.XPATH,
        "//div[@class='widgets-grid__col']"
    )

    # screen chart box
    img_name = "pics/wml_chart.png"
    chart_el.screenshot(img_name)

    # crop screenshot
    img = Image.open(img_name)
    box = (10, 5, img.width, img.height-500)
    img.crop(box).save(img_name)

    return img_name


def export_wml_chart():
    driver = webdriver.Firefox(executable_path="./geckodriver.exe")
    driver.set_window_size(1920,1080)

    report_link = get_wml_report_link()
    login(driver, report_link)

    # wait for chart to render
    sleep(2) # animation on the circle chart

    img_path = _save_chart_screenshot(driver)

    driver.close()

    return img_path


if __name__ == "__main__":
    export_wml_chart()
