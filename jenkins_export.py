import os
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from typing import Dict
import json
from urllib.parse import urljoin
from lxml import etree
from common import Projects


JENKINS_HOST = os.getenv("JENKINS_HOST", "rpr.cis.luxoft.com")
JENKINS_USERNAME = os.environ["JENKINS_USERNAME"]
JENKINS_TOKEN = os.environ["JENKINS_TOKEN"]

PROJECT_TO_JOB_MAPPING: Dict[Projects, Dict[str, str]] = {
    Projects.MAYA_RPR: {"default": "job/RPR-MayaPlugin-Weekly"},
    Projects.BLENDER_RPR: {"default": "job/RPR-BlenderPlugin-Weekly"},
    Projects.MAYA_USD: {"default": "job/USD-MayaPlugin-Weekly"},
    Projects.BLENDER_USD: {"default": "job/USD-BlenderPlugin-Weekly"},
    Projects.RENDER_STUDIO: {"default": "job/RenderStudio-Weekly"},
    Projects.HOUDINI: {"default": "job/USD-HoudiniPlugin-Weekly"},
    Projects.HDRPR: {"default": "job/HdRPR-Weekly"},
    Projects.MATERIALX: {"default": "job/MaterialXvsHdRPR-Weekly"},
    Projects.SOLIDWORKS: {},
    Projects.INVENTOR: {"default": "job/USD-Viewer-Weekly"},
    Projects.RPRHYBRID: {},
}


def _get_latest_build(project_path: str) -> dict:
    return requests.get(
        f"https://{JENKINS_HOST}/{project_path}/api/json?tree=lastBuild[*]",
        auth=HTTPBasicAuth(JENKINS_USERNAME, JENKINS_TOKEN),
    ).json()


def _get_latest_build_date(build_data: dict) -> str:
    return datetime.fromtimestamp(
        build_data["lastBuild"]["timestamp"] / 1000.0
    ).strftime("%d-%b-%Y")


def _get_latest_report_link(build_data: dict) -> str:
    latest_build_page = requests.get(
        build_data["lastBuild"]["url"],
        auth=HTTPBasicAuth(JENKINS_USERNAME, JENKINS_TOKEN),
    ).text

    # report link can have different ending, e.g. Test_20Report or Test_20Report_20Northstar
    # however, it always contains 'Test_20Report'
    html_parser = BeautifulSoup(latest_build_page, "html.parser")
    return (
        "https://"
        + JENKINS_HOST
        + html_parser.select_one("a[href*=Test_20Report]")["href"]
    )


def _get_latest_build_version(project_config: str, build_data: dict) -> str:
    description = build_data["lastBuild"]["description"]

    dom = etree.HTML(description)

    if dom.xpath("//*[@id='version-major']"):
        major = dom.xpath("//*[@id='version-major']")[0].text.strip()
        minor = dom.xpath("//*[@id='version-minor']")[0].text.strip()
        patch = dom.xpath("//*[@id='version-patch']")[0].text.strip()
        return f"{major}.{minor}.{patch}"
    else:
        return project_config


def _get_latest_build_status(build_data: dict) -> str:
    return build_data["lastBuild"]["result"]


def get_latest_build_data(project: Projects) -> dict:
    results = {}

    for project_config, project_path in PROJECT_TO_JOB_MAPPING[project].items():
        project_data = {}

        latest_build_data = _get_latest_build(project_path)

        project_data["date"] = _get_latest_build_date(latest_build_data)
        project_data["link"] = _get_latest_report_link(latest_build_data)
        project_data["version"] = _get_latest_build_version(
            project_config, latest_build_data
        )
        project_data["status"] = _get_latest_build_status(latest_build_data)

        results[project_config] = project_data

    return results


def get_wml_report_link():
    project_path = "job/WML-Weekly"
    latest_build = _get_latest_build(project_path)
    return urljoin(latest_build["lastBuild"]["url"], "allure")


if __name__ == "__main__":
    for key in PROJECT_TO_JOB_MAPPING.keys():
        print(json.dumps(get_latest_build_data(key), indent=4))

    print("WML :))))))))")
    print("Report link: {link}".format(link=get_wml_report_link()))
    # get_allure_summary_board()
