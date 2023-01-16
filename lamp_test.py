# -*- coding: utf-8 -*-
"""
Created on Thu Jan  5 14:19:19 2023

@author: ffa
"""

import serial

ser = serial.Serial()  # open serial port
ser = serial.Serial("COM3")
ser.baudrate = 9600
ser.bytesize = 8
ser.parity = 'N'
ser.stopbits = 1
ser.timeout = 5
# print(ser.name)         # check which port was really used
# ser.write(b'C1') #Enable cooling
# ser.write(b'C0') #Disable cooling
# ser.write(b'S1') #Shutter Close
# ser.write(b'S0') #Shutter Open
# ser.write(b'L1') #Light On
ser.write(b'L0') #Light Off
# ser.write(b'P=0905') #Set light intensity
ser.write(b'FS') #Read data
# print(ser.readline())
print(ser.read_until(b"END\r\n"))
    
ser.close()             # close port

# with serial.Serial() as ser:
#     ser.baudrate = 9600
#     ser.port = 'COM1'
#     ser.open()
#     # ser.write(b'C1') #Enable cooling
#     ser.write(b'C0') #Disable cooling
#     # ser.write(b'S1') #Enable Shutter
#     #ser.write(b'S') #Disable Shutter
    
    
    
