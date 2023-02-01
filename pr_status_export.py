import os
import requests
import json
from datetime import datetime, timedelta
from common import Projects, Link

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

projects_info = {
    Projects.MAYA_RPR: {
        "owner": "GPUOpen-LibrariesAndSDKs",
        "name": "RadeonProRenderMayaPlugin",
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
    Projects.RENDER_STUDIO: {"owner": "Radeon-Pro", "name": "WebUsdViewer"},
}

# Set the time range for pull requests to be included (two weeks ago to now)
two_weeks_ago = datetime.now() - timedelta(weeks=2)
now = datetime.now()


def get_pull_requests_status(project: Projects):
    owner = projects_info[project]["owner"]
    name = projects_info[project]["name"]

    url = f"https://api.github.com/repos/{owner}/{name}/pulls?state=all&sort=updated&direction=desc&per_page=100"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
    )
    data = json.loads(response.text)

    # filter pull requests (open or updated in last two weeks)
    pull_requests = list(
        filter(
            (
                lambda pr: pr["state"] == "open"
                or (
                    pr.get("closed_at", None) is not None
                    and datetime.strptime(pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ")
                    > two_weeks_ago
                )
                or (
                    pr.get("merged_at", None) is not None
                    and datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
                    > two_weeks_ago
                )
            ),
            data,
        )
    )

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
