# FakeGatoHistory

Based on the fabulous work of <https://github.com/simont77/fakegato-history> to work with HAP-Python <https://github.com/ikalchev/HAP-python>.

## Differences to the javascript implementation

The original fakegato-history have a variable mem cache for data records. I set that fixed to 4032 and interval of 10 minutes, before the counter is reset to 0. That gives 4032/6 = 672 hours values in the memory.
To pretend meantime system failure and losing data "store data" can be set by additional 'True'.
A file "YourHostBName_YourAccessory" will be created and data will be stored where before uploading.

```
self.History = FakeGatoHistory('xxxx', self, True)
```
To restart from the cratch, delete this file.

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
