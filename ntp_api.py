#! /usr/bin/python3

# apt install python3-ntp

import datetime
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


def NTP_time_string_to_ctime(s):
    if s == None:
        return '?'

    dot = s.find('.')
    v1 = int(s[2:dot], 16)
    v2 = int(s[dot + 1:], 16)
    ts = v1 + v2 / 1000000000.

    UNIX_EPOCH = 2208988800
    ts -= UNIX_EPOCH

    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S.%f')

class ntp_api(threading.Thread):
    def __init__(self, host, poll_interval, database, max_data_age):
        threading.Thread.__init__(self)
        self.host = host
        self.poll_interval = poll_interval

        # empty initially
        self.data = dict()

        self.databases = []
        #
        self.ntp_offset = time_series_db(database, 'offset', 86400 * max_data_age)
        self.databases.append(self.ntp_offset)

    def get_data(self):
        return self.data

    def get_svg(self, table, width):
        if table == 'ntp_offset':
            return plot_timeseries('ntp offset', self.ntp_offset.get(), width)

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

                # replace peer id by host or address
                if 'peer' in info['sysvars']:
                    peer_assoc = info['sysvars']['peer']
                    if peer_assoc in info['peers']:
                        info['sysvars']['peer'] = info['peers'][peer_assoc]['srchost'] if 'srchost' in info['peers'][peer_assoc] else None
                        if info['sysvars']['peer'] == None:
                            info['sysvars']['peer'] = info['peers'][peer_assoc]['srcadr']

                # replace clocks by human readable
                info['sysvars']['reftime'] = NTP_time_string_to_ctime(info['sysvars']['reftime'])
                info['sysvars']['clock'] = NTP_time_string_to_ctime(info['sysvars']['clock'])

                # print(session.mrulist())

                self.data = info

                if now - last_clean >= 300:
                    last_clean = now

                    for d in self.databases:
                        d.clean()

                del session

            except ntp.packet.ControlException as nce:
                print(f'Problem communicating with NTPSEC: {nce}')

            except Exception as e:
                print(f'Exception (ntp_api.py): {e}, line number: {e.__traceback__.tb_lineno}')
                time.sleep(1)

if __name__ == "__main__":
    n = ntp_api('localhost', 3)
    n.start()

    while True:
        print(n.get_data())
        time.sleep(3.9)
