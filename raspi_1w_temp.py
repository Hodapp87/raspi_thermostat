#!/usr/bin/env python

import time
import sys

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
    csv = open("temperatures.csv", "a+")
    csv.write("timestamp,datetime,deg_c")
    for temp_c in gen_temp_c(sys.argv[1] + "/w1_slave"):
        temp_f = c2f(temp_c)
        print("{0}: {1:.3f} (C), {2:.3f} (F)".format(time.strftime("%c"), temp_c, temp_f))
        csv.write("{0},{1},{2}".format(time.time(), time.strftime("%c"), temp_c))
