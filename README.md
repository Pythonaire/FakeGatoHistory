# FakeGatoHistory

Python transcoded, to work with HAP-Python accessory classes.

Based on the fabulous work of <https://github.com/simont77/fakegato-history>. In contrast to the original javascript, this translated version does not use persistance storage of long history data. See  <https://github.com/simont77/fakegato-history> for limitation and examples.
It is tested so fare with 'room', 'weather' and 'energy'.

I use this in combination HAP-Python <https://github.com/ikalchev/HAP-python>, a Python-based bridge. If you are using special, none HAP-default services and characteristics you need to define these under "/usr/local/lib/python3.x/dist-packages/pyhap/ressources". Additional, in these files you have to declare the history service and characteristics (see history.py) to work with.

Then, you can add:

```#!/usr/bin/env python3
self.History = FakeGatoHistory('room', self)
```

update values like:

```#!/usr/bin/env python3
@Accessory.run_at_interval(3000)
    def run(self):
    ....
self.History.addEntry({'time':round(time.time()),'temp': XXX,'humidity': XXX)})
```

To understand the example:

In this example, a sensor unit (eg. PlantSensor) send fresh data each 30 minutes to a 433 Mhz bridge unit. The bridge store these data in a dictionary. The "GardenValue" class call each 5 minutes for fresh data via getCache() in the NODE_CACHE dictionary.
This a working example. Have fun to test and make it better.
