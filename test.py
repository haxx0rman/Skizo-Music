import youtube_dl
from playsound import playsound

# Application name	Streamer
# https://www.last.fm/api/
# API key	2d9810389d8e5c0692d4c7d9908def84
# Shared secret	d37c1888bff0823a32acb8336629288b
# Registered to	mickyfubu

import urllib.request
import urllib.parse
import re
import json
import random
import threading
import time
import traceback
import subprocess
import json

lastFM_key= "2d9810389d8e5c0692d4c7d9908def84"


def find_song_by_artist(artist):
    query_string = urllib.parse.urlencode({"artist" : artist, "api_key": lastFM_key, "format": "json"})
    #print(query_string)
    html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&" + query_string)
    res = str(html_content.read().decode())
    data = json.loads(res)
    return data["toptracks"]["track"]
    #return data

def get_song_info(artist, song):
    query_string = urllib.parse.urlencode({"artist": artist, "track": song, "api_key": lastFM_key, "format": "json"})
    #print(query_string)
    html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getinfo&" + query_string)
    res = str(html_content.read().decode())
    data = json.loads(res)
    #return data["toptracks"]["track"]
    return data

def find_albums_by_artist(artist):
    query_string = urllib.parse.urlencode({"artist" : artist, "api_key": lastFM_key, "format": "json"})
    #print(query_string)
    html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.gettopalbums&" + query_string)
    res = str(html_content.read().decode())
    data = json.loads(res)
    #return data["toptracks"]["track"]
    return data["topalbums"]["album"]

def find_song_by_album(artist, album):
    query_string = urllib.parse.urlencode({"artist" : artist, "album": album, "api_key": lastFM_key, "format": "json"})
    #print(query_string)
    html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=album.getinfo&" + query_string)
    res = str(html_content.read().decode())
    data = json.loads(res)
    return data["album"]["tracks"]["track"]
    #return data



def get_library(artist):
    albums = []
    raw_albums = find_albums_by_artist(artist)
    for album in raw_albums:
        print(album["name"])
        songs = find_song_by_album(artist, album["name"])
        s = []
        for song in songs:
            s.append(song["name"])
        a = {
            "name": album["name"],
            "songs": s
            }
        albums.append(a)
    return albums
alb = get_library("lana del rey")
#songs = find_song_by_album("lana del rey", "Ultraviolence")
#info = get_song_info("lana del rey", songs[1]["name"])
#print(shit)
#parsed = json.loads(shit[0])
print(json.dumps(alb, indent=4, sort_keys=True))
