import logging, time, math, base64, re, json
from collections import defaultdict, deque
from timer import FakeGatoTimer
from storage import FakeGatoStorage
from datetime import datetime
import history_entry_formatter
import os

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

EPOCH_OFFSET = 978307200
HEX_RE = re.compile(r"[^0-9A-F]", re.I)

class FakeGatoHistory():
        # --- Class-level formatter dictionary (shared by all instances) ---
    ENTRY_FORMATTERS = {
        'weather': history_entry_formatter.format_weather_entry,
        'energy': history_entry_formatter.format_energy_entry,
        'room': history_entry_formatter.format_room_entry,
        'room2': history_entry_formatter.format_room2_entry,
        'door': history_entry_formatter.format_door_motion_switch_entry,
        'motion': history_entry_formatter.format_door_motion_switch_entry,
        'switch': history_entry_formatter.format_door_motion_switch_entry,
        'aqua': history_entry_formatter.format_aqua_entry,
        'thermo': history_entry_formatter.format_thermo_entry,
    }

    def __init__(self, accessoryType, accessory, storage= None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accessory, self.accessoryName, self.accessoryType = accessory, accessory.display_name, accessoryType
        self.memorySize, self.minutes, self.currentEntry = 2048, 10, 1
        self.entriesPerDay = int((60 / self.minutes) * 24)  # 144 for 10-min intervals
        self.retentionLimit = 14 * self.entriesPerDay       # 2016 entries
        self.firstEntry = self.lastEntry = self.usedMemory = self.refTime = self.memoryAddress = 0
        self.setTime = self.restarted = True
        self.history = deque(maxlen=self.memorySize)
        self.transfer = False
        self.dataStream = ''
        self.storage = storage

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

         # --- use shared formatter dictionary ---
        self.entry_formatters = self.ENTRY_FORMATTERS

        self.globalFakeGatoTimer = FakeGatoTimer(self.minutes,  self.accessoryName)

        if self.storage != None:
            self.globalFakeGatoStorage = FakeGatoStorage(self.accessoryName)
            self.globalFakeGatoStorage.addWriter(self)
            self.load() # load data at restart of service
            for _ in range(50):
                if self.loaded: break
                time.sleep(0.05)
            else:
                logging.warning("Timeout waiting for storage to load.")

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
        string = HEX_RE.sub('', x)
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
        # If this is the first ever entry, set reference time
        if self.refTime == 0:
            self.refTime = entry['time'] - EPOCH_OFFSET
            self.initialTime = entry['time']
            # Add the first reference time entry
            self.history.append({'time': entry['time'], 'setRefTime': 1})
            self.firstEntry = 0
            self.usedMemory = 1
            self.lastEntry = self.firstEntry + self.usedMemory - 1

        # Append actual entry (deque automatically drops oldest if maxlen exceeded)
        self.history.append(entry)
        self.usedMemory = len(self.history)
        self.firstEntry = max(0, self.lastEntry - self.usedMemory + 1)
        self.lastEntry += 1

        entryTime = self.format32(entry['time'] - self.refTime - EPOCH_OFFSET)
        refTime = self.format32(self.refTime)
        memorySize = self.format16(self.memorySize)
        usedMemory = self.format16(self.usedMemory)
        firstEntry = self.format32(self.firstEntry)
        val = f'{entryTime}00000000{refTime}{self.accessoryType116}{usedMemory}{memorySize}{firstEntry}000000000101'
        self.HistoryStatus.set_value(self.hexToBase64(val))

        if self.storage is not None:
            self.save()

        # Automatically prune if history exceeds retention
        if len(self.history) > getattr(self, "retentionLimit", 2016):
            self.pruneSentHistory()
        
    def save(self):
        if self.loaded:
            data = {
                'firstEntry': self.firstEntry,
                'lastEntry': self.lastEntry,
                'usedMemory': self.usedMemory,
                'refTime': self.refTime,
                'initialTime': self.initialTime,
                'history': list(self.history)  # convert deque to list for JSON
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
                self.history = deque(data.get('history', []), maxlen=self.memorySize)
                logging.info("** Loading Cache Data for '{0}', {1} entries **".format(self.accessoryName, max(0, self.lastEntry - self.firstEntry + 1)))
            else:
                logging.info("** No valid persistent data found; starting fresh **")
        except Exception as e:
            logging.info(f"** HISTORY CACHE is empty, restart from zero - or invalid JSON : {e}")
            # Try to restore from in-memory backup if available
            if getattr(self, "_memory_backup_data", None):
                logging.info("Attempting to restore from in-memory backup...")
                try:
                    backup_data = json.loads(self._memory_backup_data)
                    self.firstEntry = backup_data.get('firstEntry', 0)
                    self.lastEntry = backup_data.get('lastEntry', 0)
                    self.usedMemory = backup_data.get('usedMemory', 0)
                    self.refTime = backup_data.get('refTime', 0)
                    self.initialTime = backup_data.get('initialTime', 0)
                    self.history = deque(backup_data.get('history', []), maxlen=self.memorySize)
                    logging.info("** Successfully restored history from in-memory backup. **")
                except Exception as ee:
                    logging.warning(f"Failed to restore from in-memory backup: {ee}")
        self.loaded = True

    def getCurrentHistoryEntries(self):
        # ensure that currentEntry is always in range after load
        if self.currentEntry < self.firstEntry or self.currentEntry > self.lastEntry:
            self.currentEntry = self.firstEntry + 1
        # Build dataStream efficiently using a list of strings
        dataStream_parts = []
        sent_from = self.currentEntry
        sent_to = self.lastEntry
        atype117 = self.accessoryType117
        atype117bis = getattr(self, "accessoryType117bis", None)
        if (self.currentEntry <= self.lastEntry) and (self.transfer is True):
            num_entries_to_send = self.lastEntry - self.currentEntry + 1
            while self.currentEntry <= self.lastEntry and self.transfer:
                memory_index = self.currentEntry - self.firstEntry
                entry = {}
                try:
                    if memory_index >= 0 and memory_index < len(self.history):
                        entry = list(self.history)[memory_index]
                        if not isinstance(entry, dict):
                            entry = {}
                    else:
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
                    formatter = self.entry_formatters.get(self.accessoryType)
                    if not formatter:
                        logging.warning(f"No formatter found for accessory type: {self.accessoryType}")
                        continue
                    formatted_entry = formatter(self.format16, self.format32, entry, currEntry, time_hex, atype117, atype117bis)
                    dataStream_parts.append(formatted_entry)
                self.currentEntry += 1
                if self.currentEntry > self.lastEntry:
                    break
            # After processing, reset transfer flag
            self.transfer = False
            sendStream = ''.join(dataStream_parts)
            logging.info(f"Sending {num_entries_to_send} entries to HomeKit from {sent_from} to {sent_to}")
            return self.hexToBase64(sendStream)
        else:
            self.transfer = False
            logging.info("No history entries sent to HomeKit (nothing to send).")
            return self.hexToBase64('00')

    def pruneSentHistory(self):
        """
        Automatically discard history older than 14 days (~2016 entries).
        Keeps the last two weeks in memory and on disk.
        """
        try:
            limit = getattr(self, "retentionLimit", 2016)
            if len(self.history) > limit:
                drop = len(self.history) - limit
                self.history = self.history[drop:]
                self.firstEntry = self.lastEntry - len(self.history) +1
                self.usedMemory = len(self.history)
                self.currentEntry = self.firstEntry + 1
                logging.info(f"[History] Pruned {drop} old entries; kept last {len(self.history)}.")
                if self.storage:
                    self.save()
                # else: nothing to prune
        except Exception as e:
            logging.error(f"[History] Error during pruning: {e}")
            
    def setCurrentHistoryRequest(self, val):
        '''
        Triggered by the EVE App when it requests history entries.
        Sets currentEntry and transfer flag, and safely prunes old history if needed.
        '''
        valHex = self.base64ToHex(val)
        valInt = int(valHex[4:12], base=16)
        address = self.swap32(valInt)
        self.currentEntry = address if address != 0 else 1
        self.transfer = True

    def setCurrentSetTime(self, val):
        x = bytearray(base64.b64decode(val))
        x.reverse()
        date_time = datetime.fromtimestamp(EPOCH_OFFSET + int(x.hex(),16))
        d = date_time.strftime("%d.%m.%Y, %H:%M:%S")