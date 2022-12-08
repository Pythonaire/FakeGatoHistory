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
        exists = False
        self.writers.append(newWriter)
        try:
            with open(newWriter['filename'], 'r') as fs:
                if os.path.getsize(newWriter['filename']) != 0:
                    logging.info("Found History in Persistant Storage")
                    fs.close()
                    exists = True
                    #self.load(newWriter['service'])
        except IOError:
            fs = open(newWriter['filename'], 'w')
            logging.info("Create a empty File : {0}".format(newWriter['filename']))
            fs.close()
            exists = True
        return exists

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
                with open(writer['filename'], 'w') as fs: #open with truncate
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
        logging.info("** Fakegato-storage read: {}".format(writer['filename']))
        # return {'service': service, 'filename': self.path + hostname + '_' + self.filename}
        #logging.info("** Fakegato-storage read FS file: {0}".format(writer['filename']))
        try:
            with open(writer['filename'], 'r') as fs:
                list = fs.readlines()
                data = json.loads(list[0].rstrip('\n'))
                #for i in list:
                #    data.append(json.loads(i.rstrip('\n')))
            fs.close()
        except Exception as err:
            logging.info("**ERROR fetching persisting data restart from zero : {0}".format(err))
            data = ''
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