#!/usr/bin/env python3
from re import X
from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_SENSOR
import logging, time
from history import FakeGatoHistory

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

class Weather(Accessory):
    category = CATEGORY_SENSOR
    def __init__(self, node, *args, **kwargs):
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

        self.History = FakeGatoHistory('weather', self)
        
    @Accessory.run_at_interval(600)
    def run(self):
        '''
        in this example a external function getnodeData() pull sensor data from a sensor node, defined by self.node.
        '''
        nodeBattery = getnodeData('Battery')
        nodeHumidity = getnodeData('Humidity')
        nodeTemperature = getnodeData('Temperature')
        nodePressure = getnodeData('Pressure')
        self.BattStatus.set_value(nodeBattery)
        self.AirHumidity.set_value(nodeHumidity)
        self.AirTemperature.set_value(nodeTemperature)
        self.AirPressure.set_value(nodePressure)
    
        self.History.addEntry({'time':int(round(time.time())),'temp':nodeTemperature,'humidity': nodeHumidity, 'pressure':nodePressure})
        
    def stop(self):
        logging.info('Stopping accessory.')
