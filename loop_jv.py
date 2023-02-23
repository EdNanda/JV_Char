import sys
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets, QtGui, QtTest
from pymeasure.instruments.keithley import Keithley2450
import pyvisa as visa
import pandas as pd
import numpy as np
import os
import serial
# from time import time, strftime, localtime
import time
from datetime import datetime

rm = visa.ResourceManager()  # Load piVisa
device = rm.list_resources()[0]  # Get the first keithley on the list
keithley = Keithley2450(device)

filename = "C:\\Data\\testabc_JV_characteristics.csv"


def jv_measurement(save_file):
    # setup keithley
    keithley_startup_setup()
    keithley.enable_source()

    # start measurement
    jvchar, jvdata = fix_data_and_send_to_measure()

    # Save data
    jv_char = fix_jv_chars_for_save(jvchar)
    save_data(jv_char, jvdata, save_file)

    # Disable keithley
    keithley.disable_source()


def keithley_startup_setup():
    curr_limit = 300
    keithley.apply_voltage(compliance_current=curr_limit / 1000)
    keithley.measure_current(nplc=1, current=0.5, auto_range=True)


def fix_data_and_send_to_measure():
    # reset_plot_jv()

    # area = float(sam_area.text())
    volt_begin = -0.1
    volt_end = 0.6
    volt_step = 0.05
    ave_pts = 1
    set_time = 0.1

    process = ["b", "f", "f"]

    forwa_vars = [volt_begin, volt_end + volt_step * 0.95, volt_step]
    rever_vars = [volt_end, volt_begin - volt_step * 0.95, -volt_step]
    fixed_vars = [set_time, ave_pts]

    jv_chars_results = pd.DataFrame()
    curr_volt_results = pd.DataFrame()

    # TODO with multiplexing, there will be another loop here that goes through the cells
    for n, cbb in enumerate(process):
        print("Curve #",str(n))

        if "f" in cbb:  # if it is forward
            direc = "Forward"
            all_vars = forwa_vars + fixed_vars + [direc, n]
        else:
            direc = "Reverse"
            all_vars = rever_vars + fixed_vars + [direc, n]

        # print(all_vars)
        volt, curr = curr_volt_measurement(all_vars)
        chars = jv_chars_calculation(volt, curr)

        jv_chars_results[direc + "_" + str(n)] = chars
        curr_volt_results["Voltage (V)_" + direc + "_" + str(n)] = volt
        curr_volt_results["Current Density(mA/cm²)_" + direc + "_" + str(n)] = curr
        # print(jv_chars_results)
        # print(curr_volt_results)

    return jv_chars_results, curr_volt_results


def curr_volt_measurement(variables):
    volt_0, volt_f, step, time_s, average_points, mode, n = variables

    current = []
    voltage = []

    for i in np.arange(volt_0, volt_f, step):
        meas_currents = []
        meas_voltages = []

        for t in range(int(average_points)):
            keithley.source_voltage = i
            time.sleep(time_s)
            # QtTest.QTest.qWait(int(time * 1000))
            meas_voltages.append(i)
            meas_currents.append(keithley.current * 1000)

        ave_curr = np.mean(meas_currents)
        # self.display_live_current(ave_curr)
        # self.display_live_voltage(i)
        current.append(ave_curr)
        voltage.append(np.mean(meas_voltages))

    plt.plot(voltage, current, label="Curve "+str(n))
    plt.legend()
    plt.show()

        # self.plot_jv(voltage, current, mode)

    # jv_chars = self.jv_chars_calculation(voltage, current)
    # self.display_live_current(ave_curr, False)
    # self.display_live_voltage(0, False)

    return voltage, current


def jv_chars_calculation(volt, curr):
    # find Isc (find voltage value closest to 0 Volts)
    volt = np.array(volt)
    curr = np.array(curr)

    # if reverse measurement, flip it around
    if volt[0] > volt[-1]:
        volt = np.flip(volt)
        curr = np.flip(curr)

    v0 = np.argmin(abs(volt))  # Find voltage closest to zero
    m_i = (curr[v0] - curr[v0 - 1]) / (volt[v0] - volt[v0 - 1])  # Slope at Jsc

    if volt[v0] <= 0.0001:  # If voltage is equal to zero
        isc = curr[v0]
    else:  # Otherwise calculate from slope
        b_i = -curr[v0] - m_i * volt[v0]
        isc = -b_i

    # For Voc, find closest current values to 0
    i1 = np.where(curr < 0, curr, -np.inf).argmax()
    i2 = np.where(curr > 0, curr, np.inf).argmin()

    c1 = curr[i1]
    c2 = curr[i2]

    # Get Voc by finding x-intercept (y=mx+b)
    v1 = volt[i1]
    v2 = volt[i2]
    m_v = (c2 - c1) / (v2 - v1)
    b_v = c1 - m_v * v1
    voc = -b_v / m_v

    # Calculate resistances, parallel and series
    r_par = abs(1 / m_i)
    r_ser = abs(1 / m_v)

    # Find mpp values
    mpp = np.argmax(-volt * curr)

    mpp_v = volt[mpp]
    mpp_c = curr[mpp]
    mpp_p = mpp_v * mpp_c

    # Calculate FF
    ff = mpp_v * mpp_c / (voc * isc) * 100

    # Calculate PCE (this is wrong, it needs correct P_in)
    # pin = 75#mW/cm²
    # pin = float(self.pow_dens.text())  # mW/cm²
    pce = abs(voc * isc * ff) / 100

    jv_char = [voc, isc, ff, pce, mpp_v, mpp_c, mpp_p, r_ser, r_par]

    return jv_char


def fix_jv_chars_for_save(chars):
    names = ["Voc (V)", "Jsc (mA/cm²)", "FF (%)", "PCE (%)", "V_mpp (V)", "J_mpp (mA/cm²)", "P_mpp (mW/cm²)",
             "R_series (\U00002126cm²)", "R_shunt (\U00002126cm²)"]
    names_f = [na.replace(" ", "") for na in names]

    jv_chars_results = chars.T.copy()
    jv_chars_results.columns = names_f

    return jv_chars_results


def save_data(char, data, filename):
    # filename = "C:\\Data\\testabc_JV_characteristics.csv"

    empty = pd.DataFrame(data={"": ["--"]})

    char.T.to_csv(filename, index=True, header=True)
    empty.to_csv(filename, mode="a", index=False, header=False)
    data.to_csv(filename, mode="a", index=False, header=True)


jv_measurement(filename)