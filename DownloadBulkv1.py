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

artists = ["lana del rey", "alt j", "andrew jackson jihad", "elton john", "jeff magnum", "los lobos", "neutral milk hotel", "noah and the whale",
            "nancy sinatra"]
#t = threading.Thread(target=cake_server, args = (chat_message.from_jid, chat_message.body, chat_message.from_jid)).start()


class Skizo:
    def __init__(self, LFM_key, querry):

        self.current = 0
        self.prevsongs = []
        self.queue = []
        self.querry = querry
        self.songpool = []
        self.LFM_key = LFM_key
        self.songs = self.get_saved_songs()

        #https://github.com/ytdl-org/youtube-dl/blob/3e4cedf9e8cd3157df2457df7274d0c842421945/youtube_dl/YoutubeDL.py#L161
        self.ydl_opts = {
            'format': 'bestaudio/best',
            "outtmpl": "songs/%(title)s.%(ext)s",
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
            #print(query_string)
            html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&" + query_string)
            res = str(html_content.read().decode())
            data = json.loads(res)
            data = data["toptracks"]["track"]
            results = results + data
            #print(len(results))
        return results

    def get_similar(self, song):
        query_string = urllib.parse.urlencode({"artist" : song["artist"], "track": song["track"], "api_key": lastFM_key, "format": "json"})
        #print(query_string)
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["similartracks"]["track"]

    def get_song_info(self, artist, song):
        query_string = urllib.parse.urlencode({"artist": artist, "track": song, "api_key": lastFM_key, "format": "json"})
        #print(query_string)
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getinfo&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        #return data["toptracks"]["track"]
        return data

    def download(self, url):
        try:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                #print(url)
                ydl.download([url])
            #youtube-dl -f bestaudio --extract-audio --audio-format mp3 --audio-quality 0 <Video-URL>
            # subprocess.Popen(["youtube-dl", "-f", "bestaudio", "--extract-audio", "--audio-format", "wav", "--audio-quality", "3", url])
            # return "title"#self.get_title(url)
        except Exception as e:
            print("Download Error!")
            print(e)


    def get_title(self, url):
        #https://github.com/ytdl-org/youtube-dl/blob/master/README.md#output-template
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info("{}".format(url))
            return info.get("title", None)
            #print(title)

    # def get_queue(self):
    #     try:
    #         self.songpool = self.find_song_by_artist(self.querry)
    def run(self):
        self.songpool = self.find_song_by_artist(self.querry)
        count = 0
        print("Getting songs...")
        for song in self.songpool:
            try:
                count = count + 1

                raw_info = self.get_song_info(song["artist"]["name"], song["name"])
                #print(json.dumps(info, indent=4, sort_keys=True))
                try:
                    info = {
                            "album": raw_info["track"]["album"]["title"],
                            "artist": raw_info["track"]["artist"]["name"],
                            "title": raw_info["track"]["name"],
                            "thumbnail": raw_info["track"]["album"]["image"][len(raw_info["track"]["album"]["image"]) - 1]
                            }
                except:
                    info = {
                            "album": "Unknown" ,
                            "artist": raw_info["track"]["artist"]["name"],
                            "title": raw_info["track"]["name"]
                            }



                #print(json.dumps(info, indent=4, sort_keys=True))
                if os.path.exists("songs/{}/{}/{}.mp3".format(info["artist"], info["album"], song["name"])):
                    print("Skipping song (already have it)")
                    continue
                querry = "{} {} audio".format(song["name"], song["artist"]["name"], info["album"])
                url = self.search(querry)
                self.ydl_opts["outtmpl"] = "songs/{}/{}/{}.%(ext)s".format(info["artist"], info["album"], song["name"])
                self.download(url)
                print("{} - {} - Song {}/{}".format(song["name"], info["artist"], count, len(self.songpool)))
            except:
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
