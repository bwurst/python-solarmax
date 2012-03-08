#!/usr/bin/python
# -* coding: utf-8 *-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Developed 2009-2010 by Bernd Wurst <bernd@schokokeks.org> 
# for own use.
# Released to the public in 2012.


import socket, datetime


# Konstanten
inverter_types = {
      20010: { 'desc': 'SolarMax 2000S', 'max': 2000, }, # Nur geraten
      20020: { 'desc': 'SolarMax 3000S', 'max': 3000, },
      20030: { 'desc': 'SolarMax 4200S', 'max': 4200, },
      20040: { 'desc': 'SolarMax 6000S', 'max': 6000, },
    }


query_types = ['KDY', 'KYR', 'KMT', 'KT0', 'IL1', 'IDC', 'PAC', 'PRL',
               'SYS', 'SAL', 'TNF', 'PAC', 'PRL', 'TKK', 'UL1', 'UDC',
               'ADR', 'TYP', 'PIN', 'MAC', 'CAC', 'KHR', 'EC00', 'EC01',
               'EC02', 'EC03', 'EC04', 'EC05', 'EC06', 'EC07', 'EC08',
               'BDN', 'SWV', 'DIN', 'LAN', 'SDAT', 'FDAT']


status_codes = {
      20000: 'Keine Kommunikation',
      20001: 'In Betrieb',
      20002: 'Zu wenig Einstrahlung',
      20003: 'Anfahren',
      20004: 'Betrieb auf MPP',
      20005: 'Ventilator läuft',
      20006: 'Betrieb auf Maximalleistung',
      20007: 'Temperaturbegrenzung',
      20008: 'Netzbetrieb',
    }


alarm_codes = {
          0: 'kein Fehler',
          1: 'Externer Fehler 1',
          2: 'Isolationsfehler DC-Seite',
          4: 'Fehlerstrom Erde zu Groß',
          8: 'Sicherungsbruch Mittelpunkterde',
         16: 'Externer Alarm 2',
         32: 'Langzeit-Temperaturbegrenzung',
         64: 'Fehler AC-Einspeisung',
        128: 'Externer Alarm 4',
        256: 'Ventilator defekt',
        512: 'Sicherungsbruch',
       1024: 'Ausfall Temperatursensor',
       2048: 'Alarm 12',
       4096: 'Alarm 13',
       8192: 'Alarm 14',
      16384: 'Alarm 15',
      32768: 'Alarm 16',
      65536: 'Alarm 17',
  }



# Hilfs-Routine (DEBUG)

def DEBUG(*s):
  out = [datetime.datetime.now().isoformat()+':',] + [str(x) for x in s]
  print(' '.join(out))



####################################
## Haupt-Klasse
####################################


class SolarMax ( object ):
  def __init__(self, host, port):
    self.__host = host
    self.__port = port
    self.__inverters = {}
    self.__socket = None
    self.__connected = False
    self.__allinverters = False
    self.__inverter_list = []
    self.__connect()

  def __repr__(self):
    return 'SolarMax[%s:%s / socket=%s]' % (self.__host, self.__port, self.__socket)

  def __str__(self):
    return 'SolarMax[%s:%s / socket=%s / inverters=%s]' % (self.__host, self.__port, self.__socket, self.inverters())

  def __disconnect(self):
    try:
      DEBUG('Closing open connection to %s:%s' % (self.__host, self.__port))
      self.__socket.shutdown(socket.SHUT_RDWR)
      self.__socket.close()
      del self.__socket
    except:
      pass
    finally:
      self.__connected = False
      self.__allinverters = False
      self.__socket = None

  def __del__(self):
    DEBUG('destructor called')
    self.__disconnect()

  def __connect(self):
    self.__disconnect()
    DEBUG('establishing connection to %s:%i...' % (self.__host, self.__port))
    try:
      # Python 2.5
      self.__socket = socket.socket()
      s = self.__socket
      s.settimeout(2)
      s.connect((self.__host, self.__port))
      s.settimeout(10)
      self.__connected = True
      DEBUG('connected.')
    except:
      DEBUG('connection to %s:%i failed' % (self.__host, self.__port))
      self.__connected = False
      self.__allinverters = False

    # Python 2.6
    ## Socket-timeout: 5 secs
    #self.__socket = socket.create_connection((self.__host, self.__port), 5)


  # Utility-functions
  def hexval(self, i):
    return (hex(i)[2:]).upper()


  def checksum(self, s):
    total = 0
    for c in s:
      total += ord(c)
    h = self.hexval(total)
    while len(h) < 4:
      h = '0'+h
    return h


  def __receive(self):
    try:
      data = ''
      tmp = ''
      while True:
         tmp = self.__socket.recv(1)
         data += tmp
         if len(tmp) < 1 or tmp == '}':
           break
         tmp = ''
      return data
    except:
      self.__allinverters = False
      return ""


  def __parse(self, answer):
    # convenience checks
    if answer[0] != '{' or answer[-1] != '}':
      raise ValueError('malformed answer: %s' % answer)
    raw_answer = answer
    answer = answer[1:-1]
    checksum = answer[-4:]
    content = answer[:-4]
    # checksum
    if checksum != self.checksum(content):
      raise ValueError('checksum error')

    (header, content) = content[:-1].split('|', 2)
    (inverter, fb, length) = header.split(';', 3)
    if fb != 'FB':
      raise ValueError('answer not understood')
    # length
    length = int(length, 16)
    if length != len(raw_answer):
      raise ValueError('length mismatch')

    inverter = int(inverter)

    # Bei schreibzugriff antwortet der WR mit 'C8'
    #if not content.startswith('64:'):
    #  raise ValueError('Inverter did not understand our query')

    content = content[3:]
    data = {}
    
    for item in content.split(';'):
      (key, value) = item.split('=')
      if key not in query_types:
        raise NotImplementedError("Don't know %s" % item)
      data[key] = value
    return (inverter, data)




  def __build_query(self, id, values, qtype=100):
    qtype = self.hexval(qtype)
    if type(values) == list:
      for v in values:
        if v not in query_types:
          raise ValueError('Unknown data type »'+v+'«')
      values = ';'.join(values)
    elif type(values) in [str, unicode]:
      pass
    else:
      raise ValueError('value has unsupported type')

    querystring = '|' + qtype + ':' + values + '|'
    # Länge vergrößern um: 2 x { (2), WR-Nummer (2), "FB" (2), zwei Semikolon (2), Länge selbst (2), checksumme (4)
    l = len(querystring) + 2 + 2 + 2 + 2 +2 + 4
    querystring = 'FB;%02i;%s%s' % (int(id), self.hexval(l), querystring)
    querystring += self.checksum(querystring)
    return '{%s}' % querystring


  def __send_query(self, querystring):
    try:
      DEBUG(self.__host, '=>', querystring)
      self.__socket.send(querystring)
    except socket.timeout:
      self.__allinverters = False
    except socket.error:
      self.__connected = False



  def query(self, id, values, qtype=100):
    q = self.__build_query(id, values, qtype)
    #DEBUG("WR %i: %s" % (id, q))
    self.__send_query(q)
    answer = self.__receive()
    if answer:
      (inverter, data) = self.__parse(answer)
      for d in data.keys():
        data[d] = self.normalize_value(d, data[d])
      return (inverter, data)
    else:
      self.__allinverters = False

    if not self.__allinverters and not self.__detection_running:
      self.detect_inverters()
    elif not self.__connected:
      self.__connect()
    else:
      raise socket.timeout
    return None
      


  def normalize_value(self, key, value):
    if key in [ 'KDY', 'UL1', 'UDC']:
      return float(int(value, 16)) / 10
    elif key in [ 'IL1', 'IDC', 'TNF', ]:
      return float(int(value, 16)) / 100
    elif key in [ 'PAC', 'PIN', ]:
      return float(int(value, 16)) / 2
    elif key in [ 'SAL', ]:
      return int(value, 16)
    elif key in [ 'SYS', ]:
      (x,y) = value.split(',',2)
      x = int(x, 16)
      y = int(y, 16)
      return (x,y)
    elif key in [ 'SDAT', 'FDAT' ]:
      (date, time) = value.split(',',2)
      time = int(time, 16)
      return datetime.datetime(int(date[:3], 16), int(date[3:5], 16), int(date[5:], 16), time/3600, (time % 3600) / 60, time % (3600*60))
    else:
      return int(value, 16)


  def write_setting(self, inverter, data):
    rawdata = []
    for key,value in data.iteritems():
      key = key.upper()
      if key not in query_types:
        raise ValueError('unknown type')
      value = self.hexval(value)
      rawdata.append('%s=%s' % (key, value))
    DEBUG(self.query(inverter, ';'.join(rawdata), 200))


  def status(self, inverter):
    result = self.query(inverter, ['SYS', 'SAL'])
    if not result:
      return ('Offline', 'Offline')
    result = result[1]
    errors = []
    if result['SAL'] > 0:
      for (code, descr) in alarm_codes.iteritems():
        if code & result['SAL']:
          errors.append(descr)

    status = status_codes[result['SYS'][0]]
    return (status, ', '.join(errors))


  def use_inverters(self, list_of):
    self.__inverter_list = list_of
    self.detect_inverters()


  def detect_inverters(self):
    self.__inverters = {}
    if not self.__connected:
      self.__connect()
    self.__detection_running = True
    for inverter in self.__inverter_list:
      try:
        DEBUG('searching for #%i (socket: %s)' % (inverter, self.__socket))
        (inverter, data) = self.query(inverter, [ 'ADR', 'TYP', 'PIN' ])
        if data['TYP'] in inverter_types.keys():
          self.__inverters[inverter] = inverter_types[data['TYP']].copy()
          self.__inverters[inverter]['installed'] = data['PIN']
        else:
          DEBUG('Unknown inverter type: %s (ID #%i)' % (data['TYP'], data['ADR']))
      except:
        DEBUG('Inverter #%i not found' % inverter)
        self.__allinverters = False
    self.__detection_running = False
    if len(self.__inverters) == len(self.__inverter_list):
      self.__allinverters = True
      DEBUG('found all inverters:')
      DEBUG(self.__inverters)
    else:
      DEBUG('not all invertes found, reconnection!')
      self.__connect()
      

  def inverters(self):
    if not self.__allinverters:
      self.detect_inverters()
    return self.__inverters

  











