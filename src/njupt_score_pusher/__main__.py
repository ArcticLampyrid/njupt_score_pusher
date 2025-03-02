import os
import argparse
import logging
import json
import dacite


def main():
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

    if not os.path.exists(args.config):
        logging.error("Configuration file not found")
        return

    from njupt_score_pusher.app import GlobalConfig, app_main

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
        global_config = dacite.from_dict(GlobalConfig, config)
        if args.dry:
            logging.info("Dry run enabled")
            global_config.pushers = []
    app_main(global_config, args)


if __name__ == "__main__":  #
    main()
