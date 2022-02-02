#!/usr/bin/env python3
import logging, time, socket, os, json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")
hostname = socket.gethostname().split('.')[0]


class FakeGatoStorage():
    def __init__(self, path, filename, *args, **kwargs):
        self.path = path + "/"
        self.filename = filename
        self.writers = []
        
    def addWriter(self, service):
        logging.info("** Fakegato-storage AddWriter : {0}".format(service.accessoryName))
        newWriter = {'service': service, 'filename': self.path + hostname + '_' + self.filename}
		#Unique filename per homebridge server.  Allows test environments on other servers not to break prod.
        self.writers.append(newWriter)
        try:
            with open(newWriter['filename'], 'r') as fs:
                if os.path.getsize(newWriter['filename']) != 0:
                    logging.info("Found History in Persistant Storage")
                    fs.close()
                    #self.load(newWriter['service'])
        except IOError:
            fs = open(newWriter['filename'], 'w')
            logging.info("Create a empty File : {0}".format(newWriter['filename']))
            fs.close()
        return True # set history self.loaded

    def getWriter(self, service):
        for i in self.writers:
            if i['service'] == service:
                return i
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
        writer = self.getWriter(params['service'])
        while self.writing == True:
            try:
                logging.info('** Fakegato-storage write FS file: {0}'.format(writer['filename']))
                with open(writer['filename'], 'a') as fs:
                    data = json.dumps(params['data'])
                    fs.writelines(data)
                    #json.dump(params['data'], fs)
                self.writing = False
                fs.close()
            except Exception as e:
                logging.info("** Could not write Fakegato-storage {0}".format(e))
                self.writing = False
                time.sleep(0.1)
            
    def read(self, service):
        writer = self.getWriter(service)
        # return {'service': service, 'filename': self.path + hostname + '_' + self.filename}
        logging.info("** Fakegato-storage read FS file: {0}".format(writer['filename']))
        data = []
        try:
            with open(writer['filename'], 'r') as fs:
                list = fs.readlines()
                for i in list:
                    data.append(json.loads(i.rstrip('\n')))
            fs.close()
        except ValueError as err:
            logging.info("** Fakegato-storage file could not be readed: {0}".format(err))
        return data, err

    def remove(self,params):
        writer = self.getWriter(params['service'])
        if writer['storage'] == 'fs':
            logging.info("** Fakegato-storage clean persist file: {0}".format(writer['filename']))
            with open(writer['filename'], 'rw+') as fs:
                fs.truncate(0) # resize to 0
            fs.close()