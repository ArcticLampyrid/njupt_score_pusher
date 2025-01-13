import dataclasses
from time import sleep


@dataclasses.dataclass
class GlobalConfig:
    data_dir: str
    username: str
    password: str
    pushers: list[dict[str, any]] = dataclasses.field(default_factory=list)


def main():
    import os
    import argparse
    import logging

    parser = argparse.ArgumentParser(
        description="NJUPT Score Pusher", prog="njupt-score-pusher"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Configuration file path",
        required=True,
    )
    parser.add_argument("--dry", action="store_true", help="Dry run (no push)")
    parser.add_argument("--oneshot", action="store_true", help="Oneshot mode")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")
    args = parser.parse_args()

    logging_level = logging.INFO if not args.debug else logging.DEBUG
    logging.basicConfig(
        level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    if args.debug:
        logging.debug("Debug mode enabled")

    import requests
    import json
    import random
    from njupt_score_pusher.njupt_eas import NjuptEduAdminSystem, CourseScoreInfo
    from njupt_score_pusher.njupt_sso import NjuptSso
    from njupt_score_pusher.njupt_web_vpn import NjuptWebVpn

    if not os.path.exists(args.config):
        logging.error("Configuration file not found")
        return
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
        global_config = GlobalConfig(**config)
        if args.dry:
            logging.info("Dry run enabled")
            global_config.pushers = []

    def __build_message_when_new(course: CourseScoreInfo) -> str:
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

    def __build_message_when_updated(
        prev: CourseScoreInfo, course: CourseScoreInfo
    ) -> str:
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

    def __do_push(message: str, pushers: list[dict[str, any]]):
        for pusher in pushers:
            if pusher["type"] == "telegram":
                if "token" not in pusher or "chat_id" not in pusher:
                    logging.error("Telegram pusher config error")
                    return
                api_base = pusher.get("api_base", "https://api.telegram.org")
                url = f"{api_base}/bot{pusher['token']}/sendMessage"
                params = {"chat_id": pusher["chat_id"], "text": message}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code != 200:
                    logging.error("Failed to push message to Telegram")
                else:
                    logging.info("Message pushed to Telegram")
            else:
                logging.error("Unsupported pusher type: %s", pusher["type"])
            sleep(random.uniform(0.5, 1.0))

    def __update_data():
        logging.info("Start fetching data")
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            }
        )
        web_vpn = NjuptWebVpn(session)
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

        prev_score_map = {x.id(): x for x in prev_score}
        for course in new_score:
            if course.id() not in prev_score_map:
                logging.info("New item: %s %s", course.id(), course.course_name)
                __do_push(__build_message_when_new(course), global_config.pushers)
            else:
                prev_course = prev_score_map[course.id()]
                if course != prev_course:
                    logging.info("Item updated: %s %s", course.id(), course.course_name)
                    __do_push(
                        __build_message_when_updated(prev_course, course),
                        global_config.pushers,
                    )
        logging.info("Data fetched")

    def __update_data_noexcept():
        try:
            __update_data()
        except Exception as e:  # pylint: disable=broad-except
            _type = e.__class__.__name__
            logging.error("Failed to fetch data: (%s) %s", _type, e)

    if args.oneshot:
        __update_data()
    else:
        import time

        while True:
            __update_data_noexcept()
            interval = 60 * 60 * random.uniform(0.8, 1.2)
            next_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(time.time() + interval)
            )
            logging.info("Next update: %s", next_time)
            time.sleep(interval)


if __name__ == "__main__":  #
    main()
