from dataclasses import dataclass
from enum import Enum

TEMPLATE_PATH = "./template/"
WORKING_DIR_PATH = "./tmp_template/"
PICTURES_PATH = "./pics/"


@dataclass
class Link:
    url: str
    text: str


class Projects(Enum):
    MAYA_RPR = 1
    MAYA_USD = 2
    BLENDER_RPR = 3
    BLENDER_USD = 4
    HOUDINI = 5
    RENDER_STUDIO = 6
    HDRPR = 7
    SOLIDWORKS = 8
    MATERIALX = 9
    INVENTOR = 10
    WML = 13
    RPRHYBRID = 14


class ChartType(Enum):
    UNRESOLVED_ISSUES = 1
    ISSUES_UPDATES_2W = 2


class TaskType(Enum):
    COMPLETED = 1
    PLANNED = 2

class SummaryTableColumn(Enum):
    FOUND_ISSUES = 1
    MERGED_PRS = 2

class IssueType(Enum):
    BLOCKER=1
    CRITICAL=2
