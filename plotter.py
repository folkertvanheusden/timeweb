#! /usr/bin/python3

import allantools
import datetime
import io
import math
import matplotlib
import matplotlib.pyplot as plt
# matplotlib is not thread safe
from multiprocessing import Process, Queue
import numpy as np

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

def plot_allandeviation(table_name, data, width):
    def _plot_allandeviation(table_name, data, width, q):
        mulx, muly = calc_plot_dimensions(width)

        values = [float(row['y']) for row in data]
        a = allantools.Dataset(data=np.asarray(values),
                               data_type='phase',
                               rate=1)  # sample rate in Hz of the input data
        a.compute('gradev')

        b = allantools.Plot(no_display=True)
        b.ax.set_xlabel("Tau (s)")
        b.plt.title(table_name)
        b.plot(a, errorbars=True, grid=True)

        buf = io.BytesIO()
        b.plt.savefig(buf, format='svg')
        buf.seek(0)
        data = buf.read()

        q.put(data)

        buf.close()
        b.plt.close('all')
        del b

    q = Queue()

    p = Process(target=_plot_allandeviation, args=(table_name, data, width, q))
    p.start()
    p.join()

    return q.get()

def plot_dop(table_name, hdop_data, pdop_data, vdop_data, width):
    def _plot_dop(table_name, hdop_data, pdop_data, vdop_data, width, q):
        mulx, muly = calc_plot_dimensions(width)

        xh = [datetime.datetime.fromtimestamp(row['x']) for row in hdop_data]
        xp = [datetime.datetime.fromtimestamp(row['x']) for row in pdop_data]
        xv = [datetime.datetime.fromtimestamp(row['x']) for row in vdop_data]
        yh = [row['y'] for row in hdop_data]
        yp = [row['y'] for row in pdop_data]
        yv = [row['y'] for row in vdop_data]

        plt.figure(figsize=(6.4 * mulx, 4.8 * muly), dpi=100 * mulx)
        plt.title(table_name)
        plt.xlabel('time')
        plt.ylabel('value')

        plt.plot(xh, yh, label='hdop')
        plt.plot(xp, yp, label='hdop')
        plt.plot(xv, yv, label='hdop')
        plt.legend()

        buf = io.BytesIO()
        plt.savefig(buf, format='svg')

        plt.close('all')

        buf.seek(0)
        data = buf.read()
        buf.close()

        q.put(data)

    q = Queue()

    p = Process(target=_plot_dop, args=(table_name, hdop_data, pdop_data, vdop_data, width, q))
    p.start()
    p.join()

    return q.get()

