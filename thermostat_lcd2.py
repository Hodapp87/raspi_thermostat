#!/usr/bin/env python3

import asyncio

import time
import sys
import os

import aiofiles
import RPi.GPIO as GPIO
import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd

def main(argv):
    if len(sys.argv) != 2:
        print("Usage: {0} <1-wire temperature sensor>".format(sys.argv[0]))
        sys.exit(-1)
    asyncio.run(start(argv))

async def start(argv):
    lcd_columns = 16
    lcd_rows = 2
    print("Init LCD...")
    i2c = busio.I2C(board.SCL, board.SDA)
    lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
    lcd.color = [255, 0, 0]
    lcd.blink = True
    async def monitor_buttons():
        while True:
            await asyncio.sleep(0.1)
            if lcd.left_button:
                print("Left button")
            if lcd.right_button:
                print("Right button")
            if lcd.up_button:
                print("Up button")
            if lcd.down_button:
                print("Down button")
            if lcd.select_button:
                print("Select button")
                lcd.color = [255, 0, 0]
                await asyncio.sleep(10)
                lcd.color = [0, 0, 0]
    async def idle_backlight():
        await asyncio.sleep(10)
        lcd.color = [0, 0, 0]
    asyncio.create_task(idle_backlight())
    asyncio.create_task(monitor_buttons())
    try:
        # 31.5, 32.0
        t = Thermostat(fname_1w = sys.argv[1] + "/w1_slave",
                       temp_low = 39.5,
                       temp_hi  = 40.0,
                       heater_gpios = [12])
        async for temp, state in t.feedback_loop():
            descr = t.state_descr(state)
            print("{0}: {1:.2f} C, {2}".format(
                time.strftime("%c"), temp, descr))
            lcd.clear()
            lcd.message = "{0:6.1f} C\n{1}".format(temp, descr)
    finally:
        lcd.clear()
        lcd.color = [0, 0, 0]

async def averager(gen, count=4):
    vals = []
    async for val in gen:
        vals.append(val)
        if len(vals) >= count:
            avg = sum(vals) / float(len(vals))
            vals = []
            yield avg

class Thermostat(object):

    STATE_COOLING = 0
    STATE_HEATING = 1
    
    def __init__(self, fname_1w, temp_low, temp_hi, heater_gpios):
        self.fname_1w = fname_1w
        self.temp_low = temp_low
        self.temp_hi = temp_hi
        self.heater_gpios = heater_gpios
        GPIO.setmode(GPIO.BCM)
        for gpio in self.heater_gpios:
            print("Init pin {}...".format(gpio))
            GPIO.setup(gpio, GPIO.OUT, initial=GPIO.LOW)

    async def temperatures(self, timeout=30):
        deadline = None
        while True:
            if deadline is not None and time.monotonic() > deadline:
                raise Exception("Timed out waiting on temperature")
            async with aiofiles.open(self.fname_1w) as tempfile:
                text = await asyncio.wait_for(tempfile.read(), timeout)
            text = text.split("\n")
            # Bad CRC:
            if text[0].endswith("NO"):
                continue
            data = text[1].split(" ")[9]
            temp_c = float(data[2:]) / 1000.0
            deadline = time.monotonic() + timeout
            yield temp_c

    def state_descr(self, state):
        if state == Thermostat.STATE_COOLING:
            return "Cool to {:.1f}".format(self.temp_low)
        elif state == Thermostat.STATE_HEATING:
            return "Heat to {:.1f}".format(self.temp_hi)
        
    def set_heat(self, on=True):
        print("Turning heat {}".format("on" if on else "off"))
        for gpio in self.heater_gpios:
            GPIO.output(gpio, 1 if on else 0)

    async def feedback_loop(self):
        try:
            print("Starting feedback loop!")
            state = Thermostat.STATE_COOLING
            async for temp in averager(self.temperatures()):
                if state == Thermostat.STATE_COOLING:
                    if temp < self.temp_low:
                        state = Thermostat.STATE_HEATING
                        self.set_heat(True)
                elif state == Thermostat.STATE_HEATING:
                    if temp > self.temp_hi:
                        state = Thermostat.STATE_COOLING
                        self.set_heat(False)
                else:
                    raise Exception("Unknown state!")
                yield temp, state
        finally:
            self.set_heat(False)

if __name__ == "__main__":
    main(sys.argv)
