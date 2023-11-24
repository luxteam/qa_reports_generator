import os
import requests
import json
from datetime import datetime, timedelta
from common import Projects, Link
from http import HTTPStatus

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

projects_info = {
    Projects.MAYA_RPR: {
        "owner": "GPUOpen-LibrariesAndSDKs",
        "name": "RadeonProRenderMayaPlugin",
    },
    Projects.MAYA_USD: {
        "owner": "GPUOpen-LibrariesAndSDKs",
        "name": "RadeonProRenderMayaUSD",
    },
    Projects.BLENDER_RPR: {
        "owner": "GPUOpen-LibrariesAndSDKs",
        "name": "RadeonProRenderBlenderAddon",
    },
    Projects.BLENDER_USD: {
        "owner": "GPUOpen-LibrariesAndSDKs",
        "name": "BlenderUSDHydraAddon",
    },
    Projects.HOUDINI: {
        "owner": "GPUOpen-LibrariesAndSDKs",
        "name": "RadeonProRenderUSD",
    },
    Projects.RENDER_STUDIO: {
        "owner": "Radeon-Pro", 
        "name": "WebUsdViewer"
    },
    Projects.HDRPR: {
        "owner": "GPUOpen-LibrariesAndSDKs",
        "name": "RadeonProRenderUSD",
    },
    Projects.INVENTOR: {
        "owner": "Radeon-Pro",
        "name": "RadeonProRenderInventorPlugin"
    }
}


def request_pull_requests_list(project: Projects, report_date: datetime):
    report_start_date = report_date - timedelta(weeks=2)

    owner = projects_info[project]["owner"]
    name = projects_info[project]["name"]

    url = f"https://api.github.com/repos/{owner}/{name}/pulls?state=all&sort=updated&direction=desc&per_page=100"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
    )

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        print("ERROR: Github token 'GITHUB_TOKEN' is invalid!")
        exit(-1)

    data = json.loads(response.text)

    # filter pull requests (open or updated in last two weeks)
    pull_requests = list(
        filter(
            (
                lambda pr: pr["state"] == "open"
                or (
                    pr.get("merged_at", None) is not None
                    and datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ").date()
                    >= report_start_date.date()
                )
            ),
            data,
        )
    )

    return pull_requests


def get_pull_requests_status(project: Projects, report_date: datetime):
    pull_requests = request_pull_requests_list(project, report_date)

    pr_data = []
    for pull_request in pull_requests:
        pr_title: str = pull_request["title"].strip()

        # format title
        if pr_title.endswith("."):
            pr_title = pr_title[:-1]

        pr_title = "PR-{number}: {title}".format(
            number=pull_request["number"], title=pr_title
        )

        pr_data.append(
            {
                "link": Link(url=pull_request["html_url"], text=pr_title),
                "status": pull_request["state"].capitalize(),
            }
        )

    return pr_data


def get_merged_prs(project: Projects, report_date: datetime):
    owner = projects_info[project]["owner"]
    name = projects_info[project]["name"]

    since_date = report_date - timedelta(weeks=2)

    # prepare url
    url = "https://github.com/{owner}/{name}/pulls?q=is%3Apr+is%3Amerged+merged%3A{from_date}..{to_datetime}".format(
        owner=owner,
        name=name,
        from_date=since_date.strftime("%Y-%m-%d"),
        to_datetime=report_date.strftime("%Y-%m-%dT%H:%M"),
    )

    # count prs
    pull_requests = request_pull_requests_list(project, report_date)
    count = len(
        list(
            filter(
                (lambda pr: bool(pr.get("merged_at", None))),
                pull_requests,
            )
        )
    )

    return {"link": url, "count": count}


if __name__ == "__main__":
    for project in projects_info:
        print(projects_info[project]["name"] + ":")
        prs = get_pull_requests_status(project, datetime.now())
        for pr in prs:
            print(
                "\tTitle: '{title}', URL: '{url}', State: '{status}'".format(
                    title=pr["link"].text, url=pr["link"].url, status=pr["status"]
                )
            )

        info = get_merged_prs(project, datetime.now())
        print("Link: " + info["link"])
        print("Merged: " + str(info["count"]))
