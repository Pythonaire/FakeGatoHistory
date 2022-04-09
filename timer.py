#!/usr/bin/env python3
import logging, threading
def setInterval(interval):
        def decorator(function):
            def wrapper(*args, **kwargs):
                stopped = threading.Event()
                def loop(): # executed in another thread
                    while not stopped.wait(interval): # until stopped
                        function(*args, **kwargs)
                t = threading.Thread(target=loop)
                t.daemon = True # stop if the program exits
                t.start()
                return stopped
            return wrapper
        return decorator

class FakeGatoTimer():
    def __init__(self, minutes, accessoryName, *args, **kwargs):
        self.minutes = minutes
        self.subscribedServices = []
        self.running = False
        self.intervalID = None
        self.accessoryName = accessoryName
        
    def subscribe(self, service, callback):
        logging.info("** Fakegato-timer Subscription : {0}".format(service.accessoryName))
        newService = {
			'service': service,
			'callback': callback, # -> calculateAverage/select_types
			'backLog': [],
			'previousBackLog': [],
			'previousAvrg': {}
		}
        self.subscribedServices.append(newService)


    def getSubscriber(self, service):
        for i in self.subscribedServices:
            if i['service'] == service:
                break
        return i

    def _getSubscriberIndex(self, service):
        return self.subscribedServices.index(service)

    def getSubscribers(self):
        return self.subscribedServices

    def unsubscribe(self, service):
        index = self._getSubscriberIndex(service)
        self.subscribedServices.pop(index)
        if (len(self.subscribedServices) == 0 and self.running):
            self.stop()

    def start(self):
        logging.info("**Start Fakegato-Timer {0} for {1} min  **".format(self.accessoryName, self.minutes))
        if self.running == True: # = True
            self.stop()
        self.running = True
        self.intervalID = self.executeCallbacks() # start timer, the first call at the defined time

    def stop(self):
        logging.info("**Stop Global Fakegato-Timer****")
        self.intervalID.set() # stop the loop
        self.running = False
        self.intervalID = None

    @setInterval(600)
    def executeCallbacks(self):
        logging.info("**Fakegato-timer: executeCallbacks**")
        if len(self.subscribedServices) != 0:
            for service in self.subscribedServices:
                if callable(service["callback"]): # --> calculateAverage
                    service["previousAvrg"] = service["callback"](
                        {
                        'backLog': service['backLog'],
                        'previousAvrg': service['previousAvrg'],
                        'timer': self,
                        'immediate': False
                        }
                        )

    def executeImmediateCallback(self, service):
        logging.info("**Fakegato-timer: executeImmediateCallback**") 
        if callable(service['callback']) and len(service['backLog']) != 0:
            service['callback']({
				'backLog': service['backLog'],
				'timer': self,
				'immediate': True
			})
    
    def addData(self, params):
        data = params['entry']
        service = params['service']
        immediateCallback = params['immediateCallback'] if 'immediateCallback' in params else False
        if immediateCallback == True: # door or motion -> replace
            if len(self.getSubscriber(service)['backLog']) == 0:
                self.getSubscriber(service)['backLog'].append(data)
            else:
                self.getSubscriber(service)['backLog'][0] = data
        else:
            self.getSubscriber(service)['backLog'].append(data)
        if immediateCallback == True:
            self.executeImmediateCallback(self.getSubscriber(service))
        if self.running == False:
            self.start()

    def emptyData(self, service):
        logging.info("**Fakegato-timer: emptyData ** {0} ".format(service.accessoryName))
        source = self.getSubscriber(service)
        if len(source['backLog']) != 0:
            source['previousBackLog'] = source['backLog']
            source['backLog'] = []