timeweb is a web-interface showing the status of a GPSD/NTPSEC combo.


Required:
- python3-flask (apt)
- python3-ntp   (apt)
- allantools    (pip)

And it is only useful if you run gpsd and ntpsec.
In gps-ntp-monitor.py change the lines after 'you may need to change
these' to suit your environment.
Note that some tables/graphs may be empty when you open the website of
it just after it was started for the first time. That's because it
needs to collect some initial data first.

If you monitor a remote ntpsec/gpsd, do not forget to allow remote
connections/monitoring in their configurations.


Demo: http://gateway.vanheusden.com:5000/



Released under MIT license by Folkert van Heusden.
