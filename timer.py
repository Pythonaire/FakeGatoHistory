#!/usr/bin/env python3
import logging, threading


class FakeGatoTimer():
    def __init__(self, minutes, accessoryName, *args, **kwargs):
        self.minutes = minutes
        self.subscribedServices = []
        self.running = False
        self.accessoryName = accessoryName

    def call_repeatedly(self, interval, func):
        stopped = threading.Event()
        def loop():
            while not stopped.wait(stopped.wait(interval)): # the first call is in `interval` secs
                #func(*args)
                func()
        threading.Thread(target=loop, daemon=True).start()    
        return stopped.set
        
    def subscribe(self, service, callback):
        #logging.info("** Fakegato-timer Subscription : {0}".format(service.accessoryName))
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

    def stop(self):
        logging.info("**Stop Global Fakegato-Timer****")
        self.cancel_future_calls()
        self.running = False
        

    def executeCallbacks(self):
        logging.info("**Fakegato-timer: executeCallbacks** {0} ** interval {1} minutes**".format(self.accessoryName, self.minutes))
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
            self.executeImmediateCallback(self.getSubscriber(service))
        else:
            self.getSubscriber(service)['backLog'].append(data)
            if self.running == False:
                logging.info("**Start Fakegato-Timer {0} with {1} minutes inverval**".format(self.accessoryName, self.minutes))
                self.running = True
                self.cancel_future_calls = self.call_repeatedly(self.minutes*60, self.executeCallbacks)

    def emptyData(self, service):
        #logging.info("**Fakegato-timer: emptyData ** {0} ".format(service.accessoryName))
        source = self.getSubscriber(service)
        if len(source['backLog']) != 0:
            source['previousBackLog'] = source['backLog']
            source['backLog'] = []