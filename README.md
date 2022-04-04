# FakeGatoHistory

Based on the fabulous work of <https://github.com/simont77/fakegato-history> to work with HAP-Python <https://github.com/ikalchev/HAP-python>.

## Differences to the javascript implementation

The original fakegato-history contains 'fakegato-storage.js' for holding long time history data in a separate file, in case of system crash and data not uploaded. 
By default, the script stores 4032 history records in memory, before overwriting. You can increase the value count in the script. Eve history function needs values each 10 minutes to prevent holes in the graph and display the history data over 14 days. So 4032 x 10 minutes should be enough.

## Modify interval and count of records

You can change the count of stored history records in the RAM by changing "self.memorySize = XXX" and the pull data to the homekit interval by "self.minutes = XX". 


## How To (example Weather data)

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

Push the data to the history by (here all 10 minutes)

```#!/usr/bin/env python3

@Accessory.run_at_interval(300)
    def run(self):
    ....
    self.History.addEntry({'time':int(round(time.time())),'temp':XXX,'humidity': XXX, 'pressure':XXX})
```

See 'Class Example.py' for more information. 

Have fun.
