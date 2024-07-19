timeweb is a web-interface showing the status of a GPSD/NTPSEC combo.


Required:
- python3-flask
- python3-ntp

And it is only useful if you run gpsd and ntpsec.


In gps-ntp-monitor.py you may need to change the following two lines:

    ntpsec\_host = 'localhost'
    gpsd\_host = ('localhost', 2947)

Replace localhost and/or port if you have ntpsec and/or gpsd running on non-standard hosts/ports.



Released under MIT license by Folkert van Heusden.
