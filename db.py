#! /usr/bin/python3

import sqlite3
import threading
import time


class time_series_db:
    def __init__(self, database_file, table_name, max_age):
        self.database_file = database_file
        self.table_name = table_name
        self.max_age = max_age

        if self.database_file == None:
            self.db = sqlite3.connect("file::memory:?cache=shared", check_same_thread=False)

        else:
            self.db = sqlite3.connect(self.database_file, check_same_thread=False)
            self.db.execute('pragma journal_mode=wal')

        cur = self.db.cursor()
        cur.execute('create table if not exists %s(ts timestamp not null, value double not null, primary key(ts))' % self.table_name)
        cur.close()
        self.db.commit()

        self.lock = threading.Lock()

    def close(self):
        self.clean()
        self.db.close()

    def insert(self, ts, value):
        with self.lock:
            cur = self.db.cursor()
            cur.execute('INSERT INTO %s(ts, value) VALUES(?, ?)' % self.table_name, (ts, value))
            cur.close()
            self.db.commit()

    def clean(self):
        with self.lock:
            cur = self.db.cursor()
            cur.execute('DELETE FROM %s WHERE ts < ?' % self.table_name, (time.time() - self.max_age,))
            cur.close()
            self.db.commit()

    def get(self):
        with self.lock:
            cur = self.db.cursor()
            cur.execute('SELECT ts, value FROM %s WHERE ts >= ? ORDER BY ts ASC' % self.table_name, (time.time() - self.max_age,))
            rows = [{ 'x': row[0], 'y': row[1] } for row in cur.fetchall() ]
            cur.close()
            self.db.commit()

            return rows

if __name__ == "__main__":
    db = time_series_db('timeweb.db', 'offset', 86400)
    data = db.get_svg()
    fh = open('test.svg', 'wb')
    fh.write(data)
    fh.close()
