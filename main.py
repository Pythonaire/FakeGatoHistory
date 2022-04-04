#!/usr/bin/env python3
import logging, signal, os, time, sys
from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver
import ClassExample
from pyhap.loader import Loader as Loader

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

persist_file = 'devices.state'

loader = Loader(path_char='CharacteristicDefinition.json',path_service='ServiceDefinition.json')

def get_bridge(driver):
    bridge = Bridge(driver, 'HAPBridge')
    Weather = ClassExample.Weather(driver, 'Weather')
    bridge.add_accessory(Weather)
    return bridge

try:
    driver = AccessoryDriver(port=51826, persist_file= persist_file, loader=loader)
    driver.add_accessory(accessory=get_bridge(driver))
    signal.signal(signal.SIGTERM, driver.signal_handler)
    driver.start()
except Exception as e:
    logging.info('**** Could connect HAP Service: {0}'.format(e))
    os.kill(os.getpid(), signal.SIGKILL)
    
