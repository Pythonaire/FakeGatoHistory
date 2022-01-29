#!/usr/bin/env python3
from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR
import logging, requests, json, socket, time
from history import FakeGatoHistory

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

class Weather(Accessory):
    category = CATEGORY_SENSOR
    def __init__(self, node, *args, **kwargs): # Garden sensor nodeNumber 12
        super().__init__(*args, **kwargs)
        self.name = args[1] # args[1] contained the Sensor Name given
        self.node = node # node number of the 433MHz sensor
        self.set_info_service(firmware_revision='0.0.2', model='Gardener01', manufacturer= 'Pythonaire', serial_number="Weather-001")
        
        AirTemperature = self.add_preload_service('TemperatureSensor', chars=['Name', 'CurrentTemperature'])
        AirTemperature.configure_char('Name', value= 'Air Temperature')
        self.AirTemperature = AirTemperature.configure_char('CurrentTemperature', value= 0) #initial

        AirHumidity = self.add_preload_service('HumiditySensor', chars=['Name', 'CurrentRelativeHumidity'])
        AirHumidity.configure_char('Name', value= 'Air Humidity')
        self.AirHumidity = AirHumidity.configure_char('CurrentRelativeHumidity', value = 0) # initial

        AirPressure = self.add_preload_service('AtmosphericPressureSensor', chars=['Name', 'AtmosphericPressure'])
        AirPressure.configure_char('Name', value= 'Air Pressure')
        self.AirPressure = AirPressure.configure_char('AtmosphericPressure', value = 0) # initial

        Battery = self.add_preload_service("BatteryService", chars=['ChargingState','StatusLowBattery', 'BatteryLevel'])
        self.BattLevel = Battery.configure_char('BatteryLevel', value = 0)
        self.BattStatus = Battery.configure_char('StatusLowBattery', value = 1)
        Battery.configure_char('ChargingState', value = 2)

        self.HistoryTerrace = FakeGatoHistory('weather', self)
        
    @Accessory.run_at_interval(300)
    def run(self):
        '''
        in this example function getCache is used to pull sensor data from a sensor node, defined by self.node.
        The return is a dictionary 
        {'B':Battery,'AT':AirTemperature,'AH':AirHumidity,'AP':AirPressure}

        recv = getCache(str(self.node)) # pull sensor data
        logging.info('NodeData Weather :{0}'.format(recv[str(self.node)]))
        NodeData = {"B": 0, "AT":0, "AH": 0, "AP": 0} if recv[str(self.node)] == None else recv[str(self.node)]
        BattStatus = 1 if NodeData["B"]<=0 else 0
        '''
        self.BattStatus.set_value(BattStatus)
        self.AirHumidity.set_value(NodeData["AH"])
        self.AirTemperature.set_value(NodeData["AT"])
        self.AirPressure.set_value(NodeData["AP"])
        self.BattLevel.set_value(NodeData["B"])
        self.HistoryTerrace.addEntry({'time':int(round(time.time())),'temp':NodeData["AT"],'humidity': NodeData["AH"], 'pressure':NodeData["AP"]})
        
    
        
    def stop(self):
        logging.info('Stopping accessory.')