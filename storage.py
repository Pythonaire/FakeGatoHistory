#!/usr/bin/env python3
import logging, time, socket, os, json, threading
#from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")
hostname = socket.gethostname().split('.')[0]


class FakeGatoStorage():
    def __init__(self, path, filename, *args, **kwargs):
        self.path = path + "/"
        self.filename = filename.replace(" ", "")
        self.writers = []
        
    def addWriter(self, service):
        logging.info("** Fakegato-storage AddWriter : {0}".format(service.accessoryName))
        newWriter = {'service': service, 'filename': self.path + hostname + '_' + self.filename}
		#Unique filename per homebridge server.  Allows test environments on other servers not to break prod.
        self.writers.append(newWriter)
        try:
            with open(newWriter['filename'], 'r') as fs:
                if os.path.getsize(newWriter['filename']) != 0:
                    fs.close()
        except IOError:
            fs = open(newWriter['filename'], 'w')
            logging.info("Create a empty File : {0}".format(newWriter['filename']))
            fs.close()
        return True

    def getWriter(self, service):
        for i in self.writers:
            if i['service'] == service:
                return i
            break

    def write(self, params):
        self.writing = False
        writer = self.getWriter(params['service'])
        while self.writing == False:
            try:
                with open(writer['filename'], 'w') as fs:
                    #fs.writelines(json.dumps(params['data']).join('\n'))
                    fs.writelines(json.dumps(params['data']))
                    #json.dump(params['data'], fs)
                self.writing = True
                fs.close()
                logging.info("** Written data to Fakegato-storage **")
            except Exception as e:
                logging.info("** Could not write Fakegato-storage {0}".format(e))
                self.writing = False
                
            
    def read(self, params):
        writer = self.getWriter(params['service'])
        # return {'service': service, 'filename': self.path + hostname + '_' + self.filename}
        logging.info("** Fakegato-storage read FS file: {0}".format(writer['filename']))
        data = []
        try:
            with open(writer['filename'], 'r') as fs:
                data = fs.readlines()
                if bool(data) == True:
                    data = json.loads(data[0])
            fs.close()
        except Exception as err:
            logging.info("** Could read the File - {0}".format(err))
        return data

    def remove(self, service):
        writer = self.getWriter(service)
        try:
            logging.info("** Fakegato-storage clean persist file: {0}".format(writer['filename']))
            with open(writer['filename'], 'w') as fs:
                fs.truncate(0) # resize to 0
                fs.close()
        except Exception as err:
            logging.info("**ERROR cleaning '{0}' - {1}".format(writer['filename'], err))