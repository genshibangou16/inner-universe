import pigpio           # import Raspberry Pi's pin library
import time             # import library for sleep function
import numpy as np      # import library for blank screen function
import os               # import library for environment varieties
import cv2              # import library for display movie function
import simpleaudio      # import library for audio function
import requests         # import library for send request to webhock
import subprocess       # import library for hide mouse cursore
from concurrent.futures import ThreadPoolExecutor   # import library for multi-thread

RESET_PIN = 3           # set read pin for reset
DOOR_PIN = 4            # set read pin of sensing a door

pi = pigpio.pi()        # initialize pigpio

pi.set_mode(DOOR_PIN, pigpio.INPUT)     # set pigpio pin mode as input (read level of the pin)
pi.set_mode(RESET_PIN, pigpio.INPUT)

os.environ['DISPLAY'] = ':0'            # select output display
unclutter = subprocess.Popen(['unclutter', '-idle', '0.1', '-root'])    # hide mouse cursore

# Playback related functions
class Playback:
    height = 720    # set height of blank screen
    width = 1280    # set width of blank screen
    black = np.zeros((height, width, 3))    # generate color info of (0, 0, 0) on each pixel
    status = True   # a flag for the exhibition is running
    def stop(self):             # play -> blank
        self.is_blank = True    # a flag for screen status
    def play(self):             # blank -> play
        self.is_blank = False
    def halt(self):             # stop all playback: terminate window then back to the desktop
        self.status = False     # = the main program received a stop signal
    def audio(self):            # audio related functions
        wav = simpleaudio.WaveObject.from_wave_file('./audio.wav') # load WAV file
        self.start = time.perf_counter()                        # time when the audio started playing
        return wav.play()                                       # return playing instance
    def main(self):             # main function of playback
        cv2.namedWindow('Video', cv2.WINDOW_NORMAL)             # open window for video
        cv2.setWindowProperty('Video', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)  # make the window full screen
        while True:             # repeat during the exhibition
            self.is_blank = True                                # darkness was upon the face of the deep
            cv2.imshow('Video', self.black)                     # display blank screen
            while self.is_blank and self.status:                # continue blank screen while the flags are true
                cv2.waitKey(1)                                  # 1 blank frame
            # break loop

            executer_audio = ThreadPoolExecutor()
            play_obj = executer_audio.submit(self.audio)        # start playing audio
            ####
            ## in python, cv2 cannot play movie with audio
            ## play audio by executing it in parallel threads
            ####

            print('VIDEO START')

            cap = cv2.VideoCapture(r'./video.mp4')              # load movie
            count = 0                                           # frame founter
            while cap.isOpened():                               # repeat until the movie ended
                ret, frame = cap.read()                         # load current frame
                cf = (time.perf_counter() - self.start) * 24    # calculate the appropriate frame based on time
                if count < cf:      # if calculated frame is larger than the actual frame
                    count += 1      # increase the count
                    continue        # break current loop: skip current frame
                ####
                ## actual playback speed is slower than the original due to raspi's hardware restriction
                ## to sync video and audio, skip some frames if the current frame is behind then calculate
                ####
                if ret and not self.is_blank and self.status:   # if playback should be continue
                    cv2.imshow('Video', frame)                  # display the currect frame
                    cv2.waitKey(1)                              # 1 frame
                else:                                           # else playback should be ended
                    break                                       # break loop: end playback -> blank screen
                count += 1                                      # increase the count

            print('VIDEO END')

            if play_obj.result().is_playing():  # if audio is still playing
                play_obj.result().stop()        # stop playing audio
            executer_audio.shutdown()           # shutdown sub thread
            cap.release()                       # free loaded movie
            if not self.status:                 # if main program received stop signal
                break                           # end playback: return to desktop
        cv2.destroyAllWindows()                 # close all window

class Roop:
    global DOOR_PIN
    status = True                   # a flag of exhibition is runnning
    aurora_status = False
    strip_status = False
    is_in = False                   # a flag of whether people are inside or not
    def off(self):
        if self.aurora_status:
            self.kick(0, 0, True)
        if self.strip_status:
            self.kick(1, 0, True)
    def reset(self):
        self.is_in = False
        if not self.pause:
            self.off()
            self.end()
    def halt(self):
        self.status = False
        self.off()
        self.end()
    def wait_in(self):                      # a function of wait going IN
        if pi.read(DOOR_PIN):               # if the door is closed
            while pi.read(DOOR_PIN):        # wait until door is opened
                time.sleep(0.1)
            self.pause = False
            self.is_in = True
            print('GOING IN')
        else:                               # else the door is opened
            while not pi.read(DOOR_PIN):    # wait until door is closed
                time.sleep(0.1)
            self.wait_in()                  # closed, then wait until open
    def wait_out_exac(self):        # a function of wait going OUT
        if self.pause:              # if paused: reset button is pushed
            return
        if pi.read(DOOR_PIN):       # if the door is closed
            while pi.read(DOOR_PIN) and not self.pause:     # wait until the door is opened
                time.sleep(0.1)
            print('GOING OUT')
            self.pb.stop()
            self.is_in = False
            self.reset()
        else:                       # else the door is opened
            while not pi.read(DOOR_PIN) and not self.pause: # wait until the door is closed
                time.sleep(0.1)
            self.wait_out_exac()    # closed, then wait until open
    def wait_out(self):
        executer_wait = ThreadPoolExecutor()
        executer_wait.submit(self.wait_out_exac)
        return executer_wait
    def end(self):
        self.pause = True
        if self.is_in:
            self.wo.shutdown()
    def kick(self, d: int, m: int, f = False):
        if self.pause and not f:
            return
        if d:
            if m:
                triger = 'strip_on'
                self.strip_status = True
            else:
                triger = 'strip_off'
                self.strip_status = False
        else:
            if m:
                triger = 'aurora_on'
                self.aurora_status = True
            else:
                triger = 'aurora_off'
                self.aurora_status = False
        url = "https://maker.ifttt.com/trigger/" + triger + "/json/with/key/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        requests.get(url)
        print(triger)
    def sleep(self, s: int):
        for i in range(s):
            if self.pause:
                return
            time.sleep(1)
    def main(self, pb):
        self.pb = pb
        while True:
            # 点灯や再生云々の展示系スクリプト
            self.wait_in()
            self.wo = self.wait_out()
            self.kick(1, 1)
            self.kick(0, 1)
            self.sleep(4) #2
            if not self.pause:
                pb.play()       # duration: 95s
            self.sleep(3)
            self.kick(0, 0)     # turn off aurora AFTER START of the video
            self.sleep(7)
            self.kick(1, 0)     # turn off strip AFTER START of the video
            self.sleep(67)
            self.kick(0, 1)     # turn on aurora BEFORE END of the video
            self.sleep(11)
            self.kick(0, 0)     # turn off aurora AFTER END of the video
            print('THE END')
            if not self.status:
                break
            while self.is_in and not self.pause:
                time.sleep(0.5)
            self.end()

class Reset:
    global RESET_PIN
    status = True
    def halt(self):
        self.status = False
    def main(self, pb, rp):
        while True:
            if pi.read(RESET_PIN):
                while pi.read(RESET_PIN) and self.status:
                    time.sleep(1)
            else:
                while not pi.read(RESET_PIN) and self.status:
                    time.sleep(1)
            print('RESET')
            pb.stop()
            rp.reset()
            if not self.status:
                break

try:
    pb = Playback()
    rp = Roop()
    rst = Reset()
    executer_pb = ThreadPoolExecutor()
    executer_pb.submit(pb.main)
    executer_rst = ThreadPoolExecutor()
    executer_rst.submit(rst.main, pb, rp)
    rp.main(pb)
except KeyboardInterrupt:
    print()
    rst.halt()
    pb.halt()
    rp.halt()
    executer_pb.shutdown()
    executer_rst.shutdown()
    unclutter.kill()
