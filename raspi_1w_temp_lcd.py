#!/usr/bin/env python3

import time
import sys

import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd

def c2f(temp):
    return 9.0 * temp / 5 + 32.0

# Derived from:
# https://www.rs-online.com/designspark/building-a-raspberry-pi-1-wire-thermostat
def gen_temp_c(fname):
    while True:
        tempfile = open(fname)
        text = tempfile.read().split("\n")
        tempfile.close()
        # Bad CRC:
        if text[0].endswith("NO"):
            continue
        data = text[1].split(" ")[9]
        temp_c = float(data[2:]) / 1000.0
        yield temp_c

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: {0} <sysfs file>".format(sys.argv[0]))
        print("e.g. {0} /sys/bus/w1/devices/28-041781932bff".format(sys.argv[0]))
        sys.exit(-1)
    lcd_columns = 16
    lcd_rows = 2
    i2c = busio.I2C(board.SCL, board.SDA)
    lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
    csv = open("temperatures.csv", "a+")
    csv.write("timestamp,datetime,deg_c")
    i = 0
    for temp_c in gen_temp_c(sys.argv[1] + "/w1_slave"):
        temp_f = c2f(temp_c)
        lcd.clear()
        lcd.message = "{:6.2f} F {}".format(temp_f, " " if i%2 else ".")
        print("{0}: {1:.3f} (C), {2:.3f} (F)".format(time.strftime("%c"), temp_c, temp_f))
        csv.write("{0},{1},{2}".format(time.time(), time.strftime("%c"), temp_c))
        i += 1
