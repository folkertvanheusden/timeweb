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
import threading
import time


cache = dict()
cache_lock = threading.Lock()

matplotlib.use('agg')

use_cache = None

# TODO move it into a class
def set_cache(use_cache_in):
    global use_cache
    use_cache = use_cache_in

def get_cache(table_name, max_age):
    o = None
    cache_lock.acquire()

    if table_name in cache:
        now = time.time()
        if now - cache[table_name]['ts'] <= max_age:
            print(f'{table_name} from cache')
            o = cache[table_name]['obj']

    cache_lock.release()
    if o == None:
            print(f'regenerate {table_name}')
    return o

def put_cache(table_name, obj):
    if use_cache:
        cache_lock.acquire()
        cache[table_name] = { 'ts': time.time(), 'obj' : obj }
        cache_lock.release()

def calc_plot_dimensions(width):
    mulx = float(width) / 640.

    muly = mulx
    if muly > 1.:
        muly = (muly - 1) / 2 + 1

    return mulx, muly

def plot_timeseries_n(table_name, data, width, max_age):
    def _plot_timeseries_n(table_name, data, width, q):
        mulx, muly = calc_plot_dimensions(width)

        plt.figure(figsize=(6.4 * mulx, 4.8 * muly), dpi=100 * mulx)
        plt.title(table_name)
        plt.xlabel('time')

        for d in data:
            x = [datetime.datetime.fromtimestamp(row['x']) for row in d[0]]
            y = [row['y'] for row in d[0]]
            plt.plot(x, y, label=d[1])

        plt.legend()

        buf = io.BytesIO()
        plt.savefig(buf, format='svg')

        plt.close('all')

        buf.seek(0)
        data = buf.read()
        buf.close()

        q.put(data)

    o = get_cache(table_name, max_age)
    if o != None:
        return o

    q = Queue()

    p = Process(target=_plot_timeseries_n, args=(table_name, data, width, q))
    p.start()
    rc = q.get()
    p.join()

    put_cache(table_name, rc)

    return rc

def plot_allandeviation(table_name, data, width, max_age):
    def _plot_allandeviation(table_name, data, width, q):
        mulx, muly = calc_plot_dimensions(width)

        values = []
        prev_value = None
        for row in data:
            v = float(row['y'])
            if len(values) > 0:
                n_to_add = int(v) - int(prev_value) - 1
                values += [math.nan] * n_to_add
            values.append(v)
            prev_value = v

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

    o = get_cache(table_name, max_age)
    if o != None:
        return o

    q = Queue()

    p = Process(target=_plot_allandeviation, args=(table_name, data, width, q))
    p.start()
    rc = q.get()
    p.join()

    put_cache(table_name, rc)

    return rc

def plot_polar(table_name, satellites, width, max_age):
    def _plot_polar(table_name, satellites, width, q):
        mulx, muly = calc_plot_dimensions(width)

        fig = plt.figure()
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8], polar=True)
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_yticks(range(0, 90+10, 30))                   # Define the yticks
        yLabel = ['90', '60','30','0']
        ax.set_yticklabels(yLabel)
        ax.set_xticks(np.arange(0, np.pi*2, np.pi/2))                   # Define the xticks
        xLabel = ['N', 'E', 'S', 'W']
        ax.set_xticklabels(xLabel)

        for sat in satellites:
            ax.annotate(str(sat['PRN']),
                    xy=(sat['az']*np.pi/180, 90-sat['el']),  # theta, radius
                    bbox=dict(boxstyle="round", fc = matplotlib.colors.hsv_to_rgb((sat['ss']/50, 1.0, 0.5)), alpha = 0.5),
                    horizontalalignment='center',
                    verticalalignment='bottom')

        buf = io.BytesIO()
        plt.savefig(buf, format='svg')

        plt.close('all')

        buf.seek(0)
        q.put(buf.read())
        buf.close()

    o = get_cache(table_name, max_age)
    if o != None:
        return o

    q = Queue()

    p = Process(target=_plot_polar, args=(table_name, satellites, width, q))
    p.start()
    rc = q.get()
    p.join()

    put_cache(table_name, rc)

    return rc

def plot_histogram(table_name, data, width, max_age):
    def _plot_histogram(table_name, data, width, q):
        try:
            mulx, muly = calc_plot_dimensions(width)

            plt.figure(figsize=(6.4 * mulx, 4.8 * muly), dpi=100 * mulx)
            plt.title(table_name)
            plt.ylabel('count')

            for d in data:
                values = [row['y'] for row in d[1]]
                n, bins, patches = plt.hist(values, int(width / 15), label=d[0])

            plt.legend()

            buf = io.BytesIO()
            plt.savefig(buf, format='svg')

            plt.close('all')

            buf.seek(0)
            data = buf.read()
            buf.close()

            q.put(data)

        except Exception as e:
            print(f'Exception (plotter.py, plot_histogram): {e}, line number: {e.__traceback__.tb_lineno}')
            q.put(None)

    o = get_cache(table_name, max_age)
    if o != None:
        return o

    q = Queue()

    p = Process(target=_plot_histogram, args=(table_name, data, width, q))
    p.start()
    rc = q.get()
    p.join()

    put_cache(table_name, rc)

    return rc

if __name__ == "__main__":
    from gps_api import gps_api
    g = gps_api(('localhost', 2947), None, 86400, False)

    fh = open('test.svg', 'wb')
    fh.write(plot_histogram('used_hist', g.sat_used.get(), 640, 0))
    fh.close()
