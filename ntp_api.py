#! /usr/bin/python3

# apt install python3-ntp

import json
import socket
import threading
import time
from db import time_series_db
from plotter import plot_timeseries

import ntp.control
import ntp.magic
import ntp.ntpc
import ntp.packet
import ntp.util


class ntp_api(threading.Thread):
    def __init__(self, host, poll_interval, database):
        threading.Thread.__init__(self)
        self.host = host
        self.poll_interval = poll_interval

        # empty initially
        self.data = dict()

        self.databases = []
        #
        self.ntp_offset = time_series_db(database, 'offset', 86400)
        self.databases.append(self.ntp_offset)

    def get_data(self):
        return self.data

    def get_svg(self, table):
        if table == 'ntp_offset':
            return plot_timeseries('ntp offset', self.ntp_offset.get())

        return None

    def run(self):
        print('NTP poller thread starting')

        last_poll = 0
        last_clean = 0

        while True:
            try:
                now = time.time()
                if now - last_poll < self.poll_interval:
                    time.sleep(0.5)
                    continue

                last_poll = now;
                info = dict()

                info['poll_ts'] = now

                session = ntp.packet.ControlSession()
                session.openhost(self.host)

                sysvars = session.readvar()
                info['sysvars'] = sysvars

                self.ntp_offset.insert(now, sysvars['offset'])

                info['peers'] = dict()
                peers = session.readstat()
                for peer in peers:
                    peer_variables = session.readvar(peer.associd)
                    info['peers'][peer.associd] = peer_variables

                # print(session.mrulist())

                self.data = info

                if now - last_clean >= 300:
                    last_clean = now

                    for d in self.databases:
                        d.clean()

            except Exception as e:
                print(f'Exception: {e}, line number: {e.__traceback__.tb_lineno}')
                time.sleep(1)

            time.sleep(self.poll_interval)

if __name__ == "__main__":
    n = ntp_api('localhost', 3)
    n.start()

    while True:
        print(n.get_data())
        time.sleep(3.9)
