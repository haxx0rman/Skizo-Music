import youtube_dl
from requests import get
import numpy as np
import pyaudio
import wave
import time
from pynput import keyboard
import urllib.request
import urllib.parse
import json
import random
import threading
import traceback

lastFM_key= "2d9810389d8e5c0692d4c7d9908def84"


class Skizo:
    def __init__(self, LFM_key):
        self.dev_mode = False
        self.filetype = "wav"
        self.queue_limit = 20
        if self.dev_mode:
            self.debug = True
            self.warn = True
            self.err = True
            self.chatter = False
            self.chatter = True # very annoying and largely unnecessary
        else:
            self.debug = False
            self.warn = False
            self.err = True
            self.chatter = False
            #self.chatter = True
        self.log = WatchDog("SKIZO", self.debug, self.warn, self.err, self.chatter)
        self.current = 0
        self.playlist = []
        self.paused = False    # global to track if the audio is self.paused
        self.skip = False
        # The key combination to check
        self.skip_combo = {keyboard.Key.right, keyboard.Key.ctrl}
        self.pause_combo = {keyboard.Key.space, keyboard.Key.ctrl}
        self.term_combo = {keyboard.Key.esc, keyboard.Key.ctrl}
        # The currently active modifiers
        self.current = set()
        self.queue = []
        self.LFM_key = LFM_key
        self.songs = self.get_saved_songs()
        self.term = False
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False if self.dev_mode else True,
            "outtmpl": "songs/%(title)s.%(ext)s",
            "verbose": self.dev_mode, #set to true for debugging logs
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.filetype,
                'preferredquality': '192',
            }],
            'logger': WatchDog("YDL", self.debug, self.warn, self.err),
            'progress_hooks': [self.hook],
        }
        self.modes = [
            #{"id": "0", "name": "Autopilot", "alias": "auto"},
            {"id": "1", "name": "Shuffle", "alias": "shuf"},
            {"id": "2", "name": "Discography", "alias": "disco"},
            {"id": "3", "name": "Similarity", "alias": "sim"}]
        self.mode = self.pick_mode()

        if self.mode == "auto":
            self.init_auto()
        elif self.mode == "shuf":
            self.init_shuf()
        elif self.mode == "disco":
            self.init_disco()
        elif self.mode == "sim":
            self.init_sim()

    def init_auto(self):
        pass

    def init_shuf(self):
        if len(self.songs) > 3:
            self.log.main("Shuffle mode will play from current library...")
            random.shuffle(self.songs)
            self.queue = self.songs
            self.log.chatter("Queue: {}".format(self.queue))
            self.main_loop()
        else:
            self.log.main("You do not yet have enough songs for this mode. Please select another.")
            self.pick_mode()


    def init_disco(self):
        self.log.main("Discography mode allows you to input an artist and exclusively play their music.")
        self.log.main("Enter an artist to start playing their Discography (press ENTER)")
        querry = input()
        self.log.debug("Artist entered: {}".format(querry))
        if len(querry) < 1:
            self.log.main("Please enter a valid request.")
            self.init_disco()
        else:
            self.playlist = self.get_discography(querry)
            self.main_loop()

    def init_sim(self):
        self.log.main("Similarity mode allows you to input a song or artist to play similar music..")
        self.log.main("Enter an artist or song to start playing. (press ENTER)")
        querry = input()
        self.log.debug("Artist entered: {}".format(querry))
        if len(querry) < 1:
            self.log.main("Please enter a valid request.")
            self.init_sim()
        else:
            r = self.search(querry)

        if r['type'] == 'song':
            self.log.main("Search resulted in a best guess of the song {} by {}".format(r['track'], r['artist']))
            self.playlist = self.get_similar_songs(r)
        else:
            self.log.main("Search resulted in a best guess of the artist {}".format(r['name']))
            songs = []
            farts = self.get_similar_artists(r)
            for x in farts:
                for i in self.get_discography(x['name']):
                    self.playlist.append(i)
                time.sleep(.1)

        self.main_loop()

    def pick_mode(self):
        mode = None
        self.log.main("Please select which mode you'd like to operate in. (press ENTER)")
        for x in self.modes:
            self.log.main("{} - {}".format(x["id"], x["name"]))

        m = input()
        try:
            m = int(m)
        except:
            pass
        for x in self.modes:
            if m is int(x["id"]):
                self.log.main("You have selected {} mode.".format(x["name"]))
                mode = x['alias']

        if mode is None:
            self.log.main("Please input a valid integer coresponding to your desired mode.")
            self.pick_mode()
        return mode

    def main_loop(self):
        self.log.debug("Starting main loop")
        self.log.main("Skip song: (CTRL + ->) Pause: (CTRL + SPACE) Quit: (CTRL + ESC)")
        random.shuffle(self.playlist)
        self.log.main("Loading. This may take a moment...")
        if self.mode == "disco" or self.mode == "sim":
            q = SmartThread(target=self.load_queue, args = ())
            q.start()
        while not self.term:
            if len(self.queue) > 0:
                try:
                    self.log.main("Now Playing {} - by {}".format(self.queue[0]["track"], self.queue[0]["artist"]))
                    file = 'songs/{}.{}'.format(self.queue[0]["querry"], self.filetype)
                    del self.queue[0]
                    self.wf = wave.open(file, 'rb')
                    self.p = pyaudio.PyAudio()
                    self.stream = self.p.open(format=self.p.get_format_from_width(self.wf.getsampwidth()),
                        channels=self.wf.getnchannels(),
                        rate=self.wf.getframerate(),
                        output=True,
                        stream_callback=self.callback)

                    # start the stream
                    self.stream.start_stream()
                    try:
                        while self.stream.is_active() or self.paused==True or self.skip:
                            with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as self.listener:
                                if self.skip or self.term:
                                    self.skip = False
                                    break
                                self.listener.join()
                            time.sleep(0.1)
                    except Exception as e:
                        self.log.main("Skipping Song...")
                    # stop stream
                    self.listener.stop()
                    self.stream.stop_stream()
                    self.stream.close()
                    self.wf.close()
                    # close PyAudio
                    self.p.terminate()
                    if self.term:
                        self.log.main("Shutting down. This may take a moment...")
                        return
                except KeyboardInterrupt as e:
                    self.log.main("Shutting down. This may take a moment...")
                    self.term = True
                    # stop stream
                    self.stream.stop_stream()
                    self.stream.close()
                    self.wf.close()
                    # close PyAudio
                    self.p.terminate()
                    return
                except Exception as e:
                    self.log.error("Trouble playing file: {} \nException: {}".format(file, traceback.format_exc()))
                    time.sleep(1)
            else:
                try:
                    time.sleep(5)
                except:
                    self.log.main("Shutting down. This may take a moment...")
                    self.term = True
                    return

    def get_saved_songs(self):
        try:
            with open('songs.json') as f:
                data = json.load(f)
            if data["songs"]:
                return data["songs"]
            else:
                return []
        except:
            return []

    def save_song(self, song):
        if song is not None:
            self.songs.append(song)
            with open('songs.json', 'w') as outfile:
                json.dump({ "songs": self.songs }, outfile, indent=4, sort_keys=True)

    def get_discography(self, artist):
        query_string = urllib.parse.urlencode({"artist" : artist, "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["toptracks"]["track"]

    def search(self, querry):
        data = []
        bulk = []
        query_string = urllib.parse.urlencode({"track" : querry, "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.search&" + query_string)
        res = str(html_content.read().decode())
        track_data = json.loads(res)
        tracks = track_data['results']['trackmatches']['track']
        for x in tracks:
            data.append(x['name'])
            bulk.append(x)

        query_string = urllib.parse.urlencode({"artist" : querry, "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.search&" + query_string)
        res = str(html_content.read().decode())
        artist_data = json.loads(res)
        artists = artist_data['results']['artistmatches']['artist']
        for x in artists:
            data.append(x['name'])
            bulk.append(x)

        high = 99
        best_guess = ""
        for item in bulk:
            dist = levenshtein_ratio_and_distance(querry, item['name'])
            if dist < high:
                best_guess = item
                high = dist


        if 'artist' in best_guess.keys():
            result = {
                'type': 'song',
                'track': best_guess['name'],
                'artist': best_guess['artist']
            }

        else:
            result = {
                'type': 'artist',
                'name': best_guess['name']
            }

        return result


    def get_similar_songs(self, song):
        query_string = urllib.parse.urlencode({"artist" : song["artist"], "track": song["track"], "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["similartracks"]["track"]

    def get_similar_artists(self, artist):
        query_string = urllib.parse.urlencode({"artist" : artist['name'], "api_key": lastFM_key, "format": "json"})
        html_content = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&" + query_string)
        res = str(html_content.read().decode())
        data = json.loads(res)
        return data["similarartists"]["artist"]

    def download(self, querry):
        try:
            self.ydl_opts["outtmpl"] = "songs/{}.%(ext)s".format(querry)
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                try:
                    get(querry)
                except:
                    video = ydl.extract_info(f"ytsearch:{querry}", download=True)['entries'][0]
                else:
                    video = ydl.extract_info(querry, download=True)

                if video:
                    return video
                else:
                    return self.download(querry)
        except Exception as e:
            self.log.debug("Download failed for song: {} Exception: \n {}".format(querry, traceback.format_exc()))

    def load_queue(self):
        for x in self.playlist:
            if self.term:
                self.log.main("Ending processes...")
                return None
            s = self.get_song(x)
            if s:
                self.queue.append(s)
                self.log.debug("Added {} - by {} to Queue".format(s["track"], s["artist"]))


        while len(self.queue) > (self.queue_limit * .25):
            if self.term:
                self.log.main("Ending processes...")
                return None
            time.sleep(5)
        time.sleep(1)
        self.load_queue()

    def get_song(self, song):
        fails = 0
        if fails > 3:
            self.log.error("Failed to fetch song: {} Too many failed attempts. Moving on.".format(querry))
            return None
        try:
            querry = "{} by {}".format(song["name"], song["artist"]["name"])
            for x in self.songs:
                self.log.chatter("Checking if song exists in library... \nComparing {}, and {}".format(querry, x['querry']))
                if querry in x['querry']:
                    self.log.debug("{} is already in the library. Skipping...".format(querry))
                    return x
            video = self.download(querry)
            title = video.get("title", None)
            url = video.get("url", None)
            song = {
                    "artist": song["artist"]["name"].replace("'", ""),
                    "track": song["name"].replace("'", ""),
                    "title": title,
                    "querry": querry
                }
            self.save_song(song)
            self.log.debug("Added {} - by {} to Library".format(song["track"], song["artist"]))
            return song
        except Exception as e:
            self.log.error("Failed to fetch song: {} Exception: \n {}".format(querry, traceback.format_exc()))
            fails = fails + 1
            return None

    def on_press(self, key):
        self.log.chatter(key)
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self.current.add(keyboard.Key.ctrl)
        if key in self.skip_combo:
            self.current.add(key)
        if all(k in self.current for k in self.skip_combo):
            self.log.debug("Key combo for 'Skip Song' Detected")
            self.current = set()
            raise Exception("Skipping song...")
            self.skip = True
            time.sleep(1)


        if key in self.pause_combo:
            self.current.add(key)
        if all(k in self.current for k in self.pause_combo):
            self.log.debug("Key combo for 'Pause Song' Detected")
            if self.stream.is_stopped():     # time to play audio
                self.log.main("Song resumed")
                self.stream.start_stream()
                self.paused = False
            elif self.stream.is_active():   # time to pause audio
                self.log.main("Song paused")
                self.stream.stop_stream()
                self.paused = True
            self.current = set()

        if key in self.term_combo:
            self.current.add(key)
        if all(k in self.current for k in self.term_combo):
            self.log.main("Shutting down. This may take a moment...")
            self.stream.stop_stream()
            self.listener.stop()
            self.term = True
            self.current = set()


    def on_release(self, key):
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.current.remove(keyboard.Key.ctrl)
            self.current.remove(key)
        except KeyError:
            pass

    def callback(self, in_data, frame_count, time_info, status):
        data = self.wf.readframes(frame_count)
        return (data, pyaudio.paContinue)



    def hook(self, d):
        if d['status'] == 'finished':
            self.log.debug('Done downloading, now converting ...')
            pass


class WatchDog(object):
    def __init__(self, alias = "UNNAMED", en_debug = False, en_warn = True, en_err = True, en_chat = False):
        self.alias = alias
        self.en_debug = en_debug
        self.en_warn = en_warn
        self.en_err = en_err
        self.en_chat = en_chat
    def main(self, msg):
        print("{} {}: {}".format(self.alias, "MAIN", msg))

    def debug(self, msg):
        if self.en_debug:
            print("{} {}: {}".format(self.alias, "DEBUGGER", msg))

    def warning(self, msg):
        if self.en_warn:
            print("{} {}: {}".format(self.alias, "WARNING", msg))

    def error(self, msg):
        if self.en_err:
            print("{} {}: {}".format(self.alias, "ERROR", msg))

    def chatter(self, msg):
        if self.en_chat:
            print("{} {}: {}".format(self.alias, "CHATTER", msg))

class SmartThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(SmartThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

def levenshtein_ratio_and_distance(s, t, ratio_calc = False):
    rows = len(s)+1
    cols = len(t)+1
    distance = np.zeros((rows,cols),dtype = int)

    for i in range(1, rows):
        for k in range(1,cols):
            distance[i][0] = i
            distance[0][k] = k

    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0
            else:
                if ratio_calc == True:
                    cost = 2
                else:
                    cost = 1
            distance[row][col] = min(distance[row-1][col] + 1,
                                 distance[row][col-1] + 1,
                                 distance[row-1][col-1] + cost)
    if ratio_calc == True:
        Ratio = ((len(s)+len(t)) - distance[row][col]) / (len(s)+len(t))
        return Ratio
    else:
        # print(distance) # Uncomment if you want to see the matrix showing how the algorithm computes the cost of deletions,
        return int(distance[row][col])

stream = Skizo(lastFM_key)
