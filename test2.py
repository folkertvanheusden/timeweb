#! /usr/bin/python3

# pip install flask-sse

from flask import Flask, Response
import json
import socket

app = Flask(__name__)

@app.route('/gps')
def gps():
    def stream():
        s = None

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('time.lan.nurd.space', 2947))

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
            print(error)
            yield 'data:' + json.dumps({'error': str(e)}) + '\n\n'

        if s != None:
            s.close()

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

var eventSource = new EventSource("/gps");
eventSource.onmessage = function(e) {
console.log(e.data);
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
    else if (obj['class'] == 'SKY') {
        // general data
        document.getElementById('hdop').innerHTML = obj['hdop'];
        document.getElementById('pdop').innerHTML = obj['pdop'];
        document.getElementById('vdop').innerHTML = obj['vdop'];
        document.getElementById('nsat').innerHTML = obj['nSat'];
        document.getElementById('usat').innerHTML = obj['uSat'];

        // list of satellites
        let stable = '<table>';
        stable += '<caption>details</caption>';
        stable += '<thead><th>PRN ID</th><th>azimuth</th><th>elevation</th><th>gnssid</th><th>signal strength</th><th>svid</th><th>in use</th></thead>';
        obj['satellites'].forEach(item => {
            stable += `<tr><td>${item.PRN}</td><td>${item.az}</td><td>${item.el}</td><td>${item.gnssid}</td><td>${item.ss}</td><td>${item.svid}</td><td>${item.used}</td></tr>`;
        });
        stable += '</table>';

        const stable_container = document.getElementById('sats-container');
        stable_container.innerHTML = stable;
    }
    else {
        console.log(obj);
    }
};
'''
    return Response(code, mimetype="text/javascript")

@app.route('/')
def slash():
    page = '''<!DOCTYPE html>
<html>
<head>
<script type="module" src="/code.js"></script>
<title>GPS monitor</title>
<style>
tr:nth-child(even) {
   background-color: #f2f2f2;
}
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
</style>
</head>
<body>
<div>
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
</div>
<div>
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
</div>
</body>
</html>
'''
    return Response(page, mimetype="text/html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
