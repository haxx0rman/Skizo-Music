import youtube_dl
from playsound import playsound

# Application name	Streamer
# API key	2d9810389d8e5c0692d4c7d9908def84
# Shared secret	d37c1888bff0823a32acb8336629288b
# Registered to	mickyfubu

import urllib.request
import urllib.parse
import re

lastFM_key= "2d9810389d8e5c0692d4c7d9908def84"

def get_similar(song):
    query_string = urllib.parse.urlencode({"artist" : song["artist"], "track": song["track"], "api_key": lastFM_key, "format": "json"})
    print(query_string)
    html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&" + query_string)
    print(html_content.read().decode())
    search_results = html_content.read().decode()
    #video_link = "http://www.youtube.com/watch?v=" + search_results[0]
print("Enter song name: ")
query_string = urllib.parse.urlencode({"search_query" : input()})
html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode())
video_link = "http://www.youtube.com/watch?v=" + search_results[0]

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')




ydl_opts = {
    'format': 'bestaudio/best',
    "outtmpl": "songs/%(title)s.%(ext)s",
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
        'preferredquality': '192',
    }],
    'logger': MyLogger(),
    'progress_hooks': [my_hook],
}
with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    ydl.download([video_link])
    info = ydl.extract_info("{}".format(video_link))
    title = info.get("title", None)
    print(title)
    playsound('songs/{}.wav'.format(title))
    get_similar({"track": "bang bang", "artist": "nancy sinatra"})
