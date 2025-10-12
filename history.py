import logging, time, math, base64, re
from collections import defaultdict
from timer import FakeGatoTimer
from storage import FakeGatoStorage
from datetime import datetime
import os, psutil, shutil

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
        self.history = []
        self.transfer = False
        self.dataStream = ''
        self.storage = storage
        self.lastSentEntry = 0  # Track last entry sent to HomeKit for pruning

        logging.info('Registring Events {0}'.format(self.accessoryName))
        self.service = self.accessory.add_preload_service('History', chars =['HistoryStatus','HistoryEntries','HistoryRequest','SetTime'])
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

    def format16(self, value):
        return format(((int(value) & 0xFF) << 8) | ((int(value) >> 8) & 0xFF), '04X')
    
    @classmethod
    def swap32(cls, i):
        return ((i & 0xFF) << 24) | ((i & 0xFF00) << 8) | ((i >> 8) & 0xFF00) | ((i >> 24) & 0xFF)

    def format32(self, value):
        return format(self.swap32(int(value)), '08X')

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
        return x if len(x) == 0 else base64.b64decode(x).hex()

    def summarize_backLog(self, dict_list):
        result = defaultdict(int)
        for d in dict_list:
            for k, v in d.items():
                result[k] += v
        return dict(result)

    def calculateAverage(self, params): # callback
        backLog = [{k: v for k, v in d.items() if k != 'time'} for d in params['backLog']] if 'backLog' in params else []
        previousAvrg = params['previousAvrg'] if 'previousAvrg' in params else {}
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
                self._addEntry({ 'time': self.entry['time'], 'status': self.entry['status'], 'waterAmount': self.entry['waterAmount']})
            case 'weather':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case 'room':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case 'room2':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case 'energy':
                self.globalFakeGatoTimer.addData({ 'entry': self.entry, 'service': self})
            case 'custom':
                for service in self.accessory.services:
                    for characteristic in service.characteristics:
                        displayName = characteristic.display_name
                        uuid = getattr(characteristic, 'type_id', None)
                        print(f"service.characteristics {displayName} uuid: {uuid}")
            case _:
                self._addEntry(self.entry)

    def _addEntry(self, entry): 
        if self.loaded:
            self.entry2address = lambda e: e % self.memorySize
        # If this is the first ever entry, set reference time and add a setRefTime dict
        if self.refTime == 0:
            self.refTime = entry['time'] - EPOCH_OFFSET
            self.initialTime = entry['time']
            # Add the first reference time entry as a dict, not a string
            self.history.append({'time': entry['time'], 'setRefTime': 1})
            self.firstEntry = 0
            self.usedMemory = 1
            self.lastEntry = self.firstEntry + self.usedMemory - 1
        # Now add the actual entry
        if self.usedMemory < self.memorySize:
            self.history.append(entry)
            self.usedMemory += 1
            self.lastEntry = self.firstEntry + self.usedMemory - 1
        else:
            # Overwrite oldest entry (circular buffer)
            self.firstEntry += 1
            overwrite_index = self.entry2address(self.lastEntry + 1)
            if overwrite_index < len(self.history):
                self.history[overwrite_index] = entry
            else:
                self.history.append(entry)
            self.lastEntry = self.firstEntry + self.usedMemory - 1
        entryTime = self.format32(entry['time'] - self.refTime - EPOCH_OFFSET)
        refTime = self.format32(self.refTime)
        memorySize = self.format16(self.memorySize)
        if self.usedMemory < self.memorySize:
            usedMemory = self.format16(self.usedMemory)
            firstEntry = self.format32(self.firstEntry)
        else:
            usedMemory = self.format16(self.usedMemory)
            firstEntry = self.format32(self.firstEntry)
        val = f'{entryTime}00000000{refTime}{self.accessoryType116}{usedMemory}{memorySize}{firstEntry}000000000101'
        self.HistoryStatus.set_value(self.hexToBase64(val))
        if self.storage is not None:
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
        # In-memory backup: read the raw JSON data before parsing
        self._memory_backup_data = None
        try:
            storage_path = getattr(self.globalFakeGatoStorage, 'getStorageFilePath', None)
            if storage_path is not None:
                storage_file = self.globalFakeGatoStorage.getStorageFilePath(self)
            else:
                # Fallback: guess file name
                storage_file = f"{self.accessoryName}.json"
            # Read the file's raw contents for in-memory backup
            if os.path.exists(storage_file):
                with open(storage_file, 'r') as f:
                    self._memory_backup_data = f.read()
        except Exception as e:
            logging.warning(f"Could not create in-memory backup: {e}")
        # Try to parse the data as usual
        data = self.globalFakeGatoStorage.read(self)
        try:
            if isinstance(data, dict) and data:
                self.firstEntry = data.get('firstEntry', 0)
                self.lastEntry = data.get('lastEntry', 0)
                self.usedMemory = data.get('usedMemory', 0)
                self.refTime = data.get('refTime', 0)
                self.initialTime = data.get('initialTime', 0)
                self.history = data.get('history', [])
                logging.info("** Loading Cache Data for '{0}', {1} entries **".format(self.accessoryName, max(0, self.lastEntry - self.firstEntry + 1)))
            else:
                logging.info("** No valid persistent data found; starting fresh **")
        except Exception as e:
            logging.info(f"** HISTORY CACHE is empty, restart from zero - or invalid JSON : {e}")
            # Try to restore from in-memory backup if available
            if getattr(self, "_memory_backup_data", None):
                logging.info("Attempting to restore from in-memory backup...")
                import json
                try:
                    backup_data = json.loads(self._memory_backup_data)
                    self.firstEntry = backup_data.get('firstEntry', 0)
                    self.lastEntry = backup_data.get('lastEntry', 0)
                    self.usedMemory = backup_data.get('usedMemory', 0)
                    self.refTime = backup_data.get('refTime', 0)
                    self.initialTime = backup_data.get('initialTime', 0)
                    self.history = backup_data.get('history', [])
                    logging.info("** Successfully restored history from in-memory backup. **")
                except Exception as ee:
                    logging.warning(f"Failed to restore from in-memory backup: {ee}")
        self.loaded = True

    def getCurrentHistoryEntries(self):
        self.entry2address = lambda e: e % self.memorySize
        # Build dataStream efficiently using a list of strings
        dataStream_parts = []
        sent_from = self.currentEntry
        sent_to = self.lastEntry
        sent_any = False
        # Safely access self.history (list of dicts), and robustly handle missing keys
        num_entries_to_send = max(0, self.lastEntry - self.currentEntry + 1) if self.transfer else 0
        if (self.currentEntry <= self.lastEntry) and (self.transfer is True):
            while self.currentEntry <= self.lastEntry and self.transfer:
                self.memoryAddress = self.entry2address(self.currentEntry)
                # Defensive: check index and type
                entry = {}
                try:
                    entry = self.history[self.memoryAddress]
                    if not isinstance(entry, dict):
                        entry = {}
                except Exception:
                    entry = {}
                currEntry = self.format32(self.currentEntry)
                setRefTime = entry.get('setRefTime', 0)
                # Use .get with defaults for all entry accesses
                if setRefTime == 1 or self.setTime is True or self.currentEntry == self.firstEntry + 1:
                    time_hex = self.format32(self.refTime)
                    dataStream_parts.append(f",15{currEntry} 0100 0000 81{time_hex}0000 0000 00 0000")
                    self.setTime = False
                else:
                    # Defensive for 'time'
                    time_val = entry.get('time', self.refTime + EPOCH_OFFSET)
                    try:
                        time_hex = self.format32(time_val - self.refTime - EPOCH_OFFSET)
                    except Exception:
                        time_hex = self.format32(0)
                    match self.accessoryType:
                        case 'weather':
                            temp = self.format16(entry.get('temp', 0) * 100)
                            humidity = self.format16(entry.get('humidity', 0) * 100)
                            pressure = self.format16(entry.get('pressure', 0) * 10)
                            dataStream_parts.append(f",10 {currEntry}{time_hex}-{self.accessoryType117}:{temp} {humidity} {pressure}")
                        case 'energy':
                            power = self.format16(entry.get('power', 0) * 10)
                            dataStream_parts.append(f",14 {currEntry}{time_hex}-{self.accessoryType117}:0000 0000 {power} 0000 0000")
                        case 'room':
                            temp = self.format16(entry.get('temp', 0) * 100)
                            humidity = self.format16(entry.get('humidity', 0) * 100)
                            ppm = self.format16(entry.get('ppm', 0))
                            dataStream_parts.append(f",13 {currEntry}{time_hex}{self.accessoryType117}{temp}{humidity}{ppm}0000 00")
                        case 'room2':
                            temp = self.format16(entry.get('temp', 0) * 100)
                            humidity = self.format16(entry.get('humidity', 0) * 100)
                            voc = self.format16(entry.get('voc', 0))
                            dataStream_parts.append(f",15 {currEntry}{time_hex}{self.accessoryType117}{temp}{humidity}{voc}0054 a80f01")
                        case 'door' | 'motion' | 'switch':
                            status = format(entry.get('status', 0), '02X')
                            dataStream_parts.append(f",0b {currEntry}{time_hex}{self.accessoryType117}{status}")
                        case 'aqua':
                            status_val = entry.get('status', 0)
                            status = format(int(bool(status_val)), '02X')
                            if status_val is True:
                                dataStream_parts.append(f"+,0d {currEntry}{time_hex}{self.accessoryType117}{status} 300c")
                            else:
                                waterAmount = self.format32(entry.get('waterAmount', 0))
                                dataStream_parts.append(f",15 {currEntry}{time_hex}{self.accessoryType117bis}{status}{waterAmount} 00000000 300c")
                        case 'thermo':
                            currtemp = self.format16(entry.get('currentTemp', 0) * 100)
                            settemp = self.format16(entry.get('setTemp', 0) * 100)
                            valvePos = format(entry.get('valvePosition', 0), '02X')
                            dataStream_parts.append(f",11 {currEntry}{time_hex}{self.accessoryType117}{currtemp}{settemp}{valvePos} 0000")
                self.currentEntry += 1
                sent_any = True
                # Defensive: re-calculate memoryAddress for next loop
                self.memoryAddress = self.entry2address(self.currentEntry)
                if self.currentEntry > self.lastEntry:
                    break
            # After processing, reset transfer flag
            self.transfer = False
            sendStream = ''.join(dataStream_parts)
            # --- Prune sent entries from history ---
            prune_to = self.currentEntry - 1
            logging.info(f"Sending {num_entries_to_send} entries to HomeKit from {sent_from} to {sent_to}")
            self.pruneSentHistory(sent_any, prune_to)
            return self.hexToBase64(sendStream)
        else:
            self.transfer = False
            logging.info("No history entries sent to HomeKit (nothing to send).")
            return self.hexToBase64('00')

    def pruneSentHistory(self, sent_any, prune_to):
        """
        Prune sent entries from history up to prune_to (inclusive), update firstEntry, usedMemory, lastEntry, and lastSentEntry.
        Always keep at least RETENTION last entries in memory and persistent storage.
        Only clear the persistent storage file if at least one entry is actually pruned.
        Logging indicates both pruning and retention.
        """
        RETENTION = 10
        pruned = False
        if sent_any and prune_to >= self.lastSentEntry:
            total_entries = self.usedMemory
            max_pruneable = max(0, total_entries - RETENTION)
            num_to_prune = min(prune_to - self.firstEntry + 1, max_pruneable)
            if num_to_prune > 0 and self.usedMemory > 0:
                self.history = self.history[num_to_prune:]
                self.firstEntry += num_to_prune
                self.usedMemory -= num_to_prune
                if self.usedMemory < 0:
                    self.usedMemory = 0
                if self.firstEntry > self.lastEntry:
                    self.lastEntry = self.firstEntry
                logging.info(f"Pruned {num_to_prune} entries from history. Used memory: {self.usedMemory}.")
                pruned = True
            else:
                logging.info(f"No entries pruned from history; RETENTION of {RETENTION} entries maintained.")
            self.lastSentEntry = prune_to
            # Only clear the storage file if at least one entry was pruned
            if pruned and self.storage is not None:
                self.globalFakeGatoStorage.remove(self)
            elif not pruned and self.storage is not None:
                logging.info(f"Persistent storage file retained; minimum {RETENTION} entries remain in memory and storage.")

    def setCurrentHistoryRequest(self, val):
        valHex = self.base64ToHex(val)
        valInt = int(valHex[4:12], base=16)
        address = self.swap32(valInt)
        self.currentEntry = address if address != 0 else  1
        self.transfer = True

    def setCurrentSetTime(self, val):
        x = bytearray(base64.b64decode(val))
        x.reverse()
        date_time = datetime.fromtimestamp(EPOCH_OFFSET + int(x.hex(),16))
        d = date_time.strftime("%d.%m.%Y, %H:%M:%S")
        