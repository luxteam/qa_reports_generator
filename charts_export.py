import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
from PIL import Image
from common import Projects, ChartType

JIRA_AMD_HOST = os.getenv("JIRA_AMD_HOST", "amdrender.atlassian.net")
JIRA_AMD_USERNAME = os.environ["JIRA_AMD_USERNAME"]
JIRA_AMD_PASSWORD = os.environ["JIRA_AMD_PASSWORD"]

projects_chart_names = {
    Projects.MAYA_RPR: {
        ChartType.UNRESOLVED_ISSUES: "Pie Chart: Maya RPR Unresolved",
        ChartType.ISSUES_UPDATES_2W: "Pie Chart: Maya RPR 2 weeks",
    },
    Projects.MAYA_USD: {
        ChartType.UNRESOLVED_ISSUES: "MAYA USD: UNRESOLVED ISSUES",
        ChartType.ISSUES_UPDATES_2W: "MAYA USD: ISSUES UPDATES IN 2 WEEKS",
    },
    Projects.BLENDER_RPR: {
        ChartType.UNRESOLVED_ISSUES: "Pie Chart: Blender RPR Unresolved",
        ChartType.ISSUES_UPDATES_2W: "Pie Chart: Blender RPR 2 weeks",
    },
    Projects.BLENDER_USD: {
        ChartType.UNRESOLVED_ISSUES: "BLENDER USD: UNRESOLVED ISSUES",
        ChartType.ISSUES_UPDATES_2W: "BLENDER USD: ISSUES UPDATES IN 2 WEEKS",
    },
    # Projects.SOLIDWORKS: {
    #     ChartType.UNRESOLVED_ISSUES: "Pie Chart: SOLIDWORKS unresolved issues",
    #     ChartType.ISSUES_UPDATES_2W: "Pie Chart: Solidworks issues updates in 2 weeks",
    # },
    Projects.HOUDINI: {
        ChartType.UNRESOLVED_ISSUES: "Pie Chart: HOUDINI: UNRESOLVED ISSUES",
        ChartType.ISSUES_UPDATES_2W: "Pie Chart: HOUDINI: ISSUE UPDATES IN 2 WEEKS",
    },
}


def login(driver: webdriver.Firefox):
    driver.get("https://id.atlassian.com/login")
    driver.find_element(By.ID, "username").send_keys(JIRA_AMD_USERNAME)
    sleep(1)  # to avaid bot protection
    driver.find_element(By.ID, "login-submit").click()

    while not driver.find_elements(By.ID, "password"):
        sleep(1)

    sleep(4)

    driver.find_element(By.ID, "password").send_keys(JIRA_AMD_PASSWORD)
    sleep(4)  # to avaid bot protection
    driver.find_element(By.ID, "login-submit").click()

    # waiting for main page to load
    while not driver.find_elements(By.TAG_NAME, "button"):
        sleep(1)

    sleep(2)


def export_charts():
    driver = webdriver.Firefox(executable_path="./geckodriver.exe")
    # driver.fullscreen_window()
    driver.set_window_size(1920,1080)

    login(driver)

    driver.get(f"https://{JIRA_AMD_HOST}/jira/dashboards/10322")

    # wait for charts to render
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, "//h1[text()='QA report']"))
    )

    result_report = {
        project: {ChartType.UNRESOLVED_ISSUES: None, ChartType.ISSUES_UPDATES_2W: None}
        for project in projects_chart_names
    }

    for project in projects_chart_names:
        for chart_type in projects_chart_names[project]:
            chart_name = projects_chart_names[project][chart_type]

            # check wheter chart is available
            chart_not_available = driver.find_elements(
                By.XPATH,
                "//div[text()='{chart_name}']//ancestor::div[6]//descendant::div[contains(text(), 'No Data Available')]".format(
                    chart_name=chart_name
                ),
            )

            if chart_not_available:
                continue

            # find chart
            chart_el = None
            try:
                chart_el = driver.find_element(
                    By.XPATH,
                    "//div[text()='{chart_name}']//ancestor::div[6]//descendant::div[@class='piechart-with-legend']".format(
                        chart_name=chart_name
                    ),
                )
            except Exception:
                sleep(5)
                chart_el = driver.find_element(
                    By.XPATH,
                    "//div[text()='{chart_name}']//ancestor::div[6]//descendant::div[@class='piechart-with-legend']".format(
                        chart_name=chart_name
                    ),
                )

            # screen chart box
            sleep(1)
            img_name = "pics/chart_{project}_{type}.png".format(
                project=project.value, type=chart_type.value
            )
            chart_el.screenshot(img_name)

            # crop screenshot
            img = Image.open(img_name)
            box = (150, 0, img.width - 160, img.height)
            img.crop(box).save(img_name)

            result_report[project][chart_type] = img_name

    driver.close()

    return result_report


if __name__ == "__main__":
    export_charts()
