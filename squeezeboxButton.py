from machine import Pin
import urequests
import time
import json
import network
import re
import urandom
from neopixel import NeoPixel

## Constants
PLAY_PAUSE = const(1)
STOP = const(2)
VOL_UP = const(3)
VOL_DN = const(4)
NEXT_SONG = const(5)
PREV_SONG = const(6)
MIN_PRESS_THRESH_MS = const(580)
LONG_PRESS_THRESH_MS = const(800)

## Globals
url = "http://192.168.1.100:9000/jsonrpc.js" ## URL for SqueezeServer  TODO: fill in your ip and port
btnPressed = False

## JSON button type data to send  TODO: fill in your players MAC address
play_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "button", "play" ] ], "id": 0 }
playpause_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "button", "pause.single" ] ], "id": 0 }
status_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "status" ] ], "id": 0 }
stop_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "button", "stop" ] ], "id": 0 }
volup_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "mixer", "volume", "+5"] ], "id": 0 }
voldn_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "mixer", "volume", "-5"] ], "id": 0 }
nextsong_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "button", "fwd.single"] ], "id": 0 }
prevsong_t = { "method": "slim.request", "params": [ "aa:bb:cc:dd:ee:ff", [ "button", "rew.single"] ], "id": 0 }


## TODO: pick your pin for a Neopixel (OPTIONAL)
np_pin = Pin(13, Pin.OUT)   # set GPIO0 to output to drive NeoPixels
np = NeoPixel(np_pin, 8)   # create NeoPixel driver on GPIO0 for 8 pixels

## UTIL Functions
def btn_isr(pin):
  global btnPressed
  btnPressed = True

def do_connect():
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        #print('connecting to network...')
        sta_if.active(True)
        sta_if.connect('YourSSID', 'YourPassPhrase')  ## TODO: type in your username and passphrase
        while not sta_if.isconnected():
            pass
    ## set led green when connected
    np[0] = (0, 222, 0)
    np.write()
    #print('network config:', sta_if.ifconfig())


def handle_btns(btnType):
    print ("handlebtn:"+str(btnType))  ## DEBUG

    ## random color on each press to know something is happening
    np[0] = (urandom.getrandbits(8), urandom.getrandbits(8),urandom.getrandbits(8))
    np.write()

    if btnType == PLAY_PAUSE:
        status = urequests.post(url, data=json.dumps(status_t)).json()
        mode = status['result']['mode']
        if (mode == 'pause'):
            urequests.post(url, data=json.dumps(playpause_t))
        elif (mode == 'play'):
            urequests.post(url, data=json.dumps(playpause_t))
        elif (mode == 'stop'):
            urequests.post(url, data=json.dumps(play_t))
        else:
            urequests.post(url, data=json.dumps(play_t))
    elif btnType == STOP:
        urequests.post(url, data=json.dumps(stop_t))
    elif btnType == VOL_UP:
        urequests.post(url, data=json.dumps(volup_t))
    elif btnType == VOL_DN:
        urequests.post(url, data=json.dumps(voldn_t))
    elif btnType == NEXT_SONG:
        urequests.post(url, data=json.dumps(nextsong_t))
    elif btnType == PREV_SONG:
        urequests.post(url, data=json.dumps(prevsong_t))
    else:
        pass
    gc.collect()


## Setup Button TODO: make sure to use the pin of your choice
## (NODEMCU mapping can be found in the internet forums)
btn = machine.Pin(14, Pin.IN, Pin.PULL_UP)
btn.irq(trigger=Pin.IRQ_FALLING, handler=btn_isr)

## clear the led at boot up
np[0] = (0, 0, 0)
np.write()

gc.enable()
do_connect()

def mainLoop():
    global btnPressed
    pressCount = 0
    longFlag = False

    while True:

        if (pressCount > 0):
            tmpPress = time.ticks_ms()
            delta = tmpPress - lastPress
            if (delta > MIN_PRESS_THRESH_MS):
                ## button sequence must be over, check for long last press
                while (btn.value() == 0) and (longFlag == False):
                    ## TODO: DOES THIS CODE EVEN HIT???
                    #print ("d:"+str(delta))
                    time.sleep_ms(1)
                    tmpPress = time.ticks_ms()
                    delta = tmpPress - lastPress

                #print ("final d:"+str(delta))
                if (delta > LONG_PRESS_THRESH_MS):
                    longFlag = True
        
                if (longFlag):
                    if (pressCount == 1):
                      print("singlePressLong")
                    elif (pressCount == 2):
                      print("doublePressLong")
                    elif (pressCount >= 3):
                      print("triplePressLong")
                else:
                   if (pressCount == 1):
                      handle_btns(PLAY_PAUSE)
                   elif (pressCount == 2):
                      handle_btns(NEXT_SONG)
                   elif (pressCount >= 3):
                      handle_btns(STOP)
                      print("triplePress")

                pressCount = 0
                longFlag = False

        if (btnPressed):
            pressCount += 1
            lastPress = time.ticks_ms()

            keepGoing = True
            while (keepGoing):
                if (btn.value() == 0):
                    tmpPress = time.ticks_ms()
                    delta = tmpPress - lastPress
                    if (delta > LONG_PRESS_THRESH_MS):
                        time.sleep_ms(600)
                        ## Only do this for single and double which are volume control
                        if (pressCount == 1):
                            print(".",end="")  ## single long hold
                            handle_btns(VOL_DN)
                        elif (pressCount == 2):
                            print("=",end="")  ## double long hold
                            handle_btns(VOL_UP)
                elif (btn.value() == 1):
                    ## require three back to back HIGH for cheap debounce
                    time.sleep_ms(10);
                    if (btn.value() == 1):
                        time.sleep_ms(10);
                        if (btn.value() == 1):
                            keepGoing = False
                    time.sleep_ms(10);

            btnPressed = False

            ##tmpPress = time.ticks_ms()
            ##delta = tmpPress - lastPress

        #time.sleep_ms(1);

## Call main loop now
mainLoop()


