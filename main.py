#!/usr/bin/env python3
import logging, signal, os, time
from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver
import Devices

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

persist_file = 'devices.state'

"""
The bridge mixed up normal devices reached by Wifi etc and RFM69 based devices connected through 433 MHz network.
Node numbers of RFM69 devices are stored in the config.py Class.
example:
NODES = {"Pumpe":11,"Weather":12}
The the dictionary key must refer to the device class, the value is the RFM69 node number to reach the 433MHz connected device.
While loading/importing Devices, classes and Nodes will be binded 
"""

def get_bridge(driver):
    bridge = Bridge(driver, 'MacServer')
    # mixed Devices
    for item in Devices.NODES:
        DeviceClass = getattr(Devices,item)
        NodeNumber = Devices.NODES[item]
        bridge.add_accessory(DeviceClass(NodeNumber, driver, item))
        logging.info('****** add RFM69 Accessory: {0}, Number: {1} *****'.format(item, NodeNumber))
    # directly connected devices
    PVA = Devices.PhotoVoltaic(driver, 'PhotoVoltaic')
    bridge.add_accessory(PVA)
    SOIL = Devices.Moisture(12, driver, 'Soil Moisture') # needed to be separated because of new eve app
    bridge.add_accessory(SOIL)
    return bridge

try:
    driver = AccessoryDriver(port=51826, persist_file= persist_file)
    driver.add_accessory(accessory=get_bridge(driver))
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()
except Exception as e:
    logging.info('**** Could connect HAP Service: {0}'.format(e))
    os.kill(os.getpid(), signal.SIGKILL)
    
