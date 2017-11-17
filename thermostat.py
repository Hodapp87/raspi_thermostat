#!/usr/bin/env python

import raspi_1w_temp

import RPi.GPIO as GPIO
import time
import rrdtool
import sys
import os

if len(sys.argv) != 3:
    print("Usage: {0} <1-wire temperature sensor> <RRD log file>".format(sys.argv[0]))

rrdfile = sys.argv[2]
if not os.path.isfile(rrdfile):
    r = rrdtool.create(
        rrdfile,
        "--step", "1",
        "DS:temp_c:GAUGE:3:0:100",
        "DS:heater:GAUGE:3:0:1",
        "RRA:LAST:0.5:1:1800",
        "RRA:MIN:0.5:60:3600",
        "RRA:MAX:0.5:60:3600",
        "RRA:AVERAGE:0.5:60:3600",
    )

temp_l = 44.0
temp_h = 44.3

def trigger_l():
    GPIO.output(7, 0)
    GPIO.output(8, 0)

def trigger_h():
    GPIO.output(7, 1)
    GPIO.output(8, 1)

def off():
    GPIO.output(7, 1)
    GPIO.output(8, 1)

GPIO.setmode(GPIO.BCM)
GPIO.setup(7, GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(8, GPIO.OUT, initial=GPIO.HIGH)

state = 0
try:
    fname = sys.argv[1] + "/w1_slave"
    for temp_c in raspi_1w_temp.gen_temp_c(fname):
        #temp_f = c2f(temp_c)
        print("{0}: {1:.3f} (C), {2}".format(time.strftime("%c"), temp_c, "on" if state else "off"))
        r = rrdtool.update(rrdfile, "N:{0}:{1}".format(temp_c, state))
        if not state and temp_c < temp_l:
            state = 1
            print("Below threshold ({0} C), turning on".format(temp_l))
            trigger_l()
        if state and temp_c > temp_h:
            state = 0
            print("Above threshold ({0} C), turning off".format(temp_h))
            trigger_h()
finally:
    off()
