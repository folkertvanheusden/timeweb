#! /usr/bin/python3

import datetime
import io
import matplotlib
import matplotlib.pyplot as plt
# matplotlib is not thread safe
from multiprocessing import Process, Queue

matplotlib.use('agg')

def plot_timeseries(table_name, data, width):
    def _plot_timeseries(table_name, data, width, q):
        mulx = float(width) / 640.

        muly = mulx
        if muly > 1.:
            muly = (muly - 1) / 2 + 1

        # print(width, mulx, muly)

        x = [datetime.datetime.fromtimestamp(row['x']) for row in data]
        y = [row['y'] for row in data]

        plt.figure(figsize=(6.4 * mulx, 4.8 * muly), dpi=100 * mulx)
        plt.title(table_name)
        plt.xlabel('time')
        plt.ylabel('value')

        plt.plot(x, y)

        buf = io.BytesIO()
        plt.savefig(buf, format='svg')

        plt.close('all')

        buf.seek(0)
        data = buf.read()
        buf.close()

        q.put(data)

    q = Queue()

    p = Process(target=_plot_timeseries, args=(table_name, data, width, q))
    p.start()
    p.join()

    return q.get()
