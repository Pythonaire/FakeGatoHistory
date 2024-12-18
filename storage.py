#!/usr/bin/env python3
import logging, time, socket, os, json

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

class FakeGatoStorage():
    def __init__(self, filename, *args, **kwargs):
        self.path = os.path.abspath(os.getcwd()) + "/"
        self.hostname = socket.gethostname().split('.')[0]
        self.filename = filename + '_persist.json'
        self.writers = []
        
    def addWriter(self, service):
        logging.info("** Fakegato-storage AddWriter : {0}".format(service.accessoryName))
        newWriter = {'service': service, 'filename': self.path + self.hostname + '_' + self.filename}
		#Unique filename per homebridge server.  Allows test environments on other servers not to break prod.
        new = False
        self.writers.append(newWriter)
        try:
            with open(newWriter['filename'], 'r') as fs:
                if os.path.getsize(newWriter['filename']) != 0:
                    logging.info("Found History in Persistant Storage")
                    fs.close()
                    new = False
                    #self.load(newWriter['service'])
        except IOError:
            fs = open(newWriter['filename'], 'w')
            logging.info("Create a empty File : {0}".format(newWriter['filename']))
            fs.close()
            new = True
        return new
    
    def getWriter(self, service):
        for i in self.writers:
            if i['service'] == service:
                return i
            break

    def write(self, params):
        self.writing = True
        writer = self.getWriter(params['service'])
        while self.writing == True:
            try:
                #logging.info('** Fakegato-storage write FS file: {0}'.format(writer['filename']))
                '''
                older values, that not send are stored in the  "history" key, so the only need the last dict -> write with truncate = w
                '''
                with open(writer['filename'], 'w') as fs: #open with overwrite
                    data = json.dumps(params['data'])
                    fs.writelines(data)
                self.writing = False
                fs.close()
            except Exception as e:
                logging.info("** Could not write Fakegato-storage {0}".format(e))
                self.writing = False
                time.sleep(0.1)
            
    def read(self, service):
        writer = self.getWriter(service)
        logging.info("** Fakegato-storage read: {}".format(writer['filename']))
        try:
            with open(writer['filename'], 'r') as fs:
                listofLines = fs.readlines()
                data = json.loads(listofLines[0].rstrip('\n'))
            fs.close()
        except Exception as err:
            logging.info("**Cannot fetching persisting data restart from zero : {0}".format(err))
            data = []
        return data

    def remove(self, service):
        writer = self.getWriter(service)
        try:
            with open(writer['filename'], 'w') as fs:
                fs.truncate(0) # resize to 0
                fs.close()
            logging.info("** Fakegato-storage clean up persist file: {0}".format(writer['filename']))
        except Exception as err:
            logging.info("**ERROR cleaning '{0}' - {1}".format(writer['filename'], err))