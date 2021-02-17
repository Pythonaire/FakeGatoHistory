#!/usr/bin/env python3
import logging, os, time, math, re, base64
from pyhap.accessory import Accessory
from timer import FakeGatoTimer
from storage import FakeGatoStorage

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

''' add additional service and characteristics to /usr/local/lib/python3.x/dist-packages/pyhap/ressources

services.json:

    "History": {
    "OptionalCharacteristics": [
     "Name" 
    ],
   "RequiredCharacteristics": [
   "S2R1",
   "S2R2",
   "S2W1",
   "S2W2"
   ],
   "UUID": "E863F007-079E-48FF-8F27-9C2605A29F52"

 characteristics.json:

    "S2R1": {
      "Format" :"data",
      "Permissions": [
         "pr",
	    "pw",
         "ev",
         "hd"
      ],
      "UUID": "E863F116-079E-48FF-8F27-9C2605A29F52"
   },
   "S2R2": {
      "Format" :"data",
      "Permissions": [
         "pr",
         "pw",
         "ev",
         "hd"
      ],
      "UUID": "E863F117-079E-48FF-8F27-9C2605A29F52"
   },
   "S2W1": {
      "Format" :"data",
      "Permissions": [
	    "pw",
        "hd"
      ],
      "UUID": "E863F11C-079E-48FF-8F27-9C2605A29F52"
   },
   "S2W2": {
      "Format" :"data",
      "Permissions": [
	    "pw",
        "hd"
      ],
      "UUID": "E863F121-079E-48FF-8F27-9C2605A29F52"
   }
'''

EPOCH_OFFSET = 978307200
TYPE_ENERGY = 'energy'
TYPE_ROOM = 'room'
TYPE_WEATHER = 'weather'
TYPE_DOOR = 'door'
TYPE_MOTION = 'motion'
TYPE_SWITCH = 'switch'
TYPE_THERMO = 'thermo'
TYPE_AQUA = 'aqua',
TYPE_CUSTOM = 'custom'

def precisionRound(num, prec):
    factor = math.pow(10, prec)
    return round(num * factor) / factor

def hexToBase64(x):
    string = re.sub(r"[^0-9A-F]", '', ('' + x), flags = re.I)
    #replace [^0-9A-F] with '' in (''+val) IGNORE case sensitivity
    b = bytearray.fromhex(string)
    return base64.b64encode(b).decode('utf-8')
    
def base64ToHex(x):
    if len(x) == 0:
        return x
    else:
        return base64.b64decode(x).hex()

def swap16(i):
	return ((i & 0xFF) << 8) | ((i >> 8) & 0xFF)

def swap32(i):
    return ((i & 0xFF) << 24) | ((i & 0xFF00) << 8) | ((i >> 8) & 0xFF00) | ((i >> 24) & 0xFF)


class FakeGatoHistory():
    def __init__(self,accessoryType, accessory, optionalParams=None, *args, **kwargs):
        super().__init__(*args, **kwargs) 
        self.signatures = []
        self.extra= None
        self.accessory = accessory
        self.accessoryName = self.accessory.display_name
        self.accessoryType = accessoryType
        self.entry2address = lambda e: e % self.memorySize
        
        if isinstance(optionalParams, dict):
            # javascript ternary equivalent with Lambda
            #  condition ? true : false
            # (lambda: False, lambda: true)[condition]()
            currpath = os.getcwd()
            autoFileDescriptor = currpath + '/' + self.accessoryName +'_History' + '_persist.json'
            self.size = (lambda: 4032, lambda: optionalParams['size'])['size' in optionalParams]()
            self.minutes = (lambda: 10, lambda: optionalParams['minutes'])['minutes' in optionalParams]()
            self.disableTimer = (lambda: False, lambda: optionalParams['disableTimer'])['disableTimer' in optionalParams]()
            self.disableRepeatLastData = (lambda: False, lambda: optionalParams['disableRepeatLastData'])['disableRepeatLastData' in optionalParams]()
            self.storage = (lambda : None, lambda: 'fs')['storage' in optionalParams]()
            self.fileName = (lambda: autoFileDescriptor, lambda: currpath + optionalParams['fileName'])['fileName' in optionalParams]()
        else:
            self.size = 4032
            self.minutes = 10
            self.disableTimer = False
            self.storage = None
            self.chars = None
            self.disableRepeatLastData = False
            # use logging.info instead of optionalParams.log || self.Accessory.log || {};


        if self.disableTimer == False:
            self.globalFakeGatoTimer = FakeGatoTimer({'minutes':self.minutes})

        if self.storage != None:
            self.globalFakeGatoStorage = FakeGatoStorage(params=None)
            ready = self.globalFakeGatoStorage.addWriter(self, { # return with true, if file exists or generated 
                'storage': self.storage,
                'fileName': self.fileName})
            if ready == True:
                self.loaded = self.load()


        if self.accessoryType == TYPE_WEATHER:
            self.accessoryType116 = "03 0102 0202 0302"
            self.accessoryType117 = "07"
            if self.disableTimer == False:
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)
        elif self.accessoryType == TYPE_ENERGY:
            self.accessoryType116 = "04 0102 0202 0702 0f03"
            self.accessoryType117 = "1f"
            if self.disableTimer == False:
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)
        elif self.accessoryType == TYPE_ROOM:
            self.accessoryType116 = "04 0102 0202 0402 0f03"
            self.accessoryType117 = "0f"
            if self.disableTimer == False:
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)
        elif self.accessoryType == TYPE_DOOR:
            self.accessoryType116 = "01 0601"
            self.accessoryType117 = "01"
            self.globalFakeGatoTimer.subscribe(self, self.select_types)
        elif self.accessoryType == TYPE_MOTION:
            self.accessoryType116 = "02 1301 1c01"
            self.accessoryType117 = "02"
            self.globalFakeGatoTimer.subscribe(self, self.select_types)
        elif self.accessoryType == TYPE_SWITCH:
            self.accessoryType116 = "01 0e01"
            self.accessoryType117 = "01"
            self.globalFakeGatoTimer.subscribe(self, self.select_types)
        elif self.accessoryType == TYPE_AQUA:
            self.accessoryType116 = "03 1f01 2a08 2302"
            self.accessoryType117 = "05"
            self.accessoryType117bis = "07"
        elif self.accessoryType == TYPE_THERMO:
            self.accessoryType116 = "05 0102 1102 1001 1201 1d01"
            self.accessoryType117 = "1f"
        elif self.accessoryType == TYPE_CUSTOM:
            if self.chars == None:
                logging.info(' **** missing custom characteristic definition ******')
            sorter = []
            for x in self.chars:
                if x == 'temp': 
                    self.signatures.append({'signature': '0102', 'length': 4, 'factor': 100, 'entry': 'temp'})
                    sorter.append('0102')
                elif x == 'hum':
                    self.signatures.append({'signature': '0202', 'length': 4, 'factor': 100, 'entry': 'humidity'})
                    sorter.append('0202')
                elif x == 'power':
                    self.signatures.append({'signature': '0702', 'length': 4, 'factor': 10, 'entry': 'power'})
                    sorter.append('0702')
                elif x == 'pressure':
                    self.signatures.append({'signature': '0302', 'length': 4, 'factor': 10, 'entry': 'pressure'})
                    sorter.append('0202')
                elif x == 'ppm':
                    self.signatures.append({'signature': '0702', 'length': 4, 'factor': 10, 'entry': 'ppm'})
                    sorter.append('0702')
                elif x == 'contact':
                    self.signatures.append({'signature': '0602', 'length': 2, 'factor': 1, 'entry': 'contact'})
                    sorter.append('0602')
                elif x == 'switch':
                    self.signatures.append({'signature': '0e01', 'length': 2, 'factor': 1, 'entry': 'status'})
                    sorter.append('0e01')
                elif x == 'motion':
                    self.signatures.append({'signature': '0c01', 'length': 2, 'factor': 1, 'entry': 'motion'})
                    sorter.append('0c01')
            sorter.sort()
            t = ''
            for i in sorter:
                t = t + i + ' '
            self.accessoryType116 =(' 0' + str(len(self.signatures)) + ' ' + t)
            logging.info("Services: {0}:".format(self.accessoryType116))
            if self.disableTimer == False:
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)

        
        self.firstEntry = 0
        self.lastEntry = 0
        self.history = [None]
        self.memorySize = self.size
        self.usedMemory = 0
        self.currentEntry = 1
        self.transfer = False
        self.setTime = True
        self.restarted = True
        self.refTime = 0
        self.memoryAddress = 0 
        self.dataStream = ''
        self.saving = False
        self.registerEvents()
        if self.storage == None:
            self.loaded = True
        
    def registerEvents(self):
        logging.info('Registring Events {0}'.format(self.accessoryName))
        self.service = self.accessory.add_preload_service('History', chars =['S2R1','S2R2','S2W1','S2W2'])
        self.S2R2 = self.service.configure_char("S2R2")
        self.S2W1 = self.service.get_characteristic('S2W1')
        self.S2W2 = self.service.get_characteristic('S2W2')
        self.S2W1.setter_callback = self.setCurrentS2W1
        self.S2W2.setter_callback = self.setCurrentS2W2

    def calculateAverage(self, params): # callback
        backLog = (lambda: [], lambda: params['backLog'])['backLog' in params]()
        previousAvrg = (lambda: {}, lambda: params['previousAvrg'])['previousAvrg' in params]()
        timer = params['timer']
        calc = {
		    	'sum': {},
			    'num': {},
			    'avrg': {}
		        }
        if len(backLog) != 0:
            for h in backLog: #list
                for key in h: #dict
                    if key != 'time':
                        if not key in calc['sum']:
                            calc['sum'][key] = 0
                        if not key in calc['num']:
                            calc['num'][key] = 0
                        calc['sum'][key] += h[key]
                        calc['num'][key] += 1
                        calc['avrg'][key] = precisionRound(calc['sum'][key] / calc['num'][key], 2)
        calc['avrg']['time'] = round(time.time())
        if self.disableRepeatLastData == False:
            for key in previousAvrg:
                if key != 'time':
                    if len(backLog) == 0 or (key not in calc['avrg']):
                        calc['avrg'][key] = previousAvrg[key]
        if len(calc['avrg']) > 1:
            self._addEntry(calc['avrg'])
            timer.emptyData(self)
        return calc['avrg']

    def select_types(self, params): # callback
        backLog = (lambda: [], lambda: params['backLog'])['backLog' in params]()
        immediate = params['immediate']
        fakegato = self
        actualEntry = {}
        if len(backLog) != 0:
            if immediate == None:
                actualEntry['time'] = round(time.time())
                actualEntry['status'] = backLog[0]['status']
            else:
                actualEntry['time'] = backLog[0]['time']
                actualEntry['status'] = backLog[0]['status']
            logging.info("**Fakegato-timer callback: {0}, immediate: {1}, entry: {2} ****".format(fakegato.accessoryName, immediate, actualEntry)) 
            self._addEntry(actualEntry)

    def sendHistory(self, address):
        if address != 0:
            self.currentEntry = address
        else:
            self.currentEntry = 1 
        self.transfer = True

    def addEntry(self, entry):
        self.entry = entry
        if self.accessoryType == TYPE_DOOR or self.accessoryType == TYPE_MOTION or self.accessoryType == TYPE_SWITCH:
            if self.disableTimer == False:
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self, 'immediateCallback': True})
            else:
                self._addEntry({'time': self.entry['time'], 'status': self.entry['status']})
        elif self.accessoryType == TYPE_AQUA:
            self._addEntry({ 'time': self.entry['time'], 'status': self.entry['status'], 'waterAmount': self.entry['waterAmount'] })
        elif self.accessoryType == TYPE_WEATHER:
            if self.disableTimer == False:
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            else:
                self._addEntry({'time': self.entry['time'], 'temp': self.entry['temp'], 'humidity': self.entry['humidity'], 'pressure': self.entry['pressure']})
        elif self.accessoryType == TYPE_ROOM:
                if self.disableTimer == False:
                    self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
                else:
                    self._addEntry({'time': self.entry['time'], 'temp': self.entry['temp'], 'humidity': self.entry['humidity'], 'ppm': self.entry['ppm']})
        elif self.accessoryType == TYPE_ENERGY:
            if self.disableTimer == False:
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            else:
                self._addEntry({ 'time': self.entry['time'], 'power': self.entry['power'] })
        elif self.accessoryType == TYPE_CUSTOM:
            if self.disableTimer == False:
                if 'power' in entry or 'temp' in entry:
                    self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self })
                else:
                    self._addEntry(self.entry)
            else:
                self._addEntry(self.entry)
        else:
            self._addEntry(self.entry)

    def _addEntry(self, entry):
        if self.loaded == True:
            self.entry2address = lambda e: e % self.memorySize
            if self.usedMemory < self.memorySize:
                self.usedMemory += 1
                self.firstEntry = 0
                self.lastEntry = self.usedMemory
                self.history.append(self.lastEntry)
            else:
                self.firstEntry += 1
                self.lastEntry = self.firstEntry + self.usedMemory
                self.history.append(self.lastEntry)
                if self.restarted == True:
                    self.history[self.entry2address(self.lastEntry)] = {'time': entry['time'],'setRefTime': 1}
                    self.firstEntry += 1
                    self.lastEntry = self.firstEntry + self.usedMemory
                    self.restarted = False
            if self.refTime == 0:
                self.refTime = entry['time'] - EPOCH_OFFSET
                self.history[self.lastEntry] = {'time': entry['time'],'setRefTime': 1}
                self.initialTime = entry['time']
                self.lastEntry += 1
                self.usedMemory += 1
                self.history.append(self.lastEntry)
            self.history[self.entry2address(self.lastEntry)] = entry
            if self.usedMemory < self.memorySize:
                val = ('{0}00000000{1}{2}{3}{4}{5}000000000101'.format(
                format(swap32(int(entry['time'] - self.refTime - EPOCH_OFFSET)),'08X'),
                format(swap32(int(self.refTime)),'08X'),
                self.accessoryType116,
                format(swap16(int(self.usedMemory + 1)),'04X'),
                format(swap16(int(self.memorySize)),'04X'),
                format(swap32(int(self.firstEntry)),'08X')
                ))
            else:
                val = ('{0}00000000{1}{2}{3}{4}{5}000000000101'.format(
                format(swap32(int(entry['time'] - self.refTime - EPOCH_OFFSET)),'08X'),
                format(swap32(int(self.refTime)),'08X'),
                self.accessoryType116,
                format(swap16(int(self.usedMemory)),'04X'),
                format(swap16(int(self.memorySize)),'04X'),
                format(swap32(int(self.firstEntry+1)),'08X')
                ))
            self.service.configure_char("S2R1", value = hexToBase64(val))
            logging.info("First entry {0}: {1}".format(self.accessoryName, self.firstEntry))
            logging.info("Last entry {0}: {1}".format(self.accessoryName, self.lastEntry))
            logging.info("Used memory {0}: {1}".format(self.accessoryName, self.usedMemory))
            logging.info("116 {0}: {1}".format(self.accessoryName, val))
            if self.storage != None:
                self.save()
        else:
            time.sleep(0.1)
            self._addEntry(entry)

    def getInitialTime(self):
        return self.initialTime

    def setExtraPersistedData(self, extra):
        self.extra = extra

    def getExtraPersistedData(self):
        return self.extra

    def isHistoryLoaded(self):
        return self.loaded

    def save(self):
        data = {
                'firstEntry': self.firstEntry,
		        'lastEntry': self.lastEntry,
		        'usedMemory': self.usedMemory,
		        'refTime': self.refTime,
		        'initialTime': self.initialTime,
		        'history': self.history,
		        'extra': self.extra
		}
        self.globalFakeGatoStorage.write({
                'service': self,
                'data': data
                })

    def load(self):
        logging.info("Loading....")
        data = self.globalFakeGatoStorage.read({'service': self})
        logging.info("read data {0} :".format(data))
        if len(data) != 0:
            for i in data:
                try:
                    params = {
                    'firstEntry': data['firstEntry'],
                    'lastEntry' : data['lastEntry'],
                    'usedMemory' : data['usedMemory'],
                    'refTime' : data['refTime'],
                    'initialTime' : data['initialTime'],
                    'history' : data['history'],
                    'extra' : data['extra']
                    }
                    self.calculateAverage(params)
                except Exception as e:
                    logging.info("**ERROR fetching persisting data  - invalid JSON ** {0}".format(e))
            self.globalFakeGatoStorage.remove({'service': self})
        return True # set self.loaded to True


    def getCurrentS2R2(self):
        self.entry2address = lambda val: val % self.memorySize
        if (self.currentEntry <= self.lastEntry) and (self.transfer == True):
            self.memoryAddress = self.entry2address(self.currentEntry)
            for x in range(10): # 10 ?? -> max 10 values can send per action
                if self.history[self.memoryAddress].get('setRefTime') == 1 or self.setTime == True or self.currentEntry == self.firstEntry +1:
                    self.dataStream  += (",15{0} 0100 0000 81{1}0000 0000 00 0000".format(
                        format(int(swap32(self.currentEntry)), '08X'), 
                        format(int(swap32(self.refTime)), '08X'))
                    )
                    self.setTime = False
                else:
                    logging.info("{0} Entry: {1}, Address: {2}".format(self.accessoryName, self.currentEntry, self.memoryAddress))
                    if self.accessoryType == TYPE_WEATHER:
                        self.dataStream += (",10 {0}{1}-{2}:{3} {4} {5}".format(format(swap32(int(self.currentEntry)), '08X'),
                        format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08X'),
                        self.accessoryType117,
                        format(swap16(int(self.history[self.memoryAddress].get('temp') * 100)), '04X'),
			            format(swap16(int(self.history[self.memoryAddress].get('humidity') * 100)), '04X'),
			            format(swap16(int(self.history[self.memoryAddress].get('pressure') * 10)), '04X'))
                        )
                    elif self.accessoryType == TYPE_ENERGY:
                        self.dataStream += (",14 {0}{1}-{2}:0000 0000 {3} 0000 0000".format(
                        format(swap32(int(self.currentEntry)), '08X'),
                        format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08X'),
			            self.accessoryType117,
			            format(swap16(int(self.history[self.memoryAddress].get('power') * 10)), '04X'))
                        )
                    elif self.accessoryType == TYPE_ROOM:
                        self.dataStream += (",13 {0}{1}{2}{3}{4}{5}0000 00".format(format(swap32(int(self.currentEntry)), '08X'),
                        format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08x'),
			            self.accessoryType117,
			            format(swap16(int(self.history[self.memoryAddress].get('temp') * 100)), '04X'),
			            format(swap16(int(self.history[self.memoryAddress].get('humidity') * 100)), '04X'),
			            format(swap16(int(self.history[self.memoryAddress].get('ppm'))), '04X'))
                        )
                    elif self.accessoryType == TYPE_DOOR or self.accessoryType == TYPE_MOTION or self.accessoryType == TYPE_SWITCH:
                        self.dataStream += (",0b {0}{1}{2}{3}".format(format(swap32(int(self.currentEntry)), '08X'),
                        format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08X'),
			            self.accessoryType117,
			            format(self.history[self.memoryAddress].get('status'), '02X'))
                        )
                    elif self.accessoryType == TYPE_AQUA:
                        if self.history[self.memoryAddress].get('status') == True:
                            self.dataStream += (",0d {0}{1}{2}{3} 300c".format(format(swap32(int(self.currentEntry)), '08X'),
                            format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08X'),
			                self.accessoryType117,
			                format(self.history[self.memoryAddress].get('status'), '02X'))
                            )
                        else:
                            self.dataStream += (",15 {0}{1}{2}{3}{4} 00000000 300c".format(format(swap32(int(self.currentEntry)), '08X'),
			                format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08X'),
			                self.accessoryType117bis,
			                format(self.history[self.memoryAddress].get('status'), '02X'),
			                format(swap32(int(self.history[self.memoryAddress].get('waterAmount'))), '08X'))
                            )
                    elif self.accessoryType == TYPE_THERMO:
                        self.dataStream += (",11 {0}{1}{2}{3}{4}{5} 0000".format(format(swap32(int(self.currentEntry)), '08X'),
                        format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08X'),
                        self.accessoryType117,
			            format(self.history[self.memoryAddress].get('currentTemp') * 100, '04X'),
			            format(self.history[self.memoryAddress].get('setTemp') * 100, '04X'),
			            format(self.history[self.memoryAddress].get('valvePosition'), '02X'))
                        )
                    elif self.accessoryType == TYPE_CUSTOM:
                        result = []
                        bitmask = 0
                        dataStream = ("{0}{1}".format(swap32(int(self.currentEntry)), '08X'),
                        format(swap32(int(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET)), '08X'),
                        )
                        for key, value in self.history[self.memoryAddress]:
                            if key != 'time':
                                for i in range(len(self.signatures)):
                                    if self.signatures[i]['entry'] == key:
                                        if self.signatures[i]['length'] == 8:
                                            result[x] = ('{0}'.format(swap32(int(value * self.signatures[i]['factor'])), '08X'))
                                            break
                                        elif self.signatures[i]['length'] == 4:
                                            result[x] = ('{0}'.format(swap16(int(value * self.signatures[i]['factor'])), '04X'))
                                            break
                                        elif self.signatures[i]['length'] == 2:
                                            result[x] = ('{0}'.format(value * self.signatures[i]['factor'], '02X'))
                                            break
                                        bitmask += round(math.pow(2, i))
                        a = ''
                        for i in result:
                            a = a + i +' '
                        results = dataStream + ' ' + format(bitmask, '02X' ) + ' ' + a
                        self.dataStream += (' ' + '{}'.format(len(re.sub(r"[^0-9A-F]", '', results, flags = re.I))/2+1) + ' ' + results + ',')
                        break

                self.currentEntry += 1
                self.memoryAddress = self.entry2address(self.currentEntry)
                if (self.currentEntry > self.lastEntry):
                    break

            logging.info("Data {0}: {1}".format(self.accessoryName, self.dataStream))
            sendStream= self.dataStream
            self.dataStream =''
            return hexToBase64(sendStream)
        else:
            self.transfer = False
            return hexToBase64('00')

    def setCurrentS2W1(self, val):
        logging.info("Data request {0}: {1}".format(self.accessoryName, base64ToHex(val)))
        valHex = base64ToHex(val)
        substring = valHex[4:12]
        valInt = int(substring, base=16)
        address = swap32(valInt)
        hexAddress = '{:x}'.format(address)
        logging.info("Address requested {0}: {1}".format(self.accessoryName, hexAddress))
        self.sendHistory(address)
        self.S2R2.set_value(self.getCurrentS2R2())

    def setCurrentS2W2(self, val):
        logging.info("Clock adjust {0}: {1}".format(self.accessoryName, base64ToHex(val)))