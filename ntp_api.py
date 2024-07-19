#! /usr/bin/python3

# apt install python3-ntp

import json
import socket
import threading
import time

import ntp.control
import ntp.magic
import ntp.ntpc
import ntp.packet
import ntp.util


class ntp_api(threading.Thread):
    def __init__(self, host, poll_interval):
        threading.Thread.__init__(self)
        self.host = host
        self.poll_interval = poll_interval

        # empty initially
        self.data = dict()

    def get_data(self):
        return self.data

    def run(self):
        print('NTP poller thread starting')

        last_poll = 0

        while True:
            try:
                now = time.time()
                if now - last_poll < self.poll_interval:
                    time.sleep(0.5)
                    continue

                last_poll = now;
                info = dict()

                info['poll-ts'] = now

                session = ntp.packet.ControlSession()
                session.openhost(self.host)

                sysvars = session.readvar()
                info['sysvars'] = sysvars

                info['peers'] = dict()
                peers = session.readstat()
                for peer in peers:
                    peer_variables = session.readvar(peer.associd)
                    info['peers'][peer.associd] = peer_variables

                # print(session.mrulist())

                self.data = info

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
