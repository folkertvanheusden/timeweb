#! /usr/bin/python3

import json
import queue
import socket
import threading
import time
from db import time_series_db
from plotter import plot_dop, plot_allandeviation


class gps_api(threading.Thread):
    def __init__(self, gpsd_host, database):
        threading.Thread.__init__(self)

        self.gpsd_host = gpsd_host

        self.queues = []
        self.history = dict()

        self.databases = []
        #
        self.clk_offset = time_series_db(database, 'pps_clk_offset', 100000)
        self.databases.append(self.clk_offset)
        #
        self.hdop = time_series_db(database, 'gps_hdop', 86400)
        self.databases.append(self.hdop)
        self.pdop = time_series_db(database, 'gps_pdop', 86400)
        self.databases.append(self.pdop)
        self.vdop = time_series_db(database, 'gps_vdop', 86400)
        self.databases.append(self.vdop)
        #
        self.sat_seen = time_series_db(database, 'sat_seen', 86400)
        self.databases.append(self.sat_seen)
        self.sat_used = time_series_db(database, 'sat_used', 86400)
        self.databases.append(self.sat_used)

    def get_svg(self, table, width):
        if table == 'pps_clk_offset':
            return plot_allandeviation('Allan deviation', self.clk_offset.get(), width)

        if table == 'dop':
            return plot_dop('h/p/v dop', self.hdop.get(), self.pdop.get(), self.vdop.get(), width)

        return None

    def register(self):
        q = queue.Queue(maxsize = 250)
        self.queues.append(q)

        for h in self.history:
            q.put_nowait(self.history[h])

        return q

    def unregister(self, q):
        del self.queues[q]

    def run(self):
        while True:
            s = None

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(self.gpsd_host)

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

                    forget = []

                    for q in self.queues:
                        try:
                            q.put_nowait(current)

                        except queue.Full:
                            forget.append(q)

                    # in case a client "forgets" to unregister
                    for f in forget:
                        self.queues.remove(f)

                    j = json.loads(current)
                    self.history[j['class']] = current

                    now = time.time()

                    if j['class'] == 'PPS':
                        clock_offset = int(j['clock_sec']) + int(j['clock_nsec']) / 1000000000.
                        self.clk_offset.insert(now, clock_offset)

                    elif j['class'] == 'SKY':
                        hdop = float(j['hdop'])
                        if hdop < 99:
                            self.hdop.insert(now, hdop)
                        vdop = float(j['vdop'])
                        if vdop < 99:
                            self.vdop.insert(now, vdop)
                        pdop = float(j['pdop'])
                        if pdop < 99:
                            self.pdop.insert(now, pdop)

                        self.sat_seen.insert(now, float(j['nSat']))
                        self.sat_used.insert(now, float(j['uSat']))

            except Exception as e:
                print(f'Exception (gps_api.py): {e}, line number: {e.__traceback__.tb_lineno}')
                time.sleep(1)

            if s != None:
                s.close()

if __name__ == "__main__":
    g = gps_api(('localhost', 2947), None)
    g.start()

    q = g.register()

    while True:
        print(q.get())
