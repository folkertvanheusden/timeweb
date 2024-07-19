#! /usr/bin/python3

# pip install flask-sse

from flask import Flask, Response
import json
import socket
import time
from ntp_api import ntp_api

ntpsec_host = 'localhost'
gpsd_host = ('localhost', 2947)

n = ntp_api(ntpsec_host, 3.)
n.start()

app = Flask(__name__)

@app.route('/gps')
def gps():
    def stream():
        s = None

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(gpsd_host)

            # start stream
            s.send('?WATCH={"enable":true,"json":true}\r\n'.encode('ascii'))

            buffer = ''

            while True:
                buffer += s.recv(65536).decode('ascii').replace('\r','')

                lf = buffer.find('\n')
                if lf == -1:
                    continue

                current = buffer[0:lf]
                buffer = buffer[lf + 1:]

                yield 'data:' + current + '\n\n'

        except Exception as e:
            print(f'Exception: {e}, line number: {e.__traceback__.tb_lineno}')
            yield 'data:' + json.dumps({'error': str(e)}) + '\n\n'

        if s != None:
            s.close()

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
            print(f'Exception: {e}, line number: {e.__traceback__.tb_lineno}')
            yield 'data:' + json.dumps({'error': str(e)}) + '\n\n'

    return Response(stream(), mimetype="text/event-stream")

@app.route('/code.js')
def code():
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

var eventSourceNTP = new EventSource("/ntp");
eventSourceNTP.onmessage = function(e) {
    const obj = JSON.parse(e.data);

    // sysvars

    let ngtable = '<table>';
    ngtable += '<caption>general</caption>';
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
    peerstable += '<thead><th>host</th><th>refid</th><th>stratum</th><th>unreach</th><th>offset</th><th>jitter</th></thead>';
    for (const [key, value] of Object.entries(obj['peers'])) {
        var host = value.srchost;
        if (host === undefined)
            host = value.srcadr;
        peerstable += `<tr><td>${host}</td><td>${value.refid}</td><td>${value.stratum}</td><td>${value.unreach}</td><td>${value.offset}</td><td>${value.jitter}</td></tr>`;
    };

    peerstable += '</table>';

    const peerstable_container = document.getElementById('ntp-peers-container');
    peerstable_container.innerHTML = peerstable;
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
'''
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

    font-size: 1.25em;
    margin: 0;
    padding: 0 1rem;
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
        column-count: 1;
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
<h2>GPSd</h2>
<div id="devices-container"></div>
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
<div id="pps-container"></div>
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
<div id="sats-container"></div>
</section>

<section>
<h2>NTP general</h2>
<div id="ntp-general-container"></div>
</section>

<section>
<h2>NTP peers</h2>
<div id="ntp-peers-container"></div>
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
    app.run(host='0.0.0.0', port=80, debug=True)
