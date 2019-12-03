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

lastFM_key= "2d9810389d8e5c0692d4c7d9908def84"

#t = threading.Thread(target=cake_server, args = (chat_message.from_jid, chat_message.body, chat_message.from_jid)).start()


class Skizo:
    def __init__(self, LFM_key):

        self.current = 0
        self.prevsongs = []
        self.playing = None
        self.queue = []
        self.songpool = []
        self.nowplaying = None
        self.LFM_key = LFM_key
        self.songs = self.get_saved_songs()

        #https://github.com/ytdl-org/youtube-dl/blob/3e4cedf9e8cd3157df2457df7274d0c842421945/youtube_dl/YoutubeDL.py#L161
        self.ydl_opts = {
            'format': 'bestaudio/best',
            "outtmpl": "songs/%(title)s.%(ext)s",
            "verbose": False, #set to true for debugging logs
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'logger': MyLogger(),
            'progress_hooks': [my_hook],
        }

        self.start()

    def start(self):
        print("Enter an artist or leave blank for a surprise (press ENTER)")
        self.querry = input()
        if len(self.querry) < 2:
            self.querry = None
        self.get_queue()

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
        query_string = urllib.parse.urlencode({"artist" : artist, "api_key": lastFM_key, "format": "json"})
        #print(query_string)
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["toptracks"]["track"]

    def get_similar(self, song):
        query_string = urllib.parse.urlencode({"artist" : song["artist"], "track": song["track"], "api_key": lastFM_key, "format": "json"})
        #print(query_string)
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["similartracks"]["track"]

    def download(self, url):
        try:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                #print(url)
                ydl.download([url])
                info = ydl.extract_info("{}".format(url))
                title = info.get("title", None)
                return title
            #youtube-dl -f bestaudio --extract-audio --audio-format mp3 --audio-quality 0 <Video-URL>
            # subprocess.Popen(["youtube-dl", "-f", "bestaudio", "--extract-audio", "--audio-format", "wav", "--audio-quality", "3", url])
            # return "title"#self.get_title(url)
        except:
            print("Download Error!")


    def get_title(self, url):
        #https://github.com/ytdl-org/youtube-dl/blob/master/README.md#output-template
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info("{}".format(url))
            return info.get("title", None)
            #print(title)

    def get_queue(self):
        while len(self.queue) < 16:
            try:
                if len(self.songpool) < 1 and self.querry is None:
                    self.songpool = self.get_similar(self.nowplaying)
                elif self.querry is not None:
                    self.songpool = self.find_song_by_artist(self.querry)
                    #print(self.songpool)
                    self.querry = None
                    similar_song = random.choice(self.songpool)
                    self.songpool.remove(similar_song)
                    #print(similar_song)
                    querry = "{} {}".format(similar_song["name"], similar_song["artist"]["name"])
                    url = self.search(querry)
                    title = self.download(url)
                    song = {
                            "artist": similar_song["artist"]["name"].replace("'", ""),
                            "track": similar_song["name"].replace("'", ""),
                            "title": title,
                            "url": url
                        }
                    self.save_song(song)
                    self.queue.append(song)
                    print("Added {} - by {} to Queue".format(song["track"], song["artist"]))
                    time.sleep(5)
                    self.next()

                    continue
                #else:
                    #self.songpool = self.get_similar(random.choice(self.songs["songs"]))

                similar_song = random.choice(self.songpool)
                self.songpool.remove(similar_song)
                #print(similar_song)
                querry = "{} {}".format(similar_song["name"], similar_song["artist"]["name"])
                url = self.search(querry)
                title = self.download(url)
                song = {
                        "artist": similar_song["artist"]["name"].replace("'", ""),
                        "track": similar_song["name"].replace("'", ""),
                        "title": title,
                        "url": url
                    }
                self.save_song(song)
                self.queue.append(song)
                print("Added {} - by {} to Queue".format(song["track"], song["artist"]))
                if self.nowplaying is None:
                    time.sleep(5)
                    self.next()
            except Exception as e:
                print("\n\n\n\n\n\nError in get_queue():")
                traceback.print_exc()

    def play(self):
        try:
            self.prevsongs.append(self.nowplaying)
            #self.save_song(self.nowplaying)
            print("Now Playing {} - by {}".format(self.nowplaying["track"], self.nowplaying["artist"]))
            playsound('songs/{}.mp3'.format(self.nowplaying["title"]))
            self.next()
        except Exception as e:
            print("\n\n\n\n\n\nError in play():")
            traceback.print_exc()
            time.sleep(5)
            self.nowplaying = None
            self.next()
            pass

    def next(self):
        #play self.queue[0] in a thread

        # if self.playing is None or !self.nowplaying.isAlive():
        #     self.playing = threading.Thread(target=self.play, args = ()).start()
        self.nowplaying = self.queue[0]
        self.queue.remove(self.queue[0])
        self.playing = threading.Thread(target=self.play, args = ()).start()
        self.get_queue()

    def search(self, querry):
        query_string = urllib.parse.urlencode({"search_query" : querry})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
        video_link = "http://www.youtube.com/watch?v=" + search_results[0]
        return video_link


class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        #print('Done downloading, now converting ...')
        pass


stream = Skizo(lastFM_key)
