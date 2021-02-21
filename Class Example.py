#!/usr/bin/env python3
from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR
import logging, requests, json, socket, time
from history import FakeGatoHistory

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

NODE_CACHE = {}

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
        self.set_info_service(firmware_revision='0.0.1', model='Gardener01', manufacturer= 'Pythonaire', serial_number="Soil-001")
        PlantSensor = self.add_preload_service('PlantSensor', chars=['Name', 'SoilMoisture', 'CurrentTemperature', 'CurrentRelativeHumidity'])
        Battery = self.add_preload_service("BatteryService", chars=['ChargingState','StatusLowBattery', 'BatteryLevel'])
        PlantSensor.configure_char('Name', value= 'SoilMoisture')
        self.SoilMoisture = PlantSensor.configure_char('SoilMoisture', value= 0) #initial
        self.AirTemperature = PlantSensor.configure_char('CurrentTemperature', value= 0) #initial
        self.AirHumidity = PlantSensor.configure_char('CurrentRelativeHumidity', value = 0) # initial
        self.BattLevel = Battery.configure_char('BatteryLevel', value = 0)
        self.BattStatus = Battery.configure_char('StatusLowBattery', value = 1)
        Battery.configure_char('ChargingState', value = 2)

        self.url_chached = 'http://rfmgate.home:8001/cached'
        self.History = FakeGatoHistory('room', self)
        

    @Accessory.run_at_interval(3000)
    def run(self):
        recv = getCache(self.url_chached, str(self.node))
        logging.info('NodeData :{0}'.format(recv))
        NodeData = (lambda: {"Charge": 0, "Soil":0, "Hum": 0, "Temp": 0}, lambda: recv[str(self.node)])[recv[str(self.node)] != "None"]()
        BattStatus = (lambda: 0, lambda: 1)[NodeData["Charge"]<=0]()
        self.BattStatus.set_value(BattStatus)
        self.SoilMoisture.set_value(NodeData["Soil"])
        self.AirHumidity.set_value(NodeData["Hum"])
        self.AirTemperature.set_value(NodeData["Temp"])
        self.BattLevel.set_value(NodeData["Charge"])
        self.History.addEntry({'time':round(time.time()),'temp':NodeData["Temp"],'humidity': NodeData["Hum"], 'ppm': 0})
        
    def stop(self):
        logging.info('Stopping accessory.')
