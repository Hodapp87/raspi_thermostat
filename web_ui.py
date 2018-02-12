import multiprocessing
import datetime
import ctypes

import flask

app = flask.Flask(__name__)

temp_l = multiprocessing.Value('d', 0.0)
temp_h = multiprocessing.Value('d', 0.0)
temp_current = multiprocessing.Value('d', 0.0)
heater_status = multiprocessing.Value('i', 0)
cooldown_time = multiprocessing.Value('d', 0.0)
heater_time = multiprocessing.Value('d', 0.0)
last_update = multiprocessing.Value(ctypes.c_uint64, 0)

@app.route("/")
def info():
    if heater_status.value:
        s1 = "On (for {:.1f} sec total)".format(heater_time.value)
    elif cooldown_time.value > 0.0:
        s1 = "Off (duty-cycle cool for {:.1f} sec)".format(cooldown_time.value)
    else:
        s1 = "Off (waiting for temperature < {:.1f})".format(temp_l.value)
    lines = [
        '<meta http-equiv="refresh" content="30">',
        "<h1>Thermostat monitor thingy</h1>",
        "<p><b>Current Temperature:</b> {:.1f} deg C</p>".format(temp_current.value),
        "<p><b>Last update:</b> {}</p>".format(datetime.datetime.fromtimestamp(last_update.value).strftime("%c")),
        "<p><b>Heater is:</b> {}</p>".format(s1),
    ]
    return "".join(lines)

def run():
    app.run(host='0.0.0.0', port=8080)

def run_process():
    p = multiprocessing.Process(target=run)
    p.start()
    return p

run_process()
