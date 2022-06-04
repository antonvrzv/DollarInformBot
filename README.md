### About:
The main purpose of the bot is to notify users daily about the current dollar exchange rate.
### Principle of work:
The bot works in 2 threads:
- Thread for incoming updates - a stream that, after a certain period of time, sends a request to the Telegram Bot API to receive incoming updates from users. When a new user is connected, the bot creates it in the local database (JSON file) for inclusion in the mailing list. In case of loss of the bot, the user's bat is found from and, accordingly, from the mailing list.
- Mailing Thread: A stream that queries the data of the central bank web service at a specific time every day to obtain information about the official exchange rate for today and mailings to active users.
### A resource with information about the dollar exchange rate that the bot uses:
- [Json data](https://www.cbr-xml-daily.ru/daily_json.js)
### How to use the bot:

1. Install this packages:

```
pip3 install telegram
pip3 install coloredlogs
pip3 install schedule
pip3 install requests
pip3 install python-telegram-bot
```

2. After creating your bot via [@BotFather](https://t.me/BotFather), export the bot token to an environment variable to authorize the bot in the TelegramBotAPI:

```
export BOT_TOKEN="<Your token>"
```

3. Install ANSIescape package in sublime text in order to see color logs in the file '.log'

### How it works:

Starting the bot:

<img src="https://media.giphy.com/media/oRzHl9cq5MgT2NCDz5/giphy.gif" alt="Girl in a jacket" width="700" height="500">

Getting a message about the dollar exchange rate:

<img src="https://media.giphy.com/media/YaFsnFQzzPM1rwGsuf/giphy.gif" alt="Girl in a jacket" width="700" height="300">



