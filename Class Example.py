#!/usr/bin/env python3
from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR
import logging, requests, json, socket, threading, time
from history import FakeGatoHistory

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")


file = open("config.json","r")
Devices = json.load(file)
file.close()
#{"GardenValues": 10, "Irrigation": 11}
NODE_CACHE = {}

for x, y in Devices.items(): # create Cache: {'10': None, '11': None}
    NODE_CACHE[str(y)] = None

def controlrfm(url, node, cmd):
    global NODE_CACHE
    httpsend = {node: cmd}
    NODE_CACHE[node] = "None" # set to None, wait for answer
    ret = {}
    try:
        ret = requests.get(url, json=json.dumps(httpsend)).json()
        #rfm return with {'node': "None"} if request failed
        if ret[node] == "None":
            ret[node] = 0 # set to 0
        NODE_CACHE[node] = ret[node]
        return ret
    except Exception as e:
        logging.info('**** request to  {0} timed out: {1}'.format(url, e))

def getCache(url, node):
    requ = {node:"?"} # "?" useless, but needed for dict/json handling
    ret = {}
    try:
        while not node in ret:
            ret = requests.get(url, json=json.dumps(requ)).json()
            if node in ret:
                NODE_CACHE[node] = ret[node]
                break
            else:
                time.sleep(1)
    except socket.error as e:
        logging.info('**** request to  {0} timed out: {1}'.format(url, e))
    return ret

    
class GardenValues(Accessory):
    category = CATEGORY_SENSOR
    def __init__(self, node, *args, **kwargs): # Garden sensor nodeNumber 10
        super().__init__(*args, **kwargs)
        self.name = args[1] # args[1] contained the Sensor Name given
        self.node = node # node number of the 433MHz sensor
        self.set_info_service(firmware_revision='0.0.1', model='Gardener01', manufacturer= 'Peter Wiechmann', serial_number="Soil-001")
        AirQualitySensor = self.add_preload_service("AirQualitySensor", chars=['AirQuality', 'EveAirQuality', 'EveCustom', 'Name'])
        TempSensor = self.add_preload_service("TemperatureSensor", chars=['CurrentTemperature', 'EveCustom'])
        HumSensor = self.add_preload_service("HumiditySensor", chars=['CurrentRelativeHumidity','EveCustom'])
        Battery = self.add_preload_service("BatteryService", chars=['ChargingState','StatusLowBattery', 'BatteryLevel', 'EveCustom'])

        self.soilaq =AirQualitySensor.configure_char('AirQuality', value= 0) # fake AirQuality, inital value
        self.soileve = AirQualitySensor.configure_char('EveAirQuality', value = 0) # fake EveAirQuality inital value
        AirQualitySensor.configure_char('EveCustom')
        AirQualitySensor.configure_char('Name', value="Bodenfeuchtigkeit")
    
        self.temp = TempSensor.configure_char('CurrentTemperature', value= 0) # initial value
        TempSensor.configure_char('EveCustom')
        self.hum = HumSensor.configure_char('CurrentRelativeHumidity', value =0) # inital value
        HumSensor.configure_char('EveCustom')


        self.battlevel = Battery.configure_char('BatteryLevel', value = 0)
        self.battstatus = Battery.configure_char('StatusLowBattery', value = 1)
        Battery.configure_char('ChargingState', value = 2)
        Battery.configure_char('EveCustom')

        #self.History = FakeGatoHistory('room', self,{'storage':'fs'})
        self.History = FakeGatoHistory('room', self)
        
    def translate_aq(self, data):
        #"Excellent": 1, "Good": 2, "Fair": 3, "Inferior": 4, "Poor": 5, "Unknown": 0
        if data<=10 and data != 0: ret = 5
        elif data<=20 and data>=10: ret = 4
        elif data<=40 and data>=20: ret = 3
        elif data<=60 and data>= 40: ret = 2
        elif data>=60: ret = 1
        else: ret = 0
        return ret
    
    def translate_eveaq(self, data):
        #"Excellent": 0-700, "Good": 700-1100, "Acceptable": 1100-1600, "Moderate": 1600-2000, "Bad": >2000
        eve_data = (-data*20)+2000
        return eve_data

    @Accessory.run_at_interval(3000)
    def run(self):
        recv = getCache(self.url_chached, str(self.node))
        logging.info('NodeData :{0}'.format(recv))
        if recv[str(self.node)] == "None":
            NodeData = {"Charge": 0, "Soil":0, "Hum": 0, "Temp": 0}
        else:
            NodeData = recv[str(self.node)]
            if NodeData["Charge"] <= 0: #  notify StatusLowBattery
                self.battstatus.set_value(1) # StatusLowBattery
            else:
                self.battstatus.set_value(0)
            self.soilaq.set_value(self.translate_aq(NodeData["Soil"]))
            self.soileve.set_value(self.translate_eveaq(NodeData["Soil"]))
            self.hum.set_value(NodeData["Hum"]) # AM2302 accuracy ?
            self.temp.set_value(NodeData["Temp"]) # AM2302 accuracy ?
            self.battlevel.set_value(NodeData["Charge"])
        self.History.addEntry({'time':round(time.time()),'temp':NodeData["Temp"],'humidity': NodeData["Hum"],'ppm':self.translate_eveaq(NodeData["Soil"])})

        
    def stop(self):
        logging.info('Stopping accessory.')
