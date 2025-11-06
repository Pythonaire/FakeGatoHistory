

def format_weather_entry(format16, format32, entry, currEntry, time_hex, atype117, atype117bis):
    temp = format16(entry.get('temp', 0) * 100)
    humidity = format16(entry.get('humidity', 0) * 100)
    pressure = format16(entry.get('pressure', 0) * 10)
    return f",10 {currEntry}{time_hex}-{atype117}:{temp} {humidity} {pressure}"

def format_energy_entry(format16, format32, entry, currEntry, time_hex, atype117, atype117bis):
    power = format16(entry.get('power', 0) * 10)
    return f",14 {currEntry}{time_hex}-{atype117}:0000 0000 {power} 0000 0000"

def format_room_entry(format16, format32, entry, currEntry, time_hex, atype117, atype117bis):
    temp = format16(entry.get('temp', 0) * 100)
    humidity = format16(entry.get('humidity', 0) * 100)
    ppm = format16(entry.get('ppm', 0))
    return f",13 {currEntry}{time_hex}{atype117}{temp}{humidity}{ppm}0000 00"

def format_room2_entry(format16, format32, entry, currEntry, time_hex, atype117, atype117bis):
    temp = format16(entry.get('temp', 0) * 100)
    humidity = format16(entry.get('humidity', 0) * 100)
    voc = format16(entry.get('voc', 0))
    return f",15 {currEntry}{time_hex}{atype117}{temp}{humidity}{voc}0054 a80f01"

def format_door_motion_switch_entry(format16, format32, entry, currEntry, time_hex, atype117, atype117bis):
    status = format(entry.get('status', 0), '02X')
    return f",0b {currEntry}{time_hex}{atype117}{status}"

def format_aqua_entry(format16, format32, entry, currEntry, time_hex, atype117, atype117bis):
    status_val = entry.get('status', 0)
    status = format(int(bool(status_val)), '02X')
    if status_val is True:
        return f"+,0d {currEntry}{time_hex}{atype117}{status} 300c"
    else:
        waterAmount = format32(entry.get('waterAmount', 0))
        return f",15 {currEntry}{time_hex}{atype117bis}{status}{waterAmount} 00000000 300c"
    
def format_thermo_entry(format16, format32, entry, currEntry, time_hex, atype117, atype117bis):
    currtemp = format16(entry.get('currentTemp', 0) * 100)
    settemp = format16(entry.get('setTemp', 0) * 100)
    valvePos = format(entry.get('valvePosition', 0), '02X')
    return f",11 {currEntry}{time_hex}{atype117}{currtemp}{settemp}{valvePos} 0000"