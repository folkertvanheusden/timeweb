#! /usr/bin/python3

import allantools
import datetime
import io
import math
import matplotlib
import matplotlib.pyplot as plt
# matplotlib is not thread safe
from multiprocessing import Process, Queue

matplotlib.use('agg')

def calc_plot_dimensions(width):
    mulx = float(width) / 640.

    muly = mulx
    if muly > 1.:
        muly = (muly - 1) / 2 + 1

    return mulx, muly

def plot_timeseries(table_name, data, width):
    def _plot_timeseries(table_name, data, width, q):
        mulx, muly = calc_plot_dimensions(width)

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

def plot_allan_deviation(table_name, data, width):
    def _plot_allan_deviation(table_name, data, width, q):
        mulx, muly = calc_plot_dimensions(width)

        # TODO

        buf = io.BytesIO()
        plt.savefig(buf, format='svg')

        buf.seek(0)
        data = buf.read()
        buf.close()

        q.put(data)

    q = Queue()

    p = Process(target=_plot_allan_deviation, args=(table_name, data, width, q))
    p.start()
    p.join()

    return q.get()
