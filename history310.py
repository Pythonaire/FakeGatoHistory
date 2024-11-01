#!/usr/bin/env python3
import logging, time, math, re, base64
from collections import defaultdict
from timer import FakeGatoTimer
from storage import FakeGatoStorage
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

EPOCH_OFFSET = 978307200

class FakeGatoHistory():
    def __init__(self, accessoryType, accessory, storage= None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accessory, self.accessoryName, self.accessoryType = accessory, accessory.display_name, accessoryType
        self.memorySize, self.minutes, self.currentEntry = 4032, 10, 1
        self.firstEntry = self.lastEntry = self.usedMemory = self.refTime = self.memoryAddress = 0
        self.setTime = self.restarted = True
        self.entry2address = lambda e: e % self.memorySize
        self.history = [self.accessoryName]
        self.transfer = False
        self.dataStream = ''
        self.storage = storage
        
        logging.info('Registring Events {0}'.format(self.accessoryName))
        self.service = self.accessory.add_preload_service('History', chars =['HistoryStatus','HistoryEntries','HistoryRequest','SetTime'])
        #logging.info("self.service: {0}, self.service.type: {1}".format(self.service, type(self.service)))
        self.HistoryEntries = self.service.configure_char("HistoryEntries")
        self.HistoryRequest = self.service.configure_char('HistoryRequest')
        self.HistoryStatus = self.service.configure_char("HistoryStatus")
        self.CurrentTime = self.service.configure_char('SetTime')
        self.HistoryEntries.getter_callback = self.getCurrentHistoryEntries
        self.HistoryRequest.setter_callback = self.setCurrentHistoryRequest
        self.CurrentTime.setter_callback = self.setCurrentSetTime
        if self.storage == None: self.loaded = False

        self.globalFakeGatoTimer = FakeGatoTimer(self.minutes,  self.accessoryName)

        if self.storage != None:
            self.globalFakeGatoStorage = FakeGatoStorage(self.accessoryName)
            self.globalFakeGatoStorage.addWriter(self)
            self.load() # load data at restart of service
            while self.loaded == False: # wait until data loaded from file
                time.sleep(0.1)

        match self.accessoryType:
            case 'weather':
                self.accessoryType116 = "03 0102 0202 0302"
                self.accessoryType117 = "07"
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)
            case 'energy':
                self.accessoryType116 = "04 0102 0202 0702 0f03"
                self.accessoryType117 = "1f"
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)
            case 'room':
                self.accessoryType116 = "04 0102 0202 0402 0f03"
                self.accessoryType117 = "0f"
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)
            case 'room2':
                self.accessoryType116 = "07 0102 0202 2202 2901 2501 2302 2801"
                self.accessoryType117 = "7f"
                self.globalFakeGatoTimer.subscribe(self, self.calculateAverage)
            case 'door':
                self.accessoryType116 = "01 0601"
                self.accessoryType117 = "01"
                self.globalFakeGatoTimer.subscribe(self, self.select_types)
            case 'motion':
                self.accessoryType116 = "02 1301 1c01"
                self.accessoryType117 = "02"
                self.globalFakeGatoTimer.subscribe(self, self.select_types)
            case 'switch':
                self.accessoryType116 = "01 0e01"
                self.accessoryType117 = "01"
                self.globalFakeGatoTimer.subscribe(self, self.select_types)
            case 'aqua':
                self.accessoryType116 = "03 1f01 2a08 2302"
                self.accessoryType117 = "05"
                self.accessoryType117bis = "07"
            case 'thermo':
                self.accessoryType116 = "05 0102 1102 1001 1201 1d01"
                self.accessoryType117 = "1f"

            
    @classmethod
    def swap16(cls, i):
        return ((i & 0xFF) << 8) | ((i >> 8) & 0xFF)

    @classmethod
    def swap32(cls, i):
        return ((i & 0xFF) << 24) | ((i & 0xFF00) << 8) | ((i >> 8) & 0xFF00) | ((i >> 24) & 0xFF)

    def format32(self, value):
        return format(self.swap32(int(value)), '08X')

    def format16(self, value):
        return format(self.swap16(int(value)), '04X')

    @classmethod
    def precisionRound(cls, num, prec):
        factor = math.pow(10, prec)
        return round(num * factor) / factor

    @classmethod
    def hexToBase64(cls, x):
        string = re.sub(r"[^0-9A-F]", '', ('' + x), flags = re.I)
        b = bytearray.fromhex(string)
        return base64.b64encode(b).decode('utf-8')
    
    @classmethod
    def base64ToHex(cls, x):
        if len(x) == 0:
            return x
        else:
            return base64.b64decode(x).hex()

    def summarize_backLog(self, dict_list):
        result = defaultdict(int)
        for d in dict_list:
            for k, v in d.items():
                result[k] += v
        return dict(result)

    def calculateAverage(self, params): # callback
        backLog = [{k: v for k, v in d.items() if k != 'time'} for d in params['backLog']] if 'backLog' in params else []
        previousAvrg = params['previousAvrg'] if 'previousAvrg' in params else {}
        #timer = params['timer']
        summarized = self.summarize_backLog(backLog)
        avrg = {k:self.precisionRound(v/len(backLog),2) for k, v in summarized.items()} # divided values by counted list
        if 'voc' in avrg: avrg['voc']=int(avrg['voc'])
        avrg['time'] = int(round(time.time()))
        listVal = [key for key in previousAvrg if key!='time']
        for index in listVal:
            if len(backLog) == 0 or (index not in avrg):
                avrg[index] = previousAvrg[index]
        if len(avrg) > 1:
            self._addEntry(avrg)
            self.globalFakeGatoTimer.emptyData(self)
            #timer.emptyData(self)
        return avrg

    def select_types(self, params): # callback
        backLog = params['backLog'] if 'backLog' in params else []
        immediate = params['immediate']
        actualEntry = {}
        if len(backLog) != 0:
            if immediate == None:
                actualEntry['time'] = int(round(time.time()))
                actualEntry['status'] = backLog[0]['status']
            else:
                actualEntry['time'] = backLog[0]['time']
                actualEntry['status'] = backLog[0]['status']
            self._addEntry(actualEntry)


    def addEntry(self, entry):
        self.entry = entry
        match self.accessoryType:
            case 'door' | 'motion' | 'switch':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self, 'immediateCallback': True})
            case 'aqua':
                self._addEntry({ 'time': self.entry['time'], 'status': self.entry['status'], 'waterAmount': self.entry['waterAmount'] , 'immediateCallback': True})
            case 'weather':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case 'room':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case 'room2':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case 'energy':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case _:
                self._addEntry(self.entry)

    def _addEntry(self, entry): 
        if self.loaded: self.entry2address = lambda e: e % self.memorySize
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
            self.format32(entry['time'] - self.refTime - EPOCH_OFFSET),
            self.format32(self.refTime),
            self.accessoryType116,
            self.format16(self.usedMemory+1),
            self.format16(self.memorySize),
            self.format32(self.firstEntry)
            ))
        else:
            val = ('{0}00000000{1}{2}{3}{4}{5}000000000101'.format(
            self.format32(entry['time'] - self.refTime - EPOCH_OFFSET),
            self.format32(self.refTime),
            self.accessoryType116,
            self.format16(self.usedMemory),
            self.format16(self.memorySize),
            self.format32(self.firstEntry+1)
            ))   
        
        self.HistoryStatus.set_value(self.hexToBase64(val))
        #self.service.configure_char("HistoryStatus", value = hexToBase64(val))
        #logging.info("First entry {0}: {1}".format(self.accessoryName, self.firstEntry))
        #logging.info("Last entry {0}: {1}".format(self.accessoryName, self.lastEntry))
        #logging.info("Used memory {0}: {1}".format(self.accessoryName, self.usedMemory))
        #logging.info("116 {0}: {1}".format(self.accessoryName, val))

        if self.storage != None:
            self.save()
        

    def save(self):
        if self.loaded:
            data = {
            'firstEntry': self.firstEntry,
			'lastEntry': self.lastEntry,
			'usedMemory': self.usedMemory,
			'refTime': self.refTime,
			'initialTime': self.initialTime,
			'history': self.history
            }
            self.globalFakeGatoStorage.write({'service': self, 'data': data})
        

    def load(self):
        logging.info("Loading...")
        data = self.globalFakeGatoStorage.read(self)
        try:
            if len(data)!=0:
                self.firstEntry = data['firstEntry']  # type: ignore
                self.lastEntry = data['lastEntry']  # type: ignore
                self.usedMemory = data['usedMemory']  # type: ignore
                self.refTime = data['refTime']  # type: ignore
                self.initialTime = data['initialTime']  # type: ignore
                self.history = data['history']  # type: ignore
                logging.info("** Loading Cache Data for '{0}', {1} entries **".format(self.accessoryName, self.lastEntry))
                self.globalFakeGatoStorage.remove(self)
        except Exception as e:
            logging.info("** HISTORY CACHE is empty, restart from zero - or invalid JSON **".format(e))
        self.loaded = True

    def getCurrentHistoryEntries(self):
        self.entry2address = lambda e: e % self.memorySize
        if (self.currentEntry <= self.lastEntry) and (self.transfer == True):
            self.memoryAddress = self.entry2address(self.currentEntry)
            for x in self.history:
                if self.history[self.memoryAddress].get('setRefTime') == 1 or self.setTime == True or self.currentEntry == self.firstEntry +1:
                    self.dataStream = "".join([self.dataStream, ",15", self.format32(self.currentEntry),
                    " 0100 0000 81", self.format32(self.refTime), "0000 0000 00 0000"
                    ])
                    self.setTime = False
                else:
                    match self.accessoryType:
                        case 'weather':
                            self.dataStream = "".join([self.dataStream, ",10 ", self.format32(self.currentEntry),
                            self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
                            "-", self.accessoryType117, ":", self.format16(self.history[self.memoryAddress].get('temp') * 100),
                            " ", self.format16(self.history[self.memoryAddress].get('humidity') * 100),
                            " ", self.format16(self.history[self.memoryAddress].get('pressure') * 10)
                            ])
                        case 'energy':
                            self.dataStream = "".join([self.dataStream, ",14 ", self.format32(self.currentEntry),
                            self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
                            "-", self.accessoryType117, ":0000 0000 ", self.format16(self.history[self.memoryAddress].get('power') * 10),
                            " 0000 0000"
                            ])
                        case 'room':
                            self.dataStream = "".join([self.dataStream, ",13 ", self.format32(self.currentEntry),
                            self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
			                self.accessoryType117,
			                self.format16(self.history[self.memoryAddress].get('temp') * 100),
			                self.format16(self.history[self.memoryAddress].get('humidity') * 100),
			                self.format16(self.history[self.memoryAddress].get('ppm')),
                            "0000 00"
                            ])
                        case 'room2':
                            self.dataStream = "".join([self.dataStream, ",15 ", self.format32(self.currentEntry),
                            self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
                            self.accessoryType117,
                            self.format16(self.history[self.memoryAddress].get('temp') * 100),
                            self.format16(self.history[self.memoryAddress].get('humidity') * 100),
                            self.format16(self.history[self.memoryAddress].get('voc')),
                            "0054 a80f01"
                            ])
                        case 'door' | 'motion' | 'switch':
                            self.dataStream = "".join([self.dataStream, ",0b ", self.format32(self.currentEntry),
                            self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
			                self.accessoryType117,
			                format(self.history[self.memoryAddress].get('status'), '02X')
                            ])
                        case 'aqua':
                            if self.history[self.memoryAddress].get('status') == True:
                                self.dataStream = "".join([self.dataStream, ",0d ", self.format32(self.currentEntry),
                                self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
			                    self.accessoryType117,
			                    format(self.history[self.memoryAddress].get('status'), '02X'),
                                " 300c"
                                ])
                            else:
                                self.dataStream = "".join([self.dataStream, ",15 ", self.format32(self.currentEntry),
                                self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
			                    self.accessoryType117bis,
			                    format(self.history[self.memoryAddress].get('status'), '02X'),
			                    self.format32(self.history[self.memoryAddress].get('waterAmount')),
                                " 00000000 300c"
                                ])
                        case 'thermo':
                            self.dataStream = "".join([self.dataStream, ",11 ", self.format32(self.currentEntry),
                            self.format32(self.history[self.memoryAddress].get('time') - self.refTime - EPOCH_OFFSET),
                            self.accessoryType117,
			                self.format16(self.history[self.memoryAddress].get('currentTemp') * 100),
			                self.format16(self.history[self.memoryAddress].get('setTemp') * 100),
			                format(self.history[self.memoryAddress].get('valvePosition'), '02X'),
                            " 0000"
                            ])
                self.currentEntry += 1
                self.memoryAddress = self.entry2address(self.currentEntry)
                if (self.currentEntry > self.lastEntry):
                    break
            #logging.info("Data {0}: {1}".format(self.accessoryName, self.dataStream))
            sendStream= self.dataStream
            self.dataStream =''
            return self.hexToBase64(sendStream)
        else:
            self.transfer = False
            return self.hexToBase64('00')

    def setCurrentHistoryRequest(self, val):
        valHex = self.base64ToHex(val)
        #logging.info("Data request {0}: {1}".format(self.accessoryName, valHex))
        valInt = int(valHex[4:12], base=16)
        address = self.swap32(valInt)
        #hexAddress = '{:x}'.format(address)
        #logging.info("Address requested {0}: {1}".format(self.accessoryName, address))
        self.currentEntry = address if address != 0 else  1
        self.transfer = True

    def setCurrentSetTime(self, val):
        x = bytearray(base64.b64decode(val))
        x.reverse()
        date_time = datetime.fromtimestamp(EPOCH_OFFSET + int(x.hex(),16))
        d = date_time.strftime("%d.%m.%Y, %H:%M:%S")
        #logging.info("Data uploded for {0}: {1} - {2}".format(self.accessoryName, self.base64ToHex(val), d))
        #logging.info("Data uploded for {0} at {1}".format(self.accessoryName, d))
        