# FakeGatoHistory

Python transcoded, to work with HAP-Python accessory classes.

based on the fabulous work of <https://github.com/simont77/fakegato-history>.

- without external persistance data (like google drive etc.), just local storage({'storage':'fs'} - your local file)
- the persistance data feature is "under construction" - functions working, but strange behaviour on multiple clients
- tested with 'room', 'power' and 'weather' binded to a HAP-Python bridge

see  <https://github.com/simont77/fakegato-history> for limitation and examples.

You need to add service and characteristics into pyhap/ressources. (see history.py)

for a quick test, in your accessory class, add:

```#!/usr/bin/env python3
self.History = FakeGatoHistory('room', self)
```

update values like:

```#!/usr/bin/env python3
@Accessory.run_at_interval(3000)
    def run(self):
    ....
self.History.addEntry({'time':round(time.time()),'temp': XXX,'humidity': XXX, 'ppm': XXX)})
```

To understand the example:

In this example, a sensor unit (eg. PlantSensor 433 MHz) send fresh data each 30 minutes to a raspberry bridge. (see also <https://github.com/Pythonaire/HAP-Python-Packet-Bridge>) 

The bridge store these data in a dictionary (based on Flask). The HAP-Python class call each 5 minutes for fresh data via Python requests. The result is {"Charge": XX, "Soil"XX, "Hum": XX, "Temp": XX}.
This dictionary will be maped to the homekit.


This a working example. Have fun.
