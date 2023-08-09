# potentiometer.py

import serial
import time

# make sure the 'COM#' is set according the Windows Device Manager
ser = serial.Serial('COM4', 9600, timeout=1)

time.sleep(2)

# for i in range(50):
line = ser.readline().strip()   # read a byte
temp = float(line[-5:])

print(temp)
# if line:
#     print(line)
#     string = line.decode()  # convert the byte string to a unicode string
#     num = string # convert the unicode string to an int
#     print(num)
#
# ser.close()