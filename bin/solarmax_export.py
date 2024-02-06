#!/usr/bin/python
# -* coding: utf-8 *-

import datetime, sys, os
from sqlite3 import dbapi2 as sqlite

DB_FILE=sys.argv[1]
INTERVAL = 5*60  # 5 Minuten

dbconn = sqlite.connect(DB_FILE)
db = dbconn.cursor()

#yesterday = int((datetime.date.today() - datetime.timedelta(days=1)).strftime('%s'))
midnight = int(datetime.date.today().strftime("%s"))
#midnight = yesterday
now = int(datetime.datetime.now().strftime("%s"))

current = midnight

while current < now:
  db.execute("SELECT inverter, system, AVG(pac), MAX(daysum), MAX(total) FROM performance WHERE time >%i AND time <=%i GROUP BY inverter, system" % (current, current+INTERVAL))
  result = db.fetchall()
  for line in result:
    (inverter, system, pac, daysum, total) = line
    print('%i;%i;%.1f;%.1f;%.1f;%i' % (inverter, system, pac, daysum, total, current+INTERVAL))
  current += INTERVAL








