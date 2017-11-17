#!/bin/sh

#--start -3600 --end now \

rrdtool graph ./temp_graph.png \
        -w 800 -h 400 -a PNG \
        --start -4h --end 1510775039 \
        --slope-mode \
        --vertical-label "temperature (°C)" \
        --rigid -u 55 -l 30 \
        DEF:temp_c=./yoghurt_20171115_44_45.rrd:temp_c:AVERAGE \
        DEF:heater=./yoghurt_20171115_44_45.rrd:heater:MAX \
        CDEF:heater2=heater,30,*,30,+ \
        LINE1:temp_c#0000ff:"Temperature" \
        AREA:heater2#ff000030:"Heater"
