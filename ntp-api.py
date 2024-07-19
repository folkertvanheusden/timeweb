#! /usr/bin/python3

# apt install python3-ntp

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
        self.active = False

    # when there's a user of this object
    def activate(self):
        self.active = True

    def deactive(self):
        self.active = False

    def run(self):
        while True:
            try:
                if self.active == False:
                    time.sleep(0.5)
                    continue
                
                print('probe')

                # create request
                request = ntp.packet.SyncPacket()
                request.transmit_timestamp = ntp.packet.SyncPacket.posix_to_ntp(time.time())
                packet = request.flatten()

                # send request & wait for reply
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.sendto(packet, (self.host, 123))
                d, a = s.recvfrom(1024)
                s.close()

                pkt = ntp.packet.SyncPacket(d)
                pkt.posixize()

                info = []
                print(pkt)

            except Exception as e:
                print(f'Exception: {e}')
                time.sleep(1)

            time.sleep(self.poll_interval)

if __name__ == "__main__":
    n = ntp_api('192.168.64.11', 3)
    n.activate()
    n.start()
    time.sleep(60)
