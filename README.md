# FakeGatoHistory

Python transcoded, to work with HAP-Python accessory classes.

based on the fabulous work of <https://github.com/simont77/fakegato-history>.

- without external persistance data (like google drive etc.), just local storage.
- tested with 'room' an 'power' binded to a HAP-Python bridge

see  <https://github.com/simont77/fakegato-history> for limitation and examples.

in your accessory class add:

self.History = FakeGatoHistory('room', self)

update values like:

@Accessory.run_at_interval(3000)
    def run(self):
    ....
self.History.addEntry({'time':round(time.time()),'temp': XXX,'humidity': XXX,'ppm':XXX)})
