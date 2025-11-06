# FakeGatoHistory

Based on the fabulous work of <https://github.com/simont77/fakegato-history> to work with HAP-Python <https://github.com/ikalchev/HAP-python>. Minimum Python version is 3.10.

## some modifications ...

The original fakegato-history have a variable mem cache for data records. I set the mem cache fixed to 2048 and the interval of 10 minutes (to prevent memory holes). The Eve app, cut data older then 14 days. 14 days and 10 minutes interval needs around 2016 entries.
Additional, the original javascript implementation has the ability to cache data on harddisk to prevent data lost in case of system crash. These function is implemented too, but only on local space. If the rentention limit of 2016 entries is reached, them memory and files are made up.

Using public ip addresses (for example bridging IPv6) and the ISP change the network, the connection is lost, the service needs to be restarted. The "unvisible service" mDSNAdvizer update automatically the connection to the homekit gateway (here refresh/update the connection each hour continously).

## How To to use (example Weather data)

HAP-Python <https://github.com/ikalchev/HAP-python> holds the default Apple Homekit services and characteristics in two files 'services.json' and 'characteristics.json' under "/usr/local/lib/python3.x/dist-packages/pyhap/ressources". Apple change these definition in newer IOS versions. Additionally, maybe you like to define your own services. Because of that, i use my own service and characteristic definitions.

If you like to use your own definitions, add the following (see main.py):

```#!/usr/bin/env python3
from pyhap.loader import Loader as Loader
loader = Loader(path_char='CharacteristicDefinition.json',path_service='ServiceDefinition.json')
driver = AccessoryDriver(port=51826, persist_file= persist_file, loader=loader)

```

'CharacteristicDefinition.json'and 'ServiceDefinition.json' here, have the history service and characteristic descriptions.

Import the history library to your script:

```#!/usr/bin/env python3
from history import FakeGatoHistory
```

Link the history to your device class (here the example 'weather'):

```#!/usr/bin/env python3
self.History = FakeGatoHistory('weather', self)
```

If you like to store history data to prevent holes, in case of system crash,  you can add "True". That is the same functionality as the original fakegato-history offer. 

```#!/usr/bin/env python3
self.History = FakeGatoHistory('weather', self, True)
```

Push the data to the history by (here all 10 minutes)

```#!/usr/bin/env python3

@Accessory.run_at_interval(600)
    def run(self):
    ....
    self.History.addEntry({'time':int(round(time.time())),'temp':XXX,'humidity': XXX, 'pressure':XXX})
```

See 'Class Example.py' for more information. 

Have fun.
