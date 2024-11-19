#! /usr/bin/env python3

# pip install flask-sse

from flask import Flask, Response, request
import json
import socket
import time
from gps_api import gps_api
from ntp_api import ntp_api
from plotter import set_cache

from configuration import *


set_cache(use_cache)

n = ntp_api(ntpsec_host, ntpsec_interval, database_file, max_data_age * 86400, max_mru_list_size)
n.daemon = True
n.start()

g = gps_api(gpsd_host, database_file, max_data_age * 86400, hide_position)
g.daemon = True
g.start()

app = Flask(__name__)

@app.route('/gps')
def gps():
    def stream():
        try:
            global g

            q = g.register()

            while True:
                current = q.get()
                yield 'data:' + current + '\n\n'

        except Exception as e:
            print(f'Exception (main): {e}, line number: {e.__traceback__.tb_lineno}')
            yield 'data:' + json.dumps({'error': str(e)}) + '\n\n'

        g.unregister(q)

    return Response(stream(), mimetype="text/event-stream")

@app.route('/ntp')
def ntp():
    def stream():
        global n

        try:
            while True:
                data = n.get_data()

                if len(data) > 0:
                    yield 'data:' + json.dumps(data) + '\n\n'

                time.sleep(3)

        except Exception as e:
            print(f'Exception (main): {e}, line number: {e.__traceback__.tb_lineno}')
            yield 'data:' + json.dumps({'error': str(e)}) + '\n\n'

    return Response(stream(), mimetype='text/event-stream')

@app.route('/graph-data-gps')
def graph_data_gps():
    global g
    table = request.args.get('table', default = '', type = str)
    width = request.args.get('width', default = '600', type = float)
    return Response(g.get_svg(table, width), mimetype='image/svg+xml')

@app.route('/graph-data-ntp')
def graph_data_ntp():
    global n
    table = request.args.get('table', default = '', type = str)
    width = request.args.get('width', default = '600', type = float)
    return Response(n.get_svg(table, width), mimetype='image/svg+xml')

def load_file(file):
    try:
        fh = open(file, 'r')
        page = fh.read()
        fh.close()
        return page
    except Exception as e:
        print(f'Exception (main, for {file}): {e}, line number: {e.__traceback__.tb_lineno}')
    return ''

@app.route('/code.js')
def code():
    global graph_refresh_interval
    interval_string = f'{graph_refresh_interval * 1000}'
    page = load_file('code.js').replace('___REPLACE_ME___', interval_string)
    return Response(page, mimetype="text/javascript")

@app.route('/simple.css')
def css():
    return Response(load_file('simple.css'), mimetype="text/css")

@app.route('/')
def slash():
    return Response(load_file('index.html'), mimetype="text/html")

if __name__ == "__main__":
    app.run(host=listen_interface, port=listen_port, debug=True, threaded=True)
