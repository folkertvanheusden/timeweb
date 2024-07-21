#! /usr/bin/python3

# pip install flask-sse

from flask import Flask, Response, request
import json
import socket
import time
from gps_api import gps_api
from ntp_api import ntp_api

from configuration import *

n = ntp_api(ntpsec_host, ntpsec_interval, database_file, max_data_age)
n.start()

g = gps_api(gpsd_host, database_file, max_data_age)
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

@app.route('/code.js')
def code():
    global graph_refresh_interval

    code = '''
function mode_to_str(mode) {
    if (mode == "0")
        return "-";
    if (mode == "1")
        return "no fix";
    if (mode == "2")
        return "2D fix";
    if (mode == "3")
        return "3D fix";
    return "?";
}

function refresh_x_graph(target, table) {
    var element = document.getElementById(table);
    var positionInfo = element.getBoundingClientRect();
    var width = positionInfo.width;

    var url = '/graph-data-' + target + '?table=' + table + "&width=" + width;
    console.log('refreshing ' + url)

    var xhr = typeof XMLHttpRequest != 'undefined' ? new XMLHttpRequest() : new ActiveXObject('Microsoft.XMLHTTP');
    xhr.open('get', url, true);
    xhr.onreadystatechange = function() {
        console.log(target + '|' + table + ': ' + xhr.readyState + ' ' + xhr.status);
        if (xhr.readyState == 4 && xhr.status == 200) {
            element.innerHTML = xhr.responseText;
        }
    }
    xhr.send();
}

var interval = %d;

function f_ntp_offset    () { refresh_x_graph('ntp', 'ntp_offset'); }
function f_dop           () { refresh_x_graph('gps', 'dop'); }
function f_pps_clk_offset() { refresh_x_graph('gps', 'pps_clk_offset'); }
function f_polar         () { refresh_x_graph('gps', 'polar'); }

f_ntp_offset();
setInterval(f_ntp_offset, interval);

f_dop();
setInterval(f_dop, interval);

f_pps_clk_offset();
setInterval(f_pps_clk_offset, interval);

f_polar();
setInterval(f_polar, interval);

var eventSourceNTP = new EventSource("/ntp");
eventSourceNTP.onmessage = function(e) {
    const obj = JSON.parse(e.data);

    // sysvars

    let ngtable = '<table>';
    ngtable += '<caption>NTP general</caption>';
    ngtable += '<thead><th>name</th><th>value</th><th>description</th></thead>';
    var poll_ts = new Date(obj['poll_ts'] * 1000);
    ngtable += `<tr><th>poll ts</th><td>${poll_ts}</td><td>when were these values retrieved</td></tr>`;
    for (const [key, value] of Object.entries(obj['sysvars'])) {
        ngtable += `<tr><th>${key}</th><td>${value}</td></tr>`;
    };
    ngtable += '</table>';

    const ngtable_container = document.getElementById('ntp-general-container');
    ngtable_container.innerHTML = ngtable;

    // peers

    let peerstable = '<table>';
    peerstable += '<caption>NTP peers</caption>';
    peerstable += '<thead><th>host</th><th>refid</th><th>stratum</th><th>offset</th><th>jitter</th></thead>';
    for (const [key, value] of Object.entries(obj['peers'])) {
        var host = value.srchost;
        if (host === undefined)
            host = value.srcadr;
        peerstable += `<tr><td>${host}</td><td>${value.refid}</td><td>${value.stratum}</td><td>${value.offset}</td><td>${value.jitter}</td></tr>`;
    };

    peerstable += '</table>';

    const peerstable_container = document.getElementById('ntp-peers-container');
    peerstable_container.innerHTML = peerstable;

    // details for selected peer

    var associd = obj['sysvars']['assoc']

    if (associd !== undefined) {
        let aptable = '<table>';
        aptable += '<caption>details for selected peer</caption>';
        aptable += '<thead><th>name</th><th>value</th></thead>';
        for (const [key, value] of Object.entries(obj['peers'][associd])) {
            aptable += `<tr><th>${key}</th><td>${value}</td></tr>`;
        };
        aptable += '</table>';

        const aptable_container = document.getElementById('ntp-selected-peer-container');
        aptable_container.innerHTML = aptable;
    }
};

var eventSourceGPS = new EventSource("/gps");
eventSourceGPS.onmessage = function(e) {
    const obj = JSON.parse(e.data);
    if (obj['class'] == 'TPV') {
        document.getElementById('status'   ).innerHTML = obj['status'];
        document.getElementById('time'     ).innerHTML = obj['time'  ];
        document.getElementById('mode'     ).innerHTML = mode_to_str(obj['mode'  ]);
        document.getElementById('latitude' ).innerHTML = obj['lat'   ];
        document.getElementById('longitude').innerHTML = obj['lon'   ];
        document.getElementById('altitude' ).innerHTML = obj['alt'   ];
        document.getElementById('epx'      ).innerHTML = obj['epx'   ];
        document.getElementById('epy'      ).innerHTML = obj['epy'   ];
        document.getElementById('epv'      ).innerHTML = obj['epv'   ];
        document.getElementById('ept'      ).innerHTML = obj['ept'   ];
        document.getElementById('eps'      ).innerHTML = obj['eps'   ];
        document.getElementById('eph'      ).innerHTML = obj['eph'   ];
        document.getElementById('epc'      ).innerHTML = obj['epc'   ];
        document.getElementById('magvar'   ).innerHTML = obj['magvar'];
        document.getElementById('speed'    ).innerHTML = obj['speed' ];
        document.getElementById('geoidSep' ).innerHTML = obj['geoidSep'];
        document.getElementById('sep'      ).innerHTML = obj['sep'   ];
        document.getElementById('track'    ).innerHTML = obj['track' ];
    }
    else if (obj['class'] == 'PPS') {
        let ppstable = '<table>';
        ppstable += '<caption>PPS</caption>';
        ppstable += '<thead><th>name</th><th>value</th></thead>';
        for (const [key, value] of Object.entries(obj)) {
            ppstable += `<tr><th>${key}</th><td>${value}</td></tr>`;
        };
        ppstable += '</table>';

        const ppstable_container = document.getElementById('pps-container');
        ppstable_container.innerHTML = ppstable;
    }
    else if (obj['class'] == 'SKY') {
        // general data
        document.getElementById('hdop').innerHTML = obj['hdop'];
        document.getElementById('pdop').innerHTML = obj['pdop'];
        document.getElementById('vdop').innerHTML = obj['vdop'];
        document.getElementById('nsat').innerHTML = obj['nSat'];
        document.getElementById('usat').innerHTML = obj['uSat'];

        // list of satellites
        let stable = '<table>';
        stable += '<caption>satellite details</caption>';
        stable += '<thead><th>PRN ID</th><th>azimuth</th><th>elevation</th><th>gnssid</th><th>signal strength</th><th>svid</th><th>in use</th></thead>';
        obj['satellites'].forEach(item => {
            stable += `<tr><td>${item.PRN}</td><td>${item.az}</td><td>${item.el}</td><td>${item.gnssid}</td><td>${item.ss}</td><td>${item.svid}</td><td>${item.used}</td></tr>`;
        });
        stable += '</table>';

        const stable_container = document.getElementById('sats-container');
        stable_container.innerHTML = stable;
    }
    else if (obj['class'] == 'DEVICES') {
        let dtable = '<table>';
        dtable += '<caption>gpsd devices</caption>';
        dtable += '<thead><th>driver</th><th>path</th><th>activated at</th></thead>';
        obj['devices'].forEach(item => {
            dtable += `<tr><td>${item.driver}</td><td>${item.path}</td><td>${item.activated}</td></tr>`;
        });
        dtable += '</table>';

        const dtable_container = document.getElementById('devices-container');
        dtable_container.innerHTML = dtable;
    }
    else {
        console.log(obj);
    }
};
''' % (graph_refresh_interval * 1000)
    return Response(code, mimetype="text/javascript")

@app.route('/simple.css')
def css():
    page = '''tr:nth-child(even) {
   background-color: #f2f2f2;
}
* {
    box-sizing: border-box
}
body {
    display: flex;
    font: 18px/1.5 Open Sans, DejaVu Sans, Liberation Sans, Arial, sans-serif;
    flex-direction: column;
    margin: 0;
    min-height: 100vh;
    padding-top: 5em
}
footer {
    background: #000000;
    color: #ffffff;
    position: fixed;
    bottom: 0;
    right: 0;

    font-size: 0.75em;
    margin: 0;
    padding: 0 0.25rem;
    }
footer a {
    color: #ffffff;
}
section {
    display: inline-block;      /* keep content together for column-count */
    border: 1rem solid transparent;
    width: 100%
}

section > * {
    list-style: none;
    margin: 0;
    overflow: hidden;
    padding: .5rem var(--padding) 1rem;
    width: 100%
}

main {
    flex: 1 0 0
}

table { border-collapse: collapse }
td { padding: .25rem .5rem }
th { padding: .25rem .5rem }
thead {
  background-color: #333;
  color: white;
}
caption {
  font-weight: bold;
  font-size: 24px;
  text-align: left;
  color: #333;
  margin-top: 20px;
  margin-bottom: 12px;
}
tbody th {
  background-color: #555;
  color: #fff;
  text-align: left;
}

@media (min-width: 640px) {
    body {
        font-size: 16px
    }

    .columns {
        column-count: 1
    }
}

@media (min-width: 1280px) {
    .columns {
        column-count: 2;
        margin: auto;
        width: 1250px
    }
}

@media (min-width: 1920px) {
    .columns {
        column-count: 2;
        margin: auto;
        width: 1900px
    }
}

@media (min-width: 2560px) {
    .columns {
        column-count: 3;
        margin: auto;
        width: 2500px
    }
}

@media (min-width: 3840px) {
    .columns {
        column-count: 4;
        margin: auto;
        width: 3800px
    }
}
'''
    return Response(page, mimetype="text/css")

@app.route('/')
def slash():
    page = '''<!DOCTYPE html>
<html>
<head>
<script type="module" src="/code.js"></script>
<title>GPS/NTP monitor</title>
<link href="/simple.css" rel="stylesheet" type="text/css">
<meta name="viewport" content="width=device-width, initial-scale=1, minimum-scale=1, shrink-to-fit=no">
</head>
<body>

<main class="columns">

<section>
<div id="devices-container">rendering...</div>
</section>

<section>
<table>
<caption>position</caption>
<thead><th>name</th><th>value</th><th>description</th></thead>
<tr><th>time</th><td id="time"></td></tr>
<tr><th>status</th><td id="status"><td></tr>
<tr><th>fix mode</th><td id="mode"></td></tr>
<tr><th>latitude</th><td id="latitude"></td><td>+ is west</td></tr>
<tr><th>longitude</th><td id="longitude"></td><td>+ is north</td></tr>
<tr><th>altitude</th><td id="altitude"></td><td>only with 3D fix</td></tr>
<tr><th>epx</th><td id="epx"></td><td>longitude error, in meters</td></tr>
<tr><th>epy</th><td id="epy"></td><td>latitude error, in meters</td></tr>
<tr><th>epv</th><td id="epv"></td><td>vertical error, in meters</td></tr>
<tr><th>ept</th><td id="ept"></td><td>timestamp error, in seconds</td></tr>
<tr><th>eps</th><td id="eps"></td></tr>
<tr><th>epc</th><td id="epc"></td></tr>
<tr><th>eph</th><td id="eph"></td></tr>
<tr><th>track</th><td id="track"></td><td>course over ground, degrees from north</tr>
<tr><th>geoidSep</th><td id="geoidSep"></td></tr>
<tr><th>magvar</th><td id="magvar"></td></tr>
<tr><th>speed</th><td id="speed"></td></tr>
<tr><th>sep</th><td id="sep"></td></tr>
</table>
</section>

<section>
<div id="pps-container">rendering...</div>
</section>

<section>
<div id="pps_clk_offset">rendering...</div>
</section>

<section>
<table>
<caption>satellites</caption>
<thead><th>name</th><th>value</th><th>description</th></thead>
<tr><th>#</th><td id="nsat"></td></tr>
<tr><th># used</th><td id="usat"></td></tr>
<tr><th>hdop</th><td id="hdop"></td><td>horizontal dilution of precision</td></tr>
<tr><th>pdop</th><td id="pdop"></td><td>spherical dilution of precision</td></tr>
<tr><th>vdop</th><td id="vdop"></td><td>altitude dilution of precision</td></tr>
</table>
</section>

<section>
<div id="dop">rendering...</div>
</section>

<section>
<div id="sats-container">rendering...</div>
</section>

<section>
<div id="polar">rendering...</div>
</section>

<section>
<div id="ntp-general-container">rendering...</div>
</section>

<section>
<h2>Offsets</h2>
<div id="ntp_offset">rendering...</div>
</section>

<section>
<div id="ntp-peers-container">rendering...</div>
</section>

<section>
<div id="ntp-selected-peer-container">none yet</div>
</section>

<footer>
<h1><a href="https://github.com/folkertvanheusden/timeweb/">TimeWeb</a></h1>
</footer>

</main>

</body>
</html>
'''
    return Response(page, mimetype="text/html")

if __name__ == "__main__":
    app.run(host=listen_interface, port=listen_port, debug=True, threaded=True)
