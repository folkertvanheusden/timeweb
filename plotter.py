#! /usr/bin/python3

import datetime
import io
import matplotlib
import matplotlib.pyplot as plt
# matplotlib is not thread safe
from multiprocessing import Process, Queue

matplotlib.use('agg')

def plot_timeseries(table_name, data):
    def _plot_timeseries(table_name, data, q):
        x = [datetime.datetime.fromtimestamp(row['x']) for row in data]
        y = [row['y'] for row in data]

        plt.figure()
        plt.title(table_name)
        plt.xlabel('time')
        plt.ylabel('value')

        plt.plot(x, y)

        buf = io.BytesIO()
        plt.savefig(buf, format = 'svg')

        plt.close('all')

        buf.seek(0)
        data = buf.read()
        buf.close()

        q.put(data)

    q = Queue()

    p = Process(target=_plot_timeseries, args=(table_name, data, q))
    p.start()
    p.join()

    return q.get()
