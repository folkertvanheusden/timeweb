#! /usr/bin/python3

import json
import queue
import socket
import threading
import time
from db import time_series_db


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

    def get_svg(self, table, width):
        if table == 'pps_clk_offset':
            return plot_allendeviation('Allan deviation', self.clk_offset.get(), width)

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
                        del self.queues[f]

                    j = json.loads(current)
                    self.history[j['class']] = current

                    if j['class'] == 'PPS':
                        clock_offset = int(j['clock_sec']) + int(j['clock_nsec']) / 1000000000.
                        self.clk_offset.insert(time.time(), clock_offset)

            except Exception as e:
                print(f'Exception: {e}, line number: {e.__traceback__.tb_lineno}')
                time.sleep(1)

            if s != None:
                s.close()

if __name__ == "__main__":
    g = gps_api(('localhost', 2947), None)
    g.start()

    q = g.register()

    while True:
        print(q.get())
