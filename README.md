# FakeGatoHistory

Based on the fabulous work of <https://github.com/simont77/fakegato-history> to work with HAP-Python <https://github.com/ikalchev/HAP-python>.

## Differences so fare

Store long history history data is not implemented so fare. 'storage.py' is the transcoded version, but not tested and binded to the core 'history.py'.
By default, 'history.py' hold 4032 values in the memory, before overwriting. Eve needs values each 10 minutes and display the history data over 14 days. So 4032 should be enough.

## Tested

It is tested and works well for Room, Energy and Weather data. 


## How To

HAP-Python holds the default HAP services and characteristics in two files 'services.json' and 'characteristics.json'.
After installing HAP-Python these files are under "/usr/local/lib/python3.x/dist-packages/pyhap/ressources". If you want to use Eve services and characteristics, you have to add these services and characteristics.

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


Have fun.
