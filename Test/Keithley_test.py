# -*- coding: utf-8 -*-
"""
Created on Tue Jul  5 14:24:59 2022

@author: HYDN02
"""


from pymeasure.instruments.keithley import Keithley2450
import pyvisa as visa
import numpy as np
import time
import matplotlib.pyplot as plt

rm = visa.ResourceManager()
device = rm.list_resources()[0]


keithley = Keithley2450(device)


keithley.apply_voltage(compliance_current=0.3)
keithley.measure_current(nplc=1, current=0.135, auto_range=True)

# step       = 0.05
volt_begin = -1.0
volt_end   = 0.8
time_step  = 0.05


i_fwd = []
v_fwd = []
i_rev = []
v_rev = []

keithley.enable_source()

for i in np.arange(volt_begin, volt_end+time_step, time_step):
    # print(i)
    keithley.source_voltage = i
    # print(keithley.current)
    # time.sleep(1)
    i_fwd.append(keithley.current)
    v_fwd.append(i)
    


for i in np.arange(volt_end, volt_begin-time_step, -time_step):
    # print(i)
    keithley.source_voltage = i
    # print(keithley.current)
    # time.sleep(2)
    i_rev.append(keithley.current)
    v_rev.append(i)
    
keithley.disable_source()

plt.plot(v_fwd,i_fwd,"xb-")
plt.plot(v_rev,i_rev,".r-")
# plt.yscale("log")

plt.show()
