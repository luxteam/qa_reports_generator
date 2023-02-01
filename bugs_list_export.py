import os
from datetime import datetime, timedelta
from atlassian import Jira
from common import Projects
import urllib

JIRA_URL = os.getenv("JIRA_URL", "https://amdrender.atlassian.net/")
JIRA_USERNAME = os.environ["JIRA_USERNAME"]
JIRA_TOKEN = os.environ["JIRA_TOKEN"]

jira_instance = Jira(
    # Url of jira server
    url=JIRA_URL,
    # loginuser name
    username=JIRA_USERNAME,
    # password/token
    password=JIRA_TOKEN,
    cloud=True,
)

projects_jira_names = {
    Projects.MAYA_RPR: "RPRMAYA",
    Projects.MAYA_USD: "MAYAUS",
    Projects.BLENDER_RPR: "RPRBLND",
    Projects.BLENDER_USD: "BLEN",
    Projects.RENDER_STUDIO: "RS",
    # Projects.SOLIDWORKS: "SV",
    Projects.HOUDINI: "RPRHOUD",
}


def get_blockers():
    jql_request = 'project in (RPRHOUD, RS, BLEN, RPRBLND, AN, MATX, MAYAUS, PYRENDER, RI, RPRHYB, RPRMAYA, RPRUS, RPRVIEW) AND issuetype = Bug AND status in ("Under Review", Assessment, Backlog, Blocked, "In Progress", "In Review", "In Test", "In Testing", Open, Reopened, "Selected for development", "Testing / QA", "To Do", "Waiting for merge") AND priority = Blocker ORDER BY created DESC'
    issues = jira_instance.jql(jql_request).get("issues")

    blockers = []
    for issue in issues:
        blocker = {
            "key": issue["key"],
            "link": "https://amdrender.atlassian.net/browse/" + issue["key"],
            "description": issue["fields"]["summary"],
        }
        blockers.append(blocker)

    return blockers


def get_bugs():
    new_bugs = {}

    for project in projects_jira_names:
        project_jira_name = projects_jira_names[project]

        jql_request = "created >= {from_date} AND created <= {to_date} AND project = {project} AND issuetype = Bug ORDER BY created DESC".format(
            from_date=(datetime.now() - timedelta(weeks=2)).strftime("%Y-%m-%d"),
            to_date=datetime.now().strftime("%Y-%m-%d"),
            project=project_jira_name,
        )
        issues = jira_instance.jql(jql_request)
        count = issues["total"]

        link = urllib.parse.quote(
            "https://amdrender.atlassian.net/issues/?jql=project = {project} AND issuetype = Bug AND created >= {from_date} AND created <= {to_date} ORDER BY created DESC".format(
                from_date=(datetime.now() - timedelta(weeks=2)).strftime("%Y-%m-%d"),
                to_date=datetime.now().strftime("%Y-%m-%d"),
                project=project_jira_name,
            )
        )

        new_bugs[project] = {"count": int(count), "link": link}

    return new_bugs
