# FakeGatoHistory

Python transcoded, to work with HAP-Python accessory classes.

based on the fabulous work of <https://github.com/simont77/fakegato-history>.

- without external persistance data (like google drive etc.), just local storage.
- tested with 'room' an 'power' binded to a HAP-Python bridge

see  <https://github.com/simont77/fakegato-history> for limitation and examples.

in your accessory class add:

```#!/usr/bin/env python3
self.History = FakeGatoHistory('room', self)
```

update values like:

```#!/usr/bin/env python3
@Accessory.run_at_interval(3000)
    def run(self):
    ....
self.History.addEntry({'time':round(time.time()),'temp': XXX,'humidity': XXX,'ppm':XXX)})
```

To understand the example:

In this example, a sensor unit send fresh data each 30 minutes to a 433 Mhz bridge unit. The bridge store these data in a dictionary. The "GardenValue" class call each 5 minutes for fresh data via getCache() in the NODE_CACHE dictionary.
In this case, the "GardenValues" is a Eve Room accessory with:

- Temperature
- Air humidity
- Soil Humidiy

To bring up the Eve view, the soil values a recalculated to the range of an AirQuality Sensor. ("Excellent": 0-700, "Good": 700-1100, "Acceptable": 1100-1600, "Moderate": 1600-2000, "Bad": >2000)

The functions translate_aq and translate_eveaq needed to translate the soil humidity values (percentage) into readable AirQuality data. Eve AirQuality and standard Homekit AirQuality have different ranges.