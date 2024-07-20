timeweb is a web-interface showing the status of a GPSD/NTPSEC combo.


Required:
- python3-flask (apt)
- python3-ntp   (apt)
- allantools    (pip)

And it is only useful if you run gpsd and ntpsec.


In gps-ntp-monitor.py you may need to change the following two lines:

    ntpsec_host = 'localhost'
    gpsd_host = ('localhost', 2947)

Replace localhost and/or port if you have ntpsec and/or gpsd running on non-standard hosts/ports.


Demo: http://gateway.vanheusden.com:5000/



Released under MIT license by Folkert van Heusden.
