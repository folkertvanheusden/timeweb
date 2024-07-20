#! /usr/bin/python3

import datetime
import io
import matplotlib
import matplotlib.pyplot as plt
import threading

# matplotlib is not thread safe
lock = threading.Lock()

matplotlib.use('agg')


def plot_timeseries(table_name, data):
    with lock:
        plt.figure()
        plt.title(table_name)
        plt.xlabel('time')
        plt.ylabel('value')

        x = [datetime.datetime.fromtimestamp(row['x']) for row in data]
        y = [row['y'] for row in data]

        plt.plot(x, y)

        buf = io.BytesIO()
        plt.savefig(buf, format = 'svg')
        buf.seek(0)
        data = buf.read()
        buf.close()

        plt.close('all')

        return data
