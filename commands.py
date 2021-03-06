import os, re, time, json
import urllib2
from pymongo import MongoClient, ASCENDING
import youtube_util
import youtube_search

NATHAS_UI_ENDPOINT = os.environ.get("NATHAS_UI_ENDPOINT")
mongo_client = MongoClient()
db = mongo_client['nathas']

def hello():
    return "You say hello, I say world!"

def help():
    return "```" + \
        "Type @nathas command [options] \n\n" + \
        "list          list the songs in the queue \n" + \
        "play _[song]_ to add a song to queue \n" + \
        "clear all     to clear the queue \n" + \
        "next          to play the next song \n" + \
        "pause         to pause the current song \n" + \
        "resume        to resume the paused song \n" + \
        "suggest       to get song suggestion \n" + \
        "shuffle       to shuffle your song queue \n" + \
        "volumeup      to increase the volume of the player \n" + \
        "volumedown    to decrease the volume of the player \n" + \
        "```"

def list():
    records = db['playlist'].find()
    response = ""
    for index, record in enumerate(records, start = 1):
        response += str(index) + ". *" + record["request_string"] + "*\n" \
                if record["request_string"] is not None else record["request_url"] + "*\n"
    if not response:
        response = "The queue is currently empty :flushed:"
    return response


def play(slack_client, command, user, channel):
    play_list_coll = db['playlist']
    request_record = {
        "requested_by": user,
        "requested_at": long(time.time())
    }

    request = ' '.join(command.split(' ')[1:])

    try:
        request = re.search("(?P<url>https?://[^\s]+)", request).group("url")
        request_record["request_url"] = request
    except AttributeError:
        request_record["request_string"] = request

    channelId = youtube_util.is_artist(request)
    if channelId:
        tracks = youtube_search.get_top_tracks_for_channel(channelId)
        response = "```\nTop tracks of " + request + "\n"
        for index, track in enumerate(tracks, start=1):
            response += str(index) + ". *" + track + "*\n ```"

    else:
        play_list_coll.insert_one(request_record)
        response = get_confirm_play_msg(play_list_coll.count() - 1, request)

        slack_client.api_call("chat.postMessage", channel=channel,
                            text=response, as_user=True)

        artists = []
        if request_record["request_string"]:
            artists = youtube_util.get_artists(request)
            response = "\n > Related  `" + '`,`'.join(artists) + "`"

    return response

def get_confirm_play_msg(prev_queue_size, request):
    if prev_queue_size == 0:
        response = 'Sure... \'' +  request + '\' will be played next'
    elif prev_queue_size == 1:
        response = 'Sure... \'' +  request + '\' will be played after 1 song'
    else:
        response = 'Sure... \'' +  request + '\' will be played after ' + str(prev_queue_size) + ' songs'

    return response

def next(slack_client, channel):
    cursor = get_sorted_cursor(2)
    try:
        cursor.next()
        next_song = cursor.next()
        send_message_with_attachment(slack_client, channel, next_song['request_string'])
    except StopIteration:
        pass
    urllib2.urlopen(NATHAS_UI_ENDPOINT + "/next").read()

def pause():
    urllib2.urlopen(NATHAS_UI_ENDPOINT + "/pause").read()
    return "Consider it done"

def resume(slack_client, channel):
    cursor = get_sorted_cursor(1)
    try:
        next_song = cursor.next()
        send_message_with_attachment(slack_client, channel, next_song['request_string'])
        urllib2.urlopen(NATHAS_UI_ENDPOINT + "/resume").read()
    except StopIteration:
        pass


def volume_up():
    urllib2.urlopen(NATHAS_UI_ENDPOINT + "/volumeup").read()
    return "Consider it done"

def volume_down():
    urllib2.urlopen(NATHAS_UI_ENDPOINT + "/volumedown").read()
    return "Consider it done"

def shuffle():
    urllib2.urlopen(NATHAS_UI_ENDPOINT + "/shuffle").read()
    return "Consider it done"

def clear_all():
    db['playlist'].delete_many({})
    return "Sure, I have cleared the queue"

def get_sorted_cursor(limit_size):
    return db['playlist'].find().sort([("requested_at", ASCENDING)]).limit(limit_size)

def send_message_with_attachment(slack_client, channel, title):
    attachment = [{"color": "#439FE0","title": "Now Playing","text": title}]
    slack_client.api_call("chat.postMessage", channel=channel, attachments=attachment, text=title, as_user=True)
