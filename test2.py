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
            s.connect(('localhost', 2947))

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
var eventSource = new EventSource("/gps");
eventSource.onmessage = function(e) {
console.log(e.data);
    const obj = JSON.parse(e.data);
    if (obj['class'] == 'TPV') {
        document.getElementById('time'     ).innerHTML = obj['time'];
        document.getElementById('ept'      ).innerHTML = obj['ept' ];
        document.getElementById('mode'     ).innerHTML = obj['mode'];
        document.getElementById('latitude' ).innerHTML = obj['lat' ];
        document.getElementById('longitude').innerHTML = obj['lon' ];
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
        stable += '<tr><th>PRN</th><th>az</th><th>el</th><th>gnssid</th><th>ss</th><th>svid</th><th>in use</th></tr>';
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
<script type="text/javascript" src="/code.js"></script>
<title>GPS monitor</title>
</head>
<body>
<div>
<h2>position</h2>
<table>
<tr><td>time</td><td id="time"></td></tr>
<tr><td>ept</td><td id="ept"><td></tr>
<tr><td>fix mode</td><td id="mode"></td></tr>
<tr><td>latitude</td><td id="latitude"></td></tr>
<tr><td>longitude</td><td id="longitude"></td></tr>
</table>
</div>
<div>
<h2>satellites</h2>
<table>
<tr><td>#</td><td id="nsat"></td></tr>
<tr><td># used</td><td id="usat"></td></tr>
<tr><td>hdop</td><td id="hdop"></td></tr>
<tr><td>pdop</td><td id="pdop"></td></tr>
<tr><td>vdop</td><td id="vdop"></td></tr>
</table>
<div id="sats-container"></div>
</div>
</body>
</html>
'''
    return Response(page, mimetype="text/html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
