#!/usr/bin/env python3
import logging, time, socket, os, asyncio, json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")
hostname = socket.gethostname().split('.')[0]
selfStorage = None

class FakeGatoStorage():
    def __init__(self, params, *args, **kwargs):
        if params is None:
            params = {}
        self.writers = []
        self.selfStorage = selfStorage
        self.addingWriter = False
        
    def addWriter(self, service, params):
        if self.addingWriter == False: 
            if not params:
                params = {}
            logging.info("** Fakegato-storage AddWriter : {0}".format(service.accessoryName))
            newWriter = {
				'service': service,
				'storage': (lambda: 'fs', lambda: params['storage'])['storage' in params](),
                'fileName': params['fileName'],
                'path':params['path']
				#Unique filename per homebridge server.  Allows test environments on other servers not to break prod.
			}
            if newWriter['storage'] == 'fs':
                newWriter['storageHandler'] = 'fs'
                newWriter['path'] = (lambda: str(Path.home()), lambda: params['path'])['path' in params]()
                self.writers.append(newWriter)
                try:
                    fs = open(os.path.join(newWriter['path'], newWriter['fileName']), 'r')
                    if os.path.getsize(fs) != 0:
                        logging.info("History Loaded from Persistant Storage")
                        self.load(service)
                    fs.close()
                except Exception:
                    fs = open(os.path.join(newWriter['path'], newWriter['fileName']), 'a')
                    logging.info("Create a empty File : {0}".format(os.path.join(newWriter['path'], newWriter['fileName'])))
                    fs.close()
                self.addingWriter = True
        self.addingWriter = False
        return True # set history self.loaded

    def getWriter(self, service):
        for value in self.writers:
            if value == service:
                return value
            break
    def _getWriterIndex(self, service):
        return self.writers.index(service)

    def getWriters(self):
        return self.writers

    def delWriter(self, service):
        index = self._getWriterIndex(service)
        del self.writers[index: index+1]

    def write(self, params):
        self.writing = True
        writer = params['service'] 
        #logging.info("data:{0}".format(params['data']))
        while self.writing == True:
            try:
                logging.info('** Fakegato-storage write FS file: {0}'.format(os.path.join(writer.path, writer.fileName)))
                with open(os.path.join(writer.path, writer.fileName), 'a') as fs:
                    json.dump(params['data'], fs)
                self.writing = False
                fs.close()
            except Exception as e:
                logging.info("** Could not write Fakegato-storage {0}".format(e))
                self.writing = False
                time.sleep(0.1)
            
    def load(self, service):
        logging.info("Loading....")
        data = self.read({'service': service})
        if data !='':
            try:
                #logging.info("read data from {0} : {1}".format(service.accessoryName, data))
                jsonFile = json.loads(data)
                service.firstEntry = jsonFile['firstEntry']
                service.lastEntry = jsonFile['lastEntry']
                service.usedMemory = jsonFile['usedMemory']
                service.refTime = jsonFile['refTime']
                service.initialTime = jsonFile['initialTime']
                service.history = jsonFile['history']
                service.extra = jsonFile['extra']
            except Exception as e:
                logging.info("**ERROR fetching persisting data  - invalid JSON ** {0}".format(e))
        else:
            logging.info("** Start from the scratch ** ")

    
    def read(self,params):
        writer = params['service']
        data = None
        if writer.storage == 'fs':
            logging.info("** Fakegato-storage read FS file: {0}".format(os.path.join(writer.path, writer.fileName)))
            try:
                with open(os.path.join(writer.path, writer.fileName), 'r') as fs:
                    data = json.load(fs)
                fs.close()
            except Exception as err:
                logging.info("** Fakegato-storage file could not be readed: {0}".format(err))
        return data

    def remove(self,params):
        writer = params['service']
        if writer.storage == 'fs':
            logging.info("** Fakegato-storage delete FS file: {0}".format(os.path.join(writer.path, writer.fileName)))
            os.remove(os.path.join(writer.path, writer.fileName))