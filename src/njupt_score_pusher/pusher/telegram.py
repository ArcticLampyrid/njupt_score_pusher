import dataclasses

import requests

from njupt_score_pusher.pusher.entity import MessageEntity, build_text_message


@dataclasses.dataclass
class TelegramPusher:
    token: str
    chat_id: str
    api_base: str = "https://api.telegram.org"

    def push(self, message: MessageEntity):
        url = f"{self.api_base}/bot{self.token}/sendMessage"
        params = {"chat_id": self.chat_id, "text": build_text_message(message)}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
