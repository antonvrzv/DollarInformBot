#!/usr/bin/env python3
# coding: utf-8

# Copyright (C) 2022 Vorozhischev Anton. All rights reserved.
# GNU General Public License v3.0
# E-mail: antonvorozhischev@gmail.com

# In this major version of the application,
# the bot receives incoming updates and sends information to all active users.
# Information about each user is saved to a JSON file,
# when connected to the bot and removed from the file when the bot is blocked.

# In the next major version,
# you can implement the bot as a member of the telegram channel,
# which won't have to save user data in a file,
# the bot will simply send messages to this channel,
# which will be available to all active users.

import os
import sys
import time
import json
import os.path
import logging
import requests
import schedule
import telegram
import threading
import coloredlogs
from datetime import date
from telegram.error import NetworkError, BadRequest, TimedOut
from telegram.error import Unauthorized, InvalidToken

LOG = None
BOT = None
MUTEX = None
USERS_FILE = "users.json"
RESOURCE_URL = 'https://www.cbr-xml-daily.ru/daily_json.js'
GREETING = "Hi, I am a bot that daily informs " + \
           "about the official dollar exchange rate at 3 p.m. \U0001F916"


class User:
    def __init__(self, firstName, lastName, userName, chatId):
        self.firstName = firstName
        self.lastName = lastName
        self.userName = userName
        self.chatId = chatId


class Users:
    def __init__(self):
        self.usersDict = dict()
        self.usersDict['Users'] = list()

    def userIsActive(self, chatId):
        users = self.usersDict['Users']

        for user in users:
            if user['chatId'] == chatId:
                return True

    def addUser(self, firstName, lastName, userName, chatId):
        user = User(firstName, lastName, userName, chatId)
        self.usersDict['Users'].append(user.__dict__)
        del user
        with open(USERS_FILE, 'w') as f:
            json.dump(self.usersDict, f, indent=6)

    def deleteUser(self, chatId):
        users = self.usersDict['Users']

        for idx in range(len(users)):
            if users[idx]['chatId'] == chatId:
                del users[idx]
                with open(USERS_FILE, 'w') as f:
                    json.dump(self.usersDict, f, indent=6)

                return

    def sendMessageToUsers(self, usdVal):
        users = self.usersDict['Users']

        for user in users:
            chatId = user['chatId']
            try:
                BOT.send_message(chatId,
                                 "Dollar exchange rate for today " +
                                 f"({date.today().strftime('%d/%m/%Y')}): " +
                                 f"{usdVal} \U0001F4B5")

                LOG.debug(f'\nFirstname: {user["firstName"]} \
                            \nLastname: {user["lastName"]} \
                            \nUsername: {user["userName"]} \
                            \nChat ID: {user["chatId"]} \
                            \nMessage has been sent to this user\n')
                time.sleep(0.5)
            except Unauthorized:
                isActive = self.userIsActive(chatId)
                if isActive:
                    MUTEX.acquire()
                    LOG.debug(f'\nFirstname: {user["firstName"]} \
                                \nLastname: {user["lastName"]} \
                                \nUsername: {user["userName"]} \
                                \nChat ID: {user["chatId"]} \
                                \nThis user has removed or blocked the bot\n')
                    self.deleteUser(chatId)
                    MUTEX.release()


def getFirstUpdateId():
    try:
        updatesList = BOT.get_updates()
        update = updatesList[0]
        updateId = update.update_id
        LOG.debug(f'The first update id: {updateId}')
    except IndexError:
        LOG.debug('There are no updates')
        updateId = None

    return updateId


def getUpdatesThread(argsList):
    LOG.debug('getUpdatesThread has been started')

    users = argsList[0]
    tEvent = argsList[1]

    updateId = getFirstUpdateId()

    while not tEvent.is_set():
        try:
            updates = BOT.get_updates(offset=updateId, timeout=10)
            for update in updates:

                if hasattr(update.my_chat_member, 'new_chat_member'):
                    status = update.my_chat_member.new_chat_member.status
                    if status == 'kicked':
                        firstName = update.my_chat_member.chat.first_name
                        lastName = update.my_chat_member.chat.last_name
                        userName = update.my_chat_member.chat.username
                        chatId = update.my_chat_member.chat.id

                        isActive = users.userIsActive(chatId)
                        if isActive:
                            MUTEX.acquire()
                            LOG.debug(f"\nFirstname: {firstName} \
                                      \nLastname: {lastName} \
                                      \nUsername: {userName} \
                                      \nChat ID: {chatId} \
                                      \nThis user has removed or " +
                                      "blocked the bot\n")

                            users.deleteUser(chatId)
                            MUTEX.release()

                if update.message and update.message.text:
                    text = update.message.text
                    if text == '/start':
                        firstName = update.message.chat.first_name
                        lastName = update.message.chat.last_name
                        userName = update.message.chat.username
                        chatId = update.message.chat.id

                        isActive = users.userIsActive(chatId)
                        if not isActive:
                            LOG.debug(f"\nFirstname: {firstName} \
                                      \nLastname: {lastName} \
                                      \nUsername: {userName} \
                                      \nChat ID: {chatId} \
                                      \nThis user has just " +
                                      "connected to the bot\n")

                            users.addUser(firstName,
                                          lastName,
                                          userName,
                                          chatId)
                        BOT.send_message(chatId, GREETING)

                updateId = update.update_id + 1
        except NetworkError:
            LOG.error('Network error')
            time.sleep(2)
        except BadRequest:
            LOG.error('BadRequest error')
            time.sleep(2)
        except TimedOut:
            LOG.error('Time out error')
            time.sleep(2)
        # The user has removed or blocked the bot
        except Unauthorized:
            firstName = update.message.chat.first_name
            lastName = update.message.chat.last_name
            userName = update.message.chat.username
            chatId = update.message.chat.id

            isActive = users.userIsActive(chatId)
            if isActive:
                MUTEX.acquire()
                LOG.debug(f"\nFirstname: {firstName} \
                          \nLastname: {update.message.chat.last_name} \
                          \nUsername: {lastName} \
                          \nChat ID: {chatId} \
                          \nThis user has removed or " +
                          "blocked the bot\n")
                users.deleteUser(update.message.chat.id)
                MUTEX.release()

            updateId += 1


def getDollarInform(users):
    response = requests.get(RESOURCE_URL)
    if response.status_code == 200:
        LOG.debug(f'Request to {RESOURCE_URL} has succeeded')
        # convert from JSON format to dict
        dataDict = json.loads(response.text)
        valuteDict = dataDict['Valute']
        usdDict = valuteDict['USD']
        usdVal = usdDict['Value']

        users.sendMessageToUsers(usdVal)
    else:
        LOG.error(f"Request to {RESOURCE_URL} " +
                  "failed with error code={response.status_code}")
        LOG.error(f'Check if the resource {RESOURCE_URL} is reachable')


def getInformThread(argsList):
    LOG.debug('getInformThread has been started')

    users = argsList[0]
    tEvent = argsList[1]

    schedule.every().day.at("15:00").do(getDollarInform, users)

    while not tEvent.is_set():
        schedule.run_pending()
        time.sleep(1)


def loggingInit(logFile):
    global LOG
    level_styles_string = 'debug=yellow;error=red;'
    level_styles = coloredlogs.parse_encoded_styles(level_styles_string)

    field_styles_string = 'funcName=cyan;levelname=white,bold;asctime=green;'
    field_styles = coloredlogs.parse_encoded_styles(field_styles_string)

    LOG = logging.getLogger('LOG')

    # For print logs to console
    coloredlogs.install(level=logging.DEBUG,
                        logger=LOG,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        fmt="%(asctime)s [%(funcName)s]" +
                        "[%(levelname)s] %(message)s",
                        level_styles=level_styles,
                        field_styles=field_styles,
                        isatty=True)

    # Create a handler to print logs to file
    formatter = coloredlogs.ColoredFormatter(fmt="%(asctime)s [%(funcName)s]" +
                                             "[%(levelname)s] %(message)s",
                                             level_styles=level_styles,
                                             field_styles=field_styles)
    fh = logging.FileHandler(logFile)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    LOG.addHandler(fh)


def main():
    global BOT, MUTEX
    try:
        loggingInit('.log')

        LOG.debug('Bot has been started')

        users = Users()

        # Read users from json file and convert to dict
        # NOTE: Probably it is worth switching to the Yaml format
        # for storage information about users in the future.
        if os.path.isfile(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users.usersDict = json.load(f)
            LOG.debug('Getting users from JSON file has been done')

        # Autorization in Telegram Bot Api
        try:
            tokenBot = os.environ.get('BOT_TOKEN')
            BOT = telegram.Bot(tokenBot)
        except InvalidToken:
            logging.error('Invalid token: check if bot token is set')
            sys.exit(1)

        LOG.debug('Bot has been authorized')

        MUTEX = threading.Lock()

        tGetInformEvent = threading.Event()
        tGetUpdatesEvent = threading.Event()

        argsList = [users, tGetUpdatesEvent]
        tGetUpdates = threading.Thread(target=getUpdatesThread,
                                       args=(argsList,),
                                       name='getUpdatesThread')
        tGetUpdates.start()

        argsList = [users, tGetInformEvent]
        tGetInform = threading.Thread(target=getInformThread,
                                      args=(argsList,),
                                      name='getInformThread')
        tGetInform.start()

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        LOG.error('Closing app by keyboard interrupt')
        LOG.error('Threads are finishing...')
        tGetInformEvent.set()
        tGetUpdatesEvent.set()

        tGetInform.join()
        tGetUpdates.join()
        LOG.error('Threads have been closed')


if __name__ == "__main__":
    main()
