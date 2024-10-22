#! /usr/bin/python3

import json
import queue
import socket
import threading
import time
from db import time_series_db
from plotter import plot_timeseries_n, plot_allandeviation, plot_polar, plot_histogram


class gps_api(threading.Thread):
    def __init__(self, gpsd_host, database, max_data_age, hide_position):
        threading.Thread.__init__(self)

        self.gpsd_host = gpsd_host

        self.queues = []
        self.history = dict()

        self.hide_position = hide_position

        # GPS update interval
        self.update_graph_interval = 1

        self.databases = []
        #
        self.clk_offset = time_series_db(database, 'pps_clk_offset', 100000 * max_data_age)
        self.databases.append(self.clk_offset)
        #
        self.hdop = time_series_db(database, 'gps_hdop', 86400 * max_data_age)
        self.databases.append(self.hdop)
        self.pdop = time_series_db(database, 'gps_pdop', 86400 * max_data_age)
        self.databases.append(self.pdop)
        self.vdop = time_series_db(database, 'gps_vdop', 86400 * max_data_age)
        self.databases.append(self.vdop)
        #
        self.sat_seen = time_series_db(database, 'sat_seen', 86400 * max_data_age)
        self.databases.append(self.sat_seen)
        self.sat_used = time_series_db(database, 'sat_used', 86400 * max_data_age)
        self.databases.append(self.sat_used)

        # satellites
        self.sats = []

        threading.Thread(target=self._db_cleaner, args=(self.databases,)).start()

    def _db_cleaner(self, db_list):
        while True:
            for d in self.databases:
                d.clean()

            time.sleep(300)

    def get_svg(self, table, width):
        if table == 'pps_clk_offset':
            return plot_allandeviation('Allan deviation', self.clk_offset.get(), width, self.update_graph_interval)

        if table == 'dop':
            return plot_timeseries_n('dilution of precision', ((self.hdop.get_grouped(width), 'hdop'), (self.pdop.get_grouped(width), 'pdop'), (self.vdop.get_grouped(width), 'vdop')), width, self.update_graph_interval)

        if table == 'polar':
            return plot_polar('azimuth/elevation', self.sats, width, self.update_graph_interval)

        if table == 'used_hist':
            return plot_histogram('GPS seen/used count', (('GPSes used', self.sat_used.get_histogram()), ('GPSes seen', self.sat_seen.get_histogram())), width, self.update_graph_interval)

        print(f'TABLE {table} not known!')

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
        print('GPS processing thread starting')

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

                    j = json.loads(current)

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

                        self.sats = j['satellites']

                    elif j['class'] == 'TPV':
                        if self.hide_position == True:
                            j['lat'] = 'hidden'
                            j['lon'] = 'hidden'
                            j['alt'] = 'hidden'
                            current = json.dumps(j)

                    self.history[j['class']] = current

                    for q in self.queues:
                        try:
                            q.put_nowait(current)

                        except queue.Full:
                            forget.append(q)

                    # in case a client "forgets" to unregister
                    for f in forget:
                        self.queues.remove(f)

            except KeyboardInterrupt as ki:
                print(f'Exception (gps_api.py, ctrl+c): {e}, line number: {e.__traceback__.tb_lineno}')
                break

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
