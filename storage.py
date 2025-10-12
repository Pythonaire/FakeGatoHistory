import logging, time, socket, os, json, threading

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

class FakeGatoStorage():
    def getStorageFilePath(self, service):
        writer = self.getWriter(service)
        return writer['filename'] if writer is not None else None
    def __init__(self, filename, *args, **kwargs):
        self.path = os.path.abspath(os.getcwd()) + "/"
        self.hostname = socket.gethostname().split('.')[0]
        self.filename = filename + '_persist.json'
        self.writers = []
        self._write_lock = threading.Lock()
        
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
        # Not found, log a warning with accessoryName if possible
        try:
            service_name = getattr(service, "accessoryName", str(service))
        except Exception:
            service_name = str(service)
        logging.warning(f"getWriter: No writer found for service {service_name}")
        return None
        

    def write(self, params):
        self.writing = True
        writer = self.getWriter(params['service'])
        if writer is None:
            try:
                service_name = getattr(params['service'], "accessoryName", str(params['service']))
            except Exception:
                service_name = str(params['service'])
            logging.error(f"write: No writer found for service {service_name}, cannot write.")
            self.writing = False
            return
        while self.writing == True:
            with self._write_lock:
                try:
                    #logging.info('** Fakegato-storage write FS file: {0}'.format(writer['filename']))
                    '''
                    older values, that not send are stored in the  "history" key, so the only need the last dict -> write with truncate = w
                    '''
                    with open(writer['filename'], 'w') as fs: #open with overwrite
                        data = json.dumps(params['data'])
                        fs.writelines(data)
                    self.writing = False
                except Exception as e:
                    logging.info("** Could not write Fakegato-storage {0}".format(e))
                    self.writing = False
                    time.sleep(0.1)
            
    def read(self, service):
        writer = self.getWriter(service)
        if writer is None:
            try:
                service_name = getattr(service, "accessoryName", str(service))
            except Exception:
                service_name = str(service)
            logging.error(f"read: No writer found for service {service_name}, cannot read.")
            return []
        logging.info("** Fakegato-storage read: {}".format(writer['filename']))
        try:
            with open(writer['filename'], 'r') as fs:
                content = fs.read().strip()
                data = json.loads(content) if content else []
        except Exception as err:
            logging.info("**Cannot fetching persisting data restart from zero : {0}".format(err))
            data = []
        return data

    def remove(self, service):
        writer = self.getWriter(service)
        if writer is None:
            try:
                service_name = getattr(service, "accessoryName", str(service))
            except Exception:
                service_name = str(service)
            logging.error(f"remove: No writer found for service {service_name}, cannot remove.")
            return
        try:
            with open(writer['filename'], 'w') as fs:
                fs.truncate(0) # resize to 0
            logging.info("** Fakegato-storage clean up persist file: {0}".format(writer['filename']))
        except Exception as err:
            logging.info("**ERROR cleaning '{0}' - {1}".format(writer['filename'], err))