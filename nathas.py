import os, time
from slackclient import SlackClient
from pymongo import MongoClient
from apscheduler.schedulers.background import BackgroundScheduler

import commands

BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"

# BOT COMMANDS
HELLO_COMMAND = "hello"
HELP_COMMAND = "help"
LIST_COMMAND = "list"
RESUME_COMMAND = "resume"
PLAY_COMMAND = "play"
PAUSE_COMMAND = "pause"
NEXT_COMMAND = "next"
NEXT_COMMAND_1  = "play next"
CLEAR_COMMAND = "clear all"
SHUFFLE_COMMAND = "shuffle"
VOLUME_UP_COMMAND = "volume up"
VOLUME_UP_COMMAND1 = "volumeup"
VOLUME_DOWN_COMMAND = "volume down"
VOLUME_DOWN_COMMAND1 = "volumedown"

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
mongo_client = MongoClient()
db = mongo_client['nathas']

def handle_command(command, user, channel):
    response = "Not sure what you mean. Use `help` command"

    if command.startswith(HELLO_COMMAND):
        response = commands.hello()
    elif command.startswith(HELP_COMMAND):
        response = commands.help()
    elif command.startswith(LIST_COMMAND):
        response = commands.list()
    elif command.startswith(CLEAR_COMMAND):
        response = commands.clear_all()
    elif command.startswith(PAUSE_COMMAND):
        response = commands.pause()
    elif command.startswith(NEXT_COMMAND) or command.startswith(NEXT_COMMAND_1):
        response = commands.next(slack_client, channel)
    elif command.startswith(RESUME_COMMAND):
        response = commands.resume(slack_client, channel)
    elif command.startswith(SHUFFLE_COMMAND):
        response = commands.shuffle()
    elif command.startswith(PLAY_COMMAND):
        response = commands.play(slack_client, command, user, channel)
    elif command.startswith(VOLUME_UP_COMMAND) or command.startswith(VOLUME_UP_COMMAND1):
        response = commands.volume_up()
    elif command.startswith(VOLUME_DOWN_COMMAND) or command.startswith(VOLUME_DOWN_COMMAND1):
        response = commands.volume_down()

    if response:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    command = None
    user = None
    channel = None

    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                command = output['text'].split(AT_BOT)[1].strip().lower()
                user = output['user']
                channel = output['channel']

    return command, user, channel

def suggestion_engine():
    if db['playlist'].find().count() == 0:
        response = "```Your queue is empty. Here are few suggestions for you \n"
        response += "1. *Malare Ninne* \n"
        response += "2. *Kaalam kettu poi* \n"
        response += "3. *Chinna Chinna premam* \n"
        response += "4. *Pularikalo Charlie* \n"
        response += "5. *Akkam pakkam paar* \n```"
        slack_client.api_call("chat.postMessage", channel="C3DR3NLET", text=response, as_user=True)


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("nathas connected and running!")
        bg_scheduler = BackgroundScheduler()
        bg_scheduler.add_job(suggestion_engine, 'interval', seconds=60)
        bg_scheduler.start()
        while True:
            command, user, channel = parse_slack_output(slack_client.rtm_read())
            if command and user and channel:
                handle_command(command, user, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
