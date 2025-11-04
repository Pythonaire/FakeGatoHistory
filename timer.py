import logging
import threading
import time

logging.basicConfig(level=logging.INFO, format="[%(module)s] %(message)s")

def call_repeatedly(interval, func, *args, **kwargs):
    stopped = threading.Event()
    lock = threading.Lock()  # Lock to protect shared state (stopped)
    def loop():
        while not stopped.wait(interval):
            with lock:  # Ensure that no other thread is modifying stopped
                func(*args, **kwargs)
    threading.Thread(target=loop, daemon=True).start()
    return stopped


class FakeGatoTimer():
    def __init__(self, minutes, accessoryName, *args, **kwargs):
        self.minutes = minutes
        self.subscribedServices = []
        self.running = False
        self.accessoryName = accessoryName
        self._backlog_lock = threading.Lock()
    
    def subscribe(self, service, callback):
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
                return i
        try:
            service_name = getattr(service, "accessoryName", str(service))
        except Exception:
            service_name = str(service)
        logging.warning(f"Subscriber for service {service_name} not found.")
        return None

    def stop(self):
        logging.info("**Stop Global Fakegato-Timer****")
        if hasattr(self, 'cancel_future_calls') and callable(self.cancel_future_calls):
            try:
                self.cancel_future_calls()
            except Exception as e:
                logging.warning(f"Error cancelling timer: {e}")
        self.running = False
        
    def executeCallbacks(self):
        if len(self.subscribedServices) != 0:
            for service in self.subscribedServices:
                try:
                    if callable(service.get("callback")):
                        service["previousAvrg"] = service["callback"](
                            {
                            'backLog': service['backLog'],
                            'previousAvrg': service['previousAvrg'],
                            'timer': self,
                            'immediate': False
                            }
                            )
                except Exception as e:
                    try:
                        service_name = getattr(service.get('service'), 'accessoryName', str(service))
                    except Exception:
                        service_name = str(service)
                    logging.warning(f"Callback error for subscriber {service_name}: {e}")

    def executeImmediateCallback(self, service):
        logging.info("**Fakegato-timer: executeImmediateCallback**")
        if service is None:
            logging.warning("executeImmediateCallback: service is None, skipping callback.")
            return
        if callable(service.get('callback')) and len(service.get('backLog', [])) != 0:
            service['callback']({
                'backLog': service['backLog'],
                'timer': self,
                'immediate': True
            })
        else:
            logging.warning("executeImmediateCallback: Callback not callable or backLog empty for service.")
    
    def addData(self, params):
        data = params['entry']
        service = params['service']
        immediateCallback = params['immediateCallback'] if 'immediateCallback' in params else False
        subscriber = self.getSubscriber(service)
        if subscriber is None:
            try:
                service_name = getattr(service, "accessoryName", str(service))
            except Exception:
                service_name = str(service)
            logging.warning(f"addData: No subscriber found for service {service_name}. Data not added.")
            return
        with self._backlog_lock:
            if immediateCallback: # door or motion -> replace
                if len(subscriber['backLog']) == 0:
                    subscriber['backLog'].append(data)
                else:
                    subscriber['backLog'][0] = data
                self.executeImmediateCallback(subscriber)
            else:
                subscriber['backLog'].append(data)
                if self.running == False:
                    logging.info("**Start Fakegato-Timer {0} with {1} minutes inverval**".format(self.accessoryName, self.minutes))
                    self.running = True
                    self.cancel_future_calls = call_repeatedly(self.minutes*60, self.executeCallbacks)

    def emptyData(self, service):
        #logging.info("**Fakegato-timer: emptyData ** {0} ".format(service.accessoryName))
        source = self.getSubscriber(service)
        if source is None:
            try:
                service_name = getattr(service, "accessoryName", str(service))
            except Exception:
                service_name = str(service)
            logging.warning(f"emptyData: No subscriber found for service {service_name}. Cannot empty data.")
            return
        with self._backlog_lock:
            if len(source['backLog']) != 0:
                source['previousBackLog'] = source['backLog']
                source['backLog'] = []