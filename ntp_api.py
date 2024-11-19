#! /usr/bin/python3

# apt install python3-ntp

import datetime
import json
import prctl
import socket
import threading
import time
from db import time_series_db
from plotter import plot_timeseries_n

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
    def __init__(self, host, poll_interval, database, max_data_age, max_mru_list_size):
        threading.Thread.__init__(self)
        self.host = host
        self.poll_interval = poll_interval

        self.max_mru_list_size = max_mru_list_size

        # empty initially
        self.data = dict()

        self.databases = []
        #
        self.ntp_offset = time_series_db(database, 'offset', 86400 * max_data_age)
        self.databases.append(self.ntp_offset)
        #
        self.ntp_frequency = time_series_db(database, 'frequency', 86400 * max_data_age)
        self.databases.append(self.ntp_frequency)
        #
        self.ntp_sys_jitter = time_series_db(database, 'sys_jitter', 86400 * max_data_age)
        self.databases.append(self.ntp_sys_jitter)
        #
        self.ntp_clk_jitter = time_series_db(database, 'clk_jitter', 86400 * max_data_age)
        self.databases.append(self.ntp_clk_jitter)

    def get_data(self):
        return self.data

    def get_svg(self, table, width):
        if table == 'ntp_offset':
            return plot_timeseries_n('ntp local clock offset', ((self.ntp_offset.get_grouped(width), 'clock offset (μs)'),), width, self.poll_interval)

        if table == 'ntp_frequency':
            return plot_timeseries_n('ntp local clock frequency', ((self.ntp_frequency.get_grouped(width), 'frequency (ppm)'),), width, self.poll_interval)

        if table == 'ntp_jitter':
            return plot_timeseries_n('ntp jitter', ((self.ntp_sys_jitter.get_grouped(width), 'system jitter (ppb)'), (self.ntp_clk_jitter.get_grouped(width), 'clock jitter (ppb)')), width, self.poll_interval)

        return None

    def run(self):
        prctl.set_name('ntp_api')

        print('NTP poller thread starting')

        last_poll = 0
        last_clean = 0

        while True:
            try:
                session = ntp.packet.ControlSession()
                session.openhost(self.host)

                while True:
                    now = time.time()
                    next_poll = last_poll + self.poll_interval - now
                    if next_poll > 0:
                        time.sleep(next_poll)
                    now = time.time()

                    info = dict()
                    info['poll_ts'] = now

                    sysvars = session.readvar()
                    info['sysvars'] = sysvars

                    self.ntp_offset.insert(now, sysvars['offset'])
                    self.ntp_frequency.insert(now, sysvars['frequency'])
                    self.ntp_sys_jitter.insert(now, sysvars['sys_jitter'])
                    self.ntp_clk_jitter.insert(now, sysvars['clk_jitter'])

                    info['peers'] = dict()
                    peers = session.readstat()
                    for peer in peers:
                        peer_variables = session.readvar(peer.associd)
                        peer_variables['reftime'] = NTP_time_string_to_ctime(peer_variables['reftime'])
                        peer_variables['rec'] = NTP_time_string_to_ctime(peer_variables['rec'])
                        peer_variables['xmt'] = NTP_time_string_to_ctime(peer_variables['xmt'])
                        peer_variables['reach'] = f"{int(peer_variables['reach']):o} (octal)"
                        info['peers'][peer.associd] = peer_variables

                    # replace peer id by host or address
                    if 'peer' in info['sysvars']:
                        peer_assoc = info['sysvars']['peer']
                        if peer_assoc in info['peers']:
                            info['sysvars']['assoc'] = peer_assoc
                            info['sysvars']['peer'] = info['peers'][peer_assoc]['srchost'] if 'srchost' in info['peers'][peer_assoc] else None
                            if info['sysvars']['peer'] == None:
                                info['sysvars']['peer'] = info['peers'][peer_assoc]['srcadr']
                    else:
                        info['sysvars']['assoc'] = None

                    # replace clocks by human readable
                    info['sysvars']['reftime'] = NTP_time_string_to_ctime(info['sysvars']['reftime'])
                    info['sysvars']['clock'] = NTP_time_string_to_ctime(info['sysvars']['clock'])

                    try:
                        mrulist = session.mrulist()
                        info['mrulist'] = { 'entries': [], 'ts': mrulist.now }
                        entries = []
                        for entry in mrulist.entries:
                            entry = {
                                    'addr': entry.addr,
                                    'first': NTP_time_string_to_ctime(entry.first), 'last': NTP_time_string_to_ctime(entry.last),
                                    'mode_version': entry.mv,  # TODO: split?
                                    'restrictions': entry.rs,
                                    'packet_count': entry.ct,
                                    'score': entry.sc,
                                    'dropped': entry.dr
                                    }
                            entries.append(entry)
                        info['mrulist']['entries'] = sorted(entries, key=lambda d: d['last'], reverse=True)[0:self.max_mru_list_size]

                    except Exception as e:
                        print(f'Problem requesting MRU list from NTPSEC: {e}')
                        info['mrulist'] = { 'entries': [], 'ts': None }

                    self.data = info

                    if now - last_clean >= 300:
                        last_clean = now

                        for d in self.databases:
                            d.clean()

                    last_poll = now;

            except KeyboardInterrupt as ki:
                print(f'Exception (ntp_api.py, ctrl+c): {e}, line number: {e.__traceback__.tb_lineno}')
                break

            except ntp.packet.ControlException as nce:
                print(f'Problem communicating with NTPSEC: {nce}')
                time.sleep(0.5)

            except Exception as e:
                print(f'Exception (ntp_api.py): {e}, line number: {e.__traceback__.tb_lineno}')
                time.sleep(1.0)

            del session

if __name__ == "__main__":
    n = ntp_api('localhost', 3, 20)
    n.start()

    while True:
        print(n.get_data())
        time.sleep(3.9)
