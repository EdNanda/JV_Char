# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 11:33:24 2022

@author: HYDN02
"""
#from pvlib import ivtools
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

file = "C:\\Data\\cell A with bypass_before and after.xlsx"

def jv_chars_calculation(volt, curr):
    # Find Isc (find voltage value closest to 0 Volts)
    volt = np.array(volt)
    curr = np.array(curr)

    # if reverse measurement, flip it around
    if volt[0] > volt[-1]:
        volt = np.flip(volt)
        curr = np.flip(curr)

    v0 = np.argmin(abs(volt))  # Find voltage closest to zero

    # Fit datapoint around Jsc to get Shunt(parallel) resistance
    reg_par = LinearRegression()
    co = 6  # Change here to increase number of fitted points (co=1 -> 3 points)
    try:
        v_par = volt[v0 - co: v0 + co].reshape(-1, 1)
        c_par = curr[v0 - co: v0 + co].reshape(-1, 1)
    except:
        v_par = volt[v0: v0 + co].reshape(-1, 1)
        c_par = curr[v0: v0 + co].reshape(-1, 1)

    reg_par.fit(v_par, c_par)
    m_i = reg_par.coef_[0][0]

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
    r_par = abs(1 / m_i) * 1000  # 1000 factor to make it Ohms (since using mA)
    r_ser = abs(1 / m_v) * 1000

    # Find mpp values
    mpp = np.argmax(-volt * curr)

    mpp_v = volt[mpp]
    mpp_c = curr[mpp]
    mpp_p = mpp_v * mpp_c

    # Calculate FF
    ff = mpp_v * mpp_c / (voc * isc) * 100

    # Calculate PCE (this is wrong, it needs correct P_in)
    # pin = 75#mW/cm²
    #pin = float(self.pow_dens.text())  # mW/cm²
    pin = float(100)  # mW/cm²
    pce = abs(voc * isc * ff) / pin


    jv_char = [voc, isc, ff, pce, mpp_v, mpp_c, mpp_p, r_ser, r_par]

    return jv_char

def save_results(values, samples):
    names = ["Voc (V)", "Jsc (mA/cm2)", "FF (%)", "PCE (%)", "V_mpp (V)", "J_mpp (mA/cm2)", "P_mpp (mW/cm2)",
                 "R_series (Ohm cm2)", "R_shunt (Ohm cm2)"]

    results = pd.DataFrame(values, columns=names, index=samples)

    nf1 = file.rsplit("\\",1)[0]
    nf2 = file.rsplit("\\",1)[1]

    results_file = nf1 + "\\JVchars_" + nf2

    results.T.to_excel(results_file)


data = pd.read_excel(file,index_col=0,header=0)

results = []
samples = []
for key in data.keys():
    if key == "Voltage (V)":
        volt = data[key]
        continue

    else:
        curr = data[key]

    samples.append(key)

    values = jv_chars_calculation(volt,curr)
    results.append(values)

save_results(results, samples)

