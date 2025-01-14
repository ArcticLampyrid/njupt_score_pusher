import dataclasses
import enum
import logging
import random
import time
from typing import Any, Optional, Protocol

from njupt_score_pusher.njupt_eas import CourseScoreInfo
from njupt_score_pusher.pusher.registry import PUSHER_REGISTRY

logger = logging.getLogger(__name__)


@enum.unique
class MessageType(enum.Enum):
    NEW = 1
    UPDATED = 2
    REMOVED = 3


@dataclasses.dataclass
class MessageEntity:
    type: MessageType
    content: CourseScoreInfo
    prev: Optional[CourseScoreInfo] = None


class Pusher(Protocol):
    def push(self, message: MessageEntity): ...


def ___text_message_when_new(course: CourseScoreInfo) -> str:
    info = "【新成绩】\n"
    info += f"课程：{course.id()} {course.course_name} （{course.course_nature}）\n"
    info += f"成绩：{course.score}\n"
    if course.makeup_score != "":
        info += f"补考成绩：{course.makeup_score}\n"
    if course.retake_score != "":
        info += f"重修成绩：{course.retake_score}\n"
    info += f"学分：{course.credit}\n"
    info += f"绩点：{course.gpa}\n"
    return info


def ___text_message_when_updated(prev: CourseScoreInfo, course: CourseScoreInfo) -> str:
    info = "【成绩更新】\n"
    info += f"课程：{course.id()} {course.course_name} （{course.course_nature}）\n"
    if course.score != prev.score:
        info += f"成绩：{prev.score} → {course.score}\n"
    else:
        info += f"成绩：{course.score}\n"
    if course.makeup_score != prev.makeup_score:
        info += f"补考成绩：{prev.makeup_score} → {course.makeup_score}\n"
    elif course.makeup_score != "":
        info += f"补考成绩：{course.makeup_score}\n"
    if course.retake_score != prev.retake_score:
        info += f"重修成绩：{prev.retake_score} → {course.retake_score}\n"
    elif course.retake_score != "":
        info += f"重修成绩：{course.retake_score}\n"
    if course.credit != prev.credit:
        info += f"学分：{prev.credit} → {course.credit}\n"
    else:
        info += f"学分：{course.credit}\n"
    if course.gpa != prev.gpa:
        info += f"绩点：{prev.gpa} → {course.gpa}\n"
    else:
        info += f"绩点：{course.gpa}\n"
    return info


def ___text_message_when_removed(course: CourseScoreInfo) -> str:
    info = "【成绩移除】\n"
    info += f"课程：{course.id()} {course.course_name} （{course.course_nature}）\n"
    info += f"成绩：{course.score}\n"
    if course.makeup_score != "":
        info += f"补考成绩：{course.makeup_score}\n"
    if course.retake_score != "":
        info += f"重修成绩：{course.retake_score}\n"
    info += f"学分：{course.credit}\n"
    info += f"绩点：{course.gpa}\n"
    return info


def build_text_message(entity: MessageEntity) -> str:
    if entity.type == MessageType.NEW:
        return ___text_message_when_new(entity.content)
    if entity.type == MessageType.UPDATED:
        if entity.prev is None:
            logger.error("No previous data for updated message")
            return ""
        return ___text_message_when_updated(entity.prev, entity.content)
    if entity.type == MessageType.REMOVED:
        return ___text_message_when_removed(entity.content)
    logger.error("Unsupported message type: %s", entity.type)
    return ""


def build_pushers(params: list[dict[str, Any]]) -> list[Pusher]:
    pushers = []
    for param in params:
        try:
            if param["type"] in PUSHER_REGISTRY:
                pusher_param = {k: v for k, v in param.items() if k != "type"}
                pusher_instance = PUSHER_REGISTRY[param["type"]](**pusher_param)
                pushers.append(pusher_instance)
            else:
                raise ValueError("Unsupported pusher type")
        except Exception as e:  # pylint: disable=broad-except
            _type = e.__class__.__name__
            logger.error("Failed to create pusher: (%s) %s", _type, e)
    return pushers


def do_push(message: MessageEntity, pushers: list[Pusher]):
    for pusher in pushers:
        try:
            pusher.push(message)
        except Exception as e:  # pylint: disable=broad-except
            _type = e.__class__.__name__
            logging.error(
                "Failed to push message to %s: (%s) %s",
                pusher.__class__.__name__,
                _type,
                e,
            )
        time.sleep(random.uniform(0.5, 1.0))
