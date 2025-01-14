## NJUPT Score Pusher
A simple script to automatically fetch course scores of NJUPTer and push them to a chatbot. Currently, only pushing to Telegram is supported.

## Usage
1. We assume that you have created a bot and obtained the token and other necessary information.
2. Then, write your configuration file `config.json`:
   ```json
   {
     "data_dir": "/app/data",
     "username": "<njupt-sso-username>",
     "password": "<njupt-sso-password>",
     "pushers": [
       {
         "type": "telegram",
         "token": "<telegram-bot-token>",
         "chat_id": "<telegram-chat-id>"
       }
     ]
   }
   ```
   *Note: you should use the credential of the SSO (Single sign-on) system, not the educational administration system.*
3. After that, use the docker compose to start the service:
   ```yaml
   services:
     njupt-score-pusher:
       build:
         context: https://github.com/ArcticLampyrid/njupt_score_pusher.git
       container_name: njupt-score-pusher
       restart: 'always'
       volumes:
         - ./config.json:/app/config.json
         - ./data:/app/data
   ```
4. The script will automatically fetch the scores and push them to the chatbot.

## Configuration
- `data_dir`: the directory to store the data.
- `username`: the username of the SSO system.
- `password`: the password of the SSO system.
- `pushers`: a list of pushers.
  - `type`: the type of the pusher.
  - \<pusher-specific-configuration\>: the configuration of the pusher.

### Pusher
#### Telegram
- `type`: `telegram`, fixed value.
- `token`: the token of the Telegram bot.
- `chat_id`: the chat ID of the Telegram chat.
- `api_base`: the base URL of the Telegram Bot API, default to `https://api.telegram.org`. Change it to a reverse proxy if you cannot access the Telegram Bot API directly.

#### Other?
Just add your implementation in the `pusher` directory and update `pusher/registry.py` file.  
PRs are welcome!

## Development
Dev Container in VSCode is recommended for project development. Type checker and linter are enabled by default.

## License
Licensed under AGPL v3.0 or later. See [LICENSE](LICENSE.md) for more information.
