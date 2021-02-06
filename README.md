# FakeGatoHistory
Python transcoded

based on the fabulous work of https://github.com/simont77/fakegato-history.

without external persistance data (like google drive etc.), just local storage.
Tested with 'room' an 'power' binded to a HAP-Python bridge.

see  https://github.com/simont77/fakegato-history for limitation and work examples.

example:

>self.History = FakeGatoHistory('room', self)

>@Accessory.run_at_interval(3000)<br>
>    def run(self):<br>
>    ....<br>
>    self.History.addEntry({'time':round(time.time()),'temp': XXX,'humidity': XXX,'ppm':XXX)})

