# FakeGatoHistory

Based on the fabulous work of <https://github.com/simont77/fakegato-history> to work with HAP-Python <https://github.com/ikalchev/HAP-python>.

## Differences so fare

The original fakegato-history contains 'storage.py' for holding long time history data in a separate file in case of missing homekit connection. If you don't updating history data over long time in the ios app and restarting the service 'storage.py' push the missing values, selected by the timestamp. 

By default, 'history.py' holds 4032 values in memory, before overwriting. You can increase the value count in the script. Eve history function needs values each 10 minutes and display the history data over 14 days. So 4032 x 10 minutes should be enough.
'storage.py' is transcoded so fare, but not tested.


## Tested

It is tested and works well for Room, Energy and Weather data. 


## How To

HAP-Python holds the default HAP services and characteristics in two files 'services.json' and 'characteristics.json'.
After installing HAP-Python, these files are under "/usr/local/lib/python3.x/dist-packages/pyhap/ressources". If you want to use Eve services and characteristics, you have to add these services and characteristics.

services.json:

````
"History": {
    "OptionalCharacteristics": [
     "Name"
    ],
   "RequiredCharacteristics": [
   "S2R1",
   "S2R2",
   "S2W1",
   "S2W2"
   ],
   "UUID": "E863F007-079E-48FF-8F27-9C2605A29F52"
 }
 ````
characteristics.json

````
"S2R1": {
      "Format" :"data",
      "Permissions": [
         "pr",
	 "pw",
         "ev",
         "hd"
      ],
      "UUID": "E863F116-079E-48FF-8F27-9C2605A29F52"
   },
   "S2R2": {
      "Format" :"data",
      "Permissions": [
         "pr",
         "pw",
         "ev",
         "hd"
      ],
      "UUID": "E863F117-079E-48FF-8F27-9C2605A29F52"
   },
   "S2W1": {
      "Format" :"data",
      "Permissions": [
	"pw",
        "hd"
      ],
      "UUID": "E863F11C-079E-48FF-8F27-9C2605A29F52"
   },
   "S2W2": {
      "Format" :"data",
      "Permissions": [
	"pw",
        "hd"
      ],
      "UUID": "E863F121-079E-48FF-8F27-9C2605A29F52"
   }
   ````


service and characteristics example Weather data based on a BME280 sensor:

Eve use the standard humidity and temperature services and characteristics. You just need to add:

services.json:

````
"AtmosphericPressureSensor": {
    "OptionalCharacteristics": [
     "Name"
    ],
   "RequiredCharacteristics": [
   "AtmosphericPressure"
   ],
   "UUID": "E863F00A-079E-48FF-8F27-9C2605A29F52"
   }
````

characteristics.json:

````
"AtmosphericPressure": {
      "Format": "float",
      "Permissions": [
         "pr",
         "ev"
      ],
      "UUID": "E863F10F-079E-48FF-8F27-9C2605A29F52",
      "unit": "hPa",
      "maxValue": 1200.0,
      "minValue": 700.0,
      "minStep": 0.1
   }

````

Then, import the history library to your script:

```#!/usr/bin/env python3
from history import FakeGatoHistory
```

Link the history to your device class:

```#!/usr/bin/env python3
def __init__(self, node, *args, **kwargs): # Sensor
        super().__init__(*args, **kwargs)
        ....
        self.History = FakeGatoHistory('weather', self)

```

Push the data:

```#!/usr/bin/env python3

@Accessory.run_at_interval(300)
    def run(self):
    ....
    self.History.addEntry({'time':int(round(time.time())),'temp':XXX,'humidity': XXX, 'pressure':XXX})
```

See 'Class Example.py' for more information. 

Have fun.
