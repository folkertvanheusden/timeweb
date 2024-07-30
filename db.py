#! /usr/bin/python3

import sqlite3
import time


class time_series_db:
    def __init__(self, database_file, table_name, max_age):
        self.database_file = database_file
        self.table_name = table_name
        self.max_age = max_age

        db = sqlite3.connect(self.database_file)
        db.execute('pragma journal_mode=wal')
        cur = db.cursor()
        cur.execute('create table if not exists %s(ts timestamp not null, value double not null, primary key(ts))' % self.table_name)
        cur.close()
        db.commit()
        db.close()

    def close(self):
        self.clean()

    def insert(self, ts, value):
        db = sqlite3.connect(self.database_file)
        cur = db.cursor()
        try:
            cur.execute('INSERT INTO %s(ts, value) VALUES(?, ?)' % self.table_name, (ts, value))
        except Exception as e:
            print(f'Exception (db.py): {e}, line number: {e.__traceback__.tb_lineno}')
        cur.close()
        db.commit()
        db.close()

    def clean(self):
        print(f'Cleaning {self.table_name} in {self.database_file if self.database_file != None else "(memory)"}')

        db = sqlite3.connect(self.database_file)
        cur = db.cursor()
        try:
            cur.execute('DELETE FROM %s WHERE ts < ?' % self.table_name, (time.time() - self.max_age,))
        except Exception as e:
            print(f'Exception (db.py): {e}, line number: {e.__traceback__.tb_lineno}')
        cur.close()
        db.commit()
        db.close()

    def get(self):
        db = sqlite3.connect(self.database_file)
        cur = db.cursor()
        cur.execute('SELECT ts, value FROM %s ORDER BY ts ASC' % self.table_name)
        rows = [{ 'x': row[0], 'y': row[1] } for row in cur.fetchall() ]
        cur.close()
        db.close()

        return rows

    def get_grouped(self, group_to_count):
        db = sqlite3.connect(self.database_file)
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) AS n FROM %s' % self.table_name)
        n = cur.fetchone()[0]
        cur.execute('SELECT AVG(ts) AS ts, AVG(value) AS value FROM %s GROUP BY FLOOR(ts / %s) ORDER BY ts ASC' % (self.table_name, max(1, n / group_to_count)))
        rows = [{ 'x': row[0], 'y': row[1] } for row in cur.fetchall() ]
        cur.close()
        db.close()

        return rows

    def get_histogram(self):
        db = sqlite3.connect(self.database_file)
        cur = db.cursor()
        cur.execute('SELECT value, (COUNT(*) * 100. / (SELECT COUNT(*) FROM %s)) AS n FROM %s GROUP BY value ORDER BY value ASC' % (self.table_name, self.table_name))
        rows = [{ 'value': row[0], 'count': row[1] } for row in cur.fetchall() ]
        cur.close()
        db.close()

        return rows

if __name__ == "__main__":
    db = time_series_db('timeweb.db', 'offset', 86400)
    data = db.get_svg()
    fh = open('test.svg', 'wb')
    fh.write(data)
    fh.close()
