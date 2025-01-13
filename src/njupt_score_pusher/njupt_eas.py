import base64
from dataclasses import dataclass
from typing import Tuple
import urllib.parse
import requests
import logging
import re
import urllib

logger = logging.getLogger(__name__)


NAME_PATTERN = re.compile(r'<span id="xhxm">(.+?)同学</span></em>')
VIEW_STATE_PATTERN = re.compile(
    r'<input type="hidden" name="__VIEWSTATE" value="(.+?)" />'
)
VIEW_STATE_GENERATOR_PATTERN = re.compile(
    r'<input type="hidden" name="__VIEWSTATEGENERATOR" value="(.+?)" />'
)


@dataclass
class CourseScoreInfo:
    # 学年
    year: str
    # 学期
    term: str
    # 课程代码
    course_code: str
    # 课程名称
    course_name: str
    # 课程性质
    course_nature: str
    # 课程归属
    course_belong: str
    # 学分
    credit: float
    # 绩点
    gpa: float
    # 成绩（可能为百分制成绩或者等级）
    score: str
    # 辅修标记
    minor_flag: bool
    # 补考成绩（可能为百分制成绩或者等级）
    makeup_score: str
    # 重修成绩（可能为百分制成绩或者等级）
    retake_score: str
    # 学院名称
    college_name: str
    # 备注
    comment: str
    # 重修标记
    retake_flag: bool
    # 课程英文名称
    course_english_name: str

    def id(self):
        return f"{self.year}-{self.term}-{self.course_code}"


class NjuptEduAdminSystem:
    def __init__(
        self,
        session: requests.Session,
        student_id: str,
        use_web_vpn: bool = False,
    ):
        self.session = session
        self.use_web_vpn = use_web_vpn
        self.base_url = (
            "http://jwxt.njupt.edu.cn"
            if not use_web_vpn
            else "https://vpn.njupt.edu.cn:8443/http/webvpn5e607416b84322620fcfebad55f2c381efb3e3d8de97685feb46fd2e866a8ae9"
        )
        self.student_id = student_id

    def get_name(self) -> str:
        url = f"{self.base_url}/xs_main.aspx?xh={self.student_id}"
        response = self.session.get(url)
        response.raise_for_status()
        response.encoding = "gb18030"
        match = NAME_PATTERN.search(response.text)
        if match is None:
            raise ValueError("Failed to get name")
        return match.group(1)

    def __get_score_view_state(self) -> str:
        params = {
            "xh": self.student_id,
            "xm": self.get_name(),
            "gnmkdm": "N121605",
        }
        url = f"{self.base_url}/xscj_gc.aspx?" + urllib.parse.urlencode(
            params, encoding="gb18030"
        )
        response = self.session.get(url)
        response.raise_for_status()
        response.encoding = "gb18030"
        initial_view_state_match = VIEW_STATE_PATTERN.search(response.text)
        initial_view_state_generator_match = VIEW_STATE_GENERATOR_PATTERN.search(
            response.text
        )
        if (
            initial_view_state_match is None
            or initial_view_state_generator_match is None
        ):
            raise ValueError("Failed to get initial view state")
        view_state = initial_view_state_match.group(1)
        view_state_generator = initial_view_state_generator_match.group(1)
        data = {
            "__VIEWSTATE": view_state,
            "__VIEWSTATEGENERATOR": view_state_generator,
            "ddlXN": "",
            "ddlXQ": "",
            "Button2": "在校学习成绩查询",
        }
        response = self.session.post(
            url,
            data=urllib.parse.urlencode(data, encoding="gb18030"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        response.encoding = "gb18030"
        view_state_match = VIEW_STATE_PATTERN.search(response.text)
        if view_state_match is None:
            raise ValueError("Failed to get view state")
        view_state = view_state_match.group(1)
        return view_state

    @staticmethod
    def __parse_view_state(view_state: str):
        tag_string = base64.b64decode(view_state)[0:-20].decode("utf-8")
        tag = ""
        values = []
        stack = []
        is_escaped = False
        skip_next_semicolon = False
        for char in tag_string:
            if skip_next_semicolon:
                skip_next_semicolon = False
                if char == ";":
                    continue
            if is_escaped:
                tag += char
                is_escaped = False
            elif char == "\\":
                is_escaped = True
            elif char == "<":
                stack.append((tag, len(values)))
                tag = ""
            elif char == ">":
                values.append(tag)
                tag = ""
                prev_tag, prev_length = stack.pop()
                values = values[:prev_length] + [{prev_tag: values[prev_length:]}]
                skip_next_semicolon = True
            elif char == ";":
                values.append(tag)
                tag = ""
            else:
                tag += char
        if tag != "":
            values.append(tag)
        return values[0]

    def get_score(self) -> Tuple[CourseScoreInfo]:
        state_str = self.__get_score_view_state()
        state = NjuptEduAdminSystem.__parse_view_state(state_str)
        courses = state["t"][1]["t"][2]["l"][0]["t"][2]["l"][13]["t"][2]["l"][0]["t"][
            2
        ]["l"]
        result = []
        for course in courses:
            if not isinstance(course, dict):
                continue
            texts = tuple(
                (
                    x["t"][0]["p"][0]["p"][1]["l"][0].replace("&nbsp;", " ").strip()
                    for x in course["t"][2]["l"]
                    if isinstance(x, dict)
                )
            )
            result.append(
                CourseScoreInfo(
                    year=texts[0],
                    term=texts[1],
                    course_code=texts[2],
                    course_name=texts[3],
                    course_nature=texts[4],
                    course_belong=texts[5],
                    credit=float(texts[6]) if texts[6] != "" else 0,
                    gpa=float(texts[7]) if texts[7] != "" else 0,
                    score=texts[13],
                    minor_flag=texts[14] != "" and texts[14] != "0",
                    makeup_score=texts[15],
                    retake_score=texts[16],
                    college_name=texts[18],
                    comment=texts[19],
                    retake_flag=texts[20] != "" and texts[20] != "0",
                    course_english_name=texts[21],
                )
            )
        return tuple(result)
