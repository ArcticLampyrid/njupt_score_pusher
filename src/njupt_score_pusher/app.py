import dataclasses
import logging
import os
import json
import random
import time
from typing import Any
import requests
from njupt_score_pusher.njupt_eas import NjuptEduAdminSystem, CourseScoreInfo
from njupt_score_pusher.njupt_sso import NjuptSso
from njupt_score_pusher.njupt_web_vpn import NjuptWebVpn
from njupt_score_pusher.pusher.common import (
    Pusher,
    do_push,
    build_pushers,
)
from njupt_score_pusher.pusher.entity import (
    MessageEntity,
    MessageType,
)


@dataclasses.dataclass
class GlobalConfig:
    data_dir: str
    username: str
    password: str
    web_vpn_mode: str | bool | None = None
    pushers: list[dict[str, Any]] = dataclasses.field(default_factory=list)


def __update_data(global_config: GlobalConfig, pushers: list[Pusher]):
    logging.info("Start fetching data")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        }
    )
    web_vpn = NjuptWebVpn(session)
    if global_config.web_vpn_mode == "auto" or global_config.web_vpn_mode is None:
        use_web_vpn = web_vpn.auto_detect()
    elif global_config.web_vpn_mode == "on" or global_config.web_vpn_mode is True:
        use_web_vpn = True
    elif global_config.web_vpn_mode == "off" or global_config.web_vpn_mode is False:
        use_web_vpn = False
    else:
        logging.error(
            "Invalid web vpn mode: %s, fallback to auto mode",
            global_config.web_vpn_mode,
        )
        use_web_vpn = web_vpn.auto_detect()
    if use_web_vpn:
        logging.info("Mode: Using WebVPN")
    else:
        logging.info("Mode: Direct")
    sso = NjuptSso(session, use_web_vpn)
    sso.login(global_config.username, global_config.password)
    sso.grant_service("http://jwxt.njupt.edu.cn/login_cas.aspx")
    eas = NjuptEduAdminSystem(session, global_config.username, use_web_vpn)
    new_score = eas.get_score()
    prev_score: list[CourseScoreInfo] = []
    os.makedirs(global_config.data_dir, exist_ok=True)
    if os.path.exists(os.path.join(global_config.data_dir, "score.json")):
        with open(
            os.path.join(global_config.data_dir, "score.json"),
            "r",
            encoding="utf-8",
        ) as f:
            prev_score = [CourseScoreInfo(**x) for x in json.load(f)]
    with open(
        os.path.join(global_config.data_dir, "score.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(list(map(dataclasses.asdict, new_score)), f, ensure_ascii=False)

    new_score_map = {x.id(): x for x in new_score}
    prev_score_map = {x.id(): x for x in prev_score}
    for course in new_score:
        if course.id() not in prev_score_map:
            logging.info("New item: %s %s", course.id(), course.course_name)
            do_push(
                MessageEntity(
                    type=MessageType.NEW,
                    content=course,
                ),
                pushers,
            )
        else:
            prev_course = prev_score_map[course.id()]
            if course != prev_course:
                logging.info("Item updated: %s %s", course.id(), course.course_name)
                do_push(
                    MessageEntity(
                        type=MessageType.UPDATED,
                        content=course,
                        prev=prev_course,
                    ),
                    pushers,
                )
    for prev_course in prev_score:
        if prev_course.id() not in new_score_map:
            logging.info(
                "Item removed: %s %s", prev_course.id(), prev_course.course_name
            )
            do_push(
                MessageEntity(
                    type=MessageType.REMOVED,
                    content=prev_course,
                ),
                pushers,
            )
    logging.info("Data fetched")


def __update_data_noexcept(global_config: GlobalConfig, pushers: list[Pusher]):
    try:
        __update_data(global_config, pushers)
    except Exception as e:  # pylint: disable=broad-except
        _type = e.__class__.__name__
        logging.error("Failed to fetch data: (%s) %s", _type, e)


def app_main(global_config: GlobalConfig, args):
    pushers = build_pushers(global_config.pushers)
    if args.oneshot:
        __update_data(global_config, pushers)
    else:
        while True:
            __update_data_noexcept(global_config, pushers)
            interval = 60 * 60 * random.uniform(0.8, 1.2)
            next_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(time.time() + interval)
            )
            logging.info("Next update: %s", next_time)
            time.sleep(interval)
