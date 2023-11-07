# potentiometer.py

import serial
import time
import numpy as np
import serial.tools.list_ports

def list_com_ports():
    ports = serial.tools.list_ports.comports()
    port_dict = {}
    for port in ports:
        port_dict[port.description.split(' (')[0]] = port.name
        print(f"Port: {port.device}, Name: {port.name}, Description: {port.description}")
    return port_dict

if __name__ == '__main__':
    list_com_ports()

# make sure the 'COM#' is set according the Windows Device Manager
ser = serial.Serial('COM8', 9600, timeout=1)

time.sleep(2)

# for i in range(50):
line = ser.readline().strip()   # read a byte
temp = float(line[-5:])

print(temp)
print(np.nan)
# if line:
#     print(line)
#     string = line.decode()  # convert the byte string to a unicode string
#     num = string # convert the unicode string to an int
#     print(num)
#
# ser.close()