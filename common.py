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
    USD_VIEWER_INVENTOR = 10
    ANARI = 11
    BLENDER_HIP = 12
    WML = 13


class ChartType(Enum):
    UNRESOLVED_ISSUES = 1
    ISSUES_UPDATES_2W = 2


class TaskType(Enum):
    COMPLETED = 1
    PLANNED = 2

class SummaryTableColumn(Enum):
    FOUND_ISSUES = 1
    MERGED_PRS = 2