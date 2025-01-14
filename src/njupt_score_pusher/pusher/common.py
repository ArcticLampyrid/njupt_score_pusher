import logging
import random
import time
from typing import Any, Protocol

from njupt_score_pusher.pusher.entity import MessageEntity
from njupt_score_pusher.pusher.registry import PUSHER_REGISTRY

logger = logging.getLogger(__name__)


class Pusher(Protocol):
    def push(self, message: MessageEntity): ...


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
