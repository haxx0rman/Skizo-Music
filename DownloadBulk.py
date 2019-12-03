import youtube_dl
from playsound import playsound

# Application name	Streamer
# https://www.last.fm/api/
# API key	2d9810389d8e5c0692d4c7d9908def84
# Shared secret	d37c1888bff0823a32acb8336629288b
# Registered to	mickyfubu

import urllib.request
import urllib.parse
import urllib
import re
import json
import random
import threading
import time
import traceback
import subprocess
import requests
import os.path

lastFM_key= "2d9810389d8e5c0692d4c7d9908def84"

# artists = ["lana del rey", "alt j", "andrew jackson jihad", "elton john", "jeff magnum", "los lobos", "neutral milk hotel", "noah and the whale",
#             "nancy sinatra", "jack stauber"]
# artists = ["jeff buckley", "glass animals", "sufjan stevens", "queen", "tom petty", "cage the elephant", "vampire weekend", "paul mccartney", "the beatles", "red hot chili peppers", "the talking heads",
#             "the black keys", "rem", "milky chance"]
#t = threading.Thread(target=cake_server, args = (chat_message.from_jid, chat_message.body, chat_message.from_jid)).start()


class Skizo:
    def __init__(self, LFM_key, querry):

        self.current = 0
        self.prevsongs = []
        self.queue = []
        self.total_songs = 0
        self.querry = querry
        self.artist = None
        self.library = []
        self.LFM_key = LFM_key
        self.songs = self.get_saved_songs()

        #https://github.com/ytdl-org/youtube-dl/blob/3e4cedf9e8cd3157df2457df7274d0c842421945/youtube_dl/YoutubeDL.py#L161
        self.ydl_opts = {
            'format': 'bestaudio/best',
            "outtmpl": "Music/%(title)s.%(ext)s",
            "verbose": False, #set to true for debugging logs
            'postprocessors': [{
                #'embed-thumbnail': "./img.png",
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'logger': MyLogger(),
            'progress_hooks': [my_hook],
        }

        self.start()

    def start(self):
        # print("Enter an artist (press ENTER)")
        # self.querry = input()
        # if len(self.querry) < 2:
        #     self.querry = None
        # #self.get_queue()
        self.run()

    def get_saved_songs(self):
        with open('songs.json') as f:
            data = json.load(f)
        return data

    def save_song(self, song):
        if song is not None:
            self.songs["songs"].append(song)
            with open('songs.json', 'w') as outfile:
                json.dump(self.songs, outfile, indent=4, sort_keys=True)

    def find_song_by_artist(self, artist):

        results = []
        for x in range(1, 10):
            query_string = urllib.parse.urlencode({"artist" : artist, "api_key": lastFM_key, "format": "json", "page": x})
            html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&" + query_string)
            res = str(html_content.read().decode())
            data = json.loads(res)
            data = data["toptracks"]["track"]
            results = results + data
        return results

    def find_song_by_album(self, artist, album):
        query_string = urllib.parse.urlencode({"artist" : artist, "album": album, "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=album.getinfo&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["album"]["tracks"]["track"]

    def find_albums_by_artist(self, artist):
        query_string = urllib.parse.urlencode({"artist" : artist, "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.gettopalbums&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        self.artist = data["topalbums"]["@attr"]["artist"]
        return data["topalbums"]["album"]

    def get_library(self, artist):
        albums = []
        raw_albums = self.find_albums_by_artist(artist)
        print("Fetching Albums...")
        for album in raw_albums:
            try:
                print(album["name"])
                songs = self.find_song_by_album(artist, album["name"])
                s = []
                if len(songs) < 1:
                    continue
                for song in songs:
                    self.total_songs = self.total_songs + 1
                    s.append(song["name"])
                a = {
                    "name": album["name"],
                    "songs": s
                    }
                albums.append(a)
            except Exception as e:
                print(e)
        return albums

    def get_similar(self, song):
        query_string = urllib.parse.urlencode({"artist" : song["artist"], "track": song["track"], "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["similartracks"]["track"]

    def get_song_info(self, artist, song):
        query_string = urllib.parse.urlencode({"artist": artist, "track": song, "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getinfo&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data

    def download(self, url):
        try:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([url])

        except Exception as e:
            print("Download Error!")
            print(e)


    def get_title(self, url):
        #https://github.com/ytdl-org/youtube-dl/blob/master/README.md#output-template
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info("{}".format(url))
            return info.get("title", None)
            #print(title)

    def run(self):
        print("Fetching Library...")
        self.library = self.get_library(self.querry)
        count = 0
        print("Total Songs: " + str(self.total_songs))
        #print(json.dumps(self.library, indent=4, sort_keys=True))
        print("Done!")
        for album in self.library:

            for song in album["songs"]:
                try:
                    count = count + 1

                    info = {
                            "album": album["name"],
                            "artist": self.artist,
                            "title": song,
                            }

                    if os.path.exists("Music/{}/{}/{}.mp3".format(info["artist"], info["album"], info["title"])):
                        print("Skipping song (already have it)")
                        continue
                    querry = "{} {} audio".format(info["title"], info["artist"], info["album"])
                    url = self.search(querry)
                    self.ydl_opts["outtmpl"] = "Music/{}/{}/{}.%(ext)s".format(info["artist"], info["album"], info["title"])
                    self.download(url)
                    print("{} - {} - Song {}/{}".format(info["title"], info["artist"], count, self.total_songs))
                except KeyboardInterrupt:
                    raise KeyboardInterrupt
                except Exception as e:
                    print("ERROR!!!")
                    print(e)
                    continue

        print("Thats all folks! Happy Listening!!")

    def search(self, querry):
        query_string = urllib.parse.urlencode({"search_query" : querry})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
        #print(search_results)
        video_link = "http://www.youtube.com/watch?v=" + search_results[0]
        return video_link


class MyLogger(object):
    def debug(self, msg):
        print(msg)
        pass

    def warning(self, msg):
        print(msg)
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')
        pass


print("Starting up...")
artists = []
with open("artists.txt") as f:
    for line in f:
        line = line.replace("\n", "")
        if len(line) > 2 and "$" not in line:
            #print(line)
            artists.append(line)
for artist in artists:
    try:
        stream = Skizo(lastFM_key, artist)
    except Exception as e:
        print(e)
        continue
# print("Enter an artist (press ENTER)")
# querry = input()
# if len(self.querry) < 2:
#     self.querry = None
#self.get_queue()
