#!/usr/bin/env python3

import raspi_1w_temp

import RPi.GPIO as GPIO
import time
import rrdtool
import sys
import os

import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd

if len(sys.argv) != 3:
    print("Usage: {0} <1-wire temperature sensor> <RRD log file>".format(sys.argv[0]))
    sys.exit(-1)

import web_ui

rrdfile = sys.argv[2]
if not os.path.isfile(rrdfile):
    r = rrdtool.create(
        rrdfile,
        "--step", "1",
        "DS:temp_c:GAUGE:15:0:100",
        "DS:temp_deriv:GAUGE:15:0:100",
        "DS:heater:GAUGE:15:0:1",
        "RRA:LAST:0.5:8:1800",
        "RRA:MIN:0.5:60:3600",
        "RRA:MAX:0.5:60:3600",
        "RRA:AVERAGE:0.5:60:3600",
    )

#temp_l = 44.0
#temp_h = 44.3
temp_l, temp_h = 32.0, 32.2
web_ui.temp_l.value = temp_l
web_ui.temp_h.value = temp_h

# Number of consecutive samples to average for a reading:
average_count = 8

# Maximum length of time to allow heater on for in seconds:
heater_max_on = 1200

# Required cooldown multiplier (the time the heater was on is
# multiplied by this to determine the delay until it can power
# on again):
cooldown_multiplier = 0.3

def trigger_l():
    GPIO.output(12, 0)
    #GPIO.output(8, 0)

def trigger_h():
    GPIO.output(12, 1)
    #GPIO.output(8, 1)

def off():
    GPIO.output(12, 1)
    #GPIO.output(8, 1)

GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT, initial=GPIO.HIGH)
#GPIO.setup(8, GPIO.OUT, initial=GPIO.HIGH)

# Main feedback:
def check_temp(state, temp_c, derivative):
    if not state and temp_c < temp_l:
        state = 1
        print("Below threshold ({0} C), turning on".format(temp_l))
        web_ui.heater_status.value = 1
        trigger_l()
    if state and temp_c > temp_h:
        state = 0
        print("Above threshold ({0} C), turning off".format(temp_h))
        web_ui.heater_status.value = 0
        trigger_h()
    return state

state = 0
try:
    fname = sys.argv[1] + "/w1_slave"
    readings = []
    last_tmp_avg_c = None
    last_time_avg = None
    tmp_avg_c = None
    time_avg = None
    heat_time_on = None
    heat_accum = 0
    cooldown_wait = 0
    last_time = time.time()
    lcd_columns = 16
    lcd_rows = 2
    i2c = busio.I2C(board.SCL, board.SDA)
    lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
    for temp_c in raspi_1w_temp.gen_temp_c(fname):
        #temp_f = c2f(temp_c)
        #print("{0}: {1:.3f} (C), {2}".format(time.strftime("%c"), temp_c, "on" if state else "off"))
        sys.stdout.write(".")
        sys.stdout.flush()
        readings.append(temp_c)
        if len(readings) >= average_count:
            last_tmp_avg_c = tmp_avg_c
            last_time_avg = time_avg
            time_avg = time.time()
            tmp_avg_c = sum(readings) / float(len(readings))
            web_ui.temp_current.value = tmp_avg_c
            readings = []
            if last_time_avg is not None:
                derivative = (tmp_avg_c - last_tmp_avg_c) / (time_avg - last_time_avg)
                r = rrdtool.update(rrdfile, "N:{0}:{1}:{2}".format(
                    temp_c, state, derivative))
                dt = time.time() - last_time
                est = None
                if state == 1:
                    heat_accum += dt
                    web_ui.heater_time.value = heat_accum
                    if derivative > 0:
                        est = (temp_h - tmp_avg_c) / derivative
                if state == 0 and cooldown_wait > 0:
                    cooldown_wait = max(cooldown_wait - dt, 0)
                    web_ui.cooldown_time.value = cooldown_wait
                print("{0}: {1:.3f} (C) ({2:f} C/s), heater {3}".format(
                    time.strftime("%c"), tmp_avg_c, derivative,
                    "on ({0:.1f} sec)".format(heat_accum) if state else "off ({0:.1f} sec left to cool)".format(cooldown_wait)))
                if est is not None:
                    print("Est remaining: {:.1f} sec".format(est))
                lcd.clear()
                lcd.message = ("{1:6.2f} C\n{3}".format(
                    time.strftime("%c"), tmp_avg_c, derivative,
                    "on, {0:4d} sec".format(int(heat_accum)) if state else "off, cool {0:4d} sec".format(int(cooldown_wait))))
                if False and heat_accum > heater_max_on:
                    cooldown_wait = cooldown_multiplier * heat_accum
                    web_ui.cooldown_time.value = cooldown_wait
                    heat_accum = 0
                    web_ui.heater_status.value = 0
                    web_ui.heater_time.value = heat_accum
                    print("Heater exceeded duty cycle - powering off for {0:.1f} sec".format(cooldown_wait))
                    trigger_h()
                    state = 0
                if cooldown_wait == 0:
                    state = check_temp(state, tmp_avg_c, derivative)
                last_time = time.time()
                web_ui.last_update.value = int(last_time)
finally:
    off()

# Debug notes
# To turn off LCD: lcd.color = [0,0,0]
