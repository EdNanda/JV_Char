# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 11:33:24 2022

@author: HYDN02
"""
#from pvlib import ivtools
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

volt=[-0.2,-0.19,-0.18,-0.17,-0.16,-0.15,-0.14,-0.13,-0.12,-0.11,-0.1,-0.09,-0.08,-0.07,-0.06,-0.05,-0.04,-0.03,-0.02,-0.01,1.67E-16,0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,0.11,0.12,0.13,0.14,0.15,0.16,0.17,0.18,0.19,0.2,0.21,0.22,0.23,0.24,0.25,0.26,0.27,0.28,0.29,0.3,0.31,0.32,0.33,0.34,0.35,0.36,0.37,0.38,0.39,0.4,0.41,0.42,0.43,0.44,0.45,0.46,0.47,0.48,0.49,0.5,0.51,0.52,0.53,0.54,0.55,0.56,0.57,0.58,0.59,0.6,0.61,0.62,0.63,0.64,0.65,0.66,0.67,0.68,0.69,0.7,0.71,0.72,0.73,0.74,0.75,0.76,0.77,0.78,0.79,0.8,0.81,0.82,0.83,0.84,0.85,0.86,0.87,0.88,0.89,0.9,0.91,0.92,0.93,0.94,0.95,0.96,0.97,0.98,0.99,1,1.01,1.02,1.03,1.04,1.05,1.06,1.07,1.08,1.09,1.1,1.11,1.12,1.13,1.14,1.15,1.16,1.17,1.18,1.19,1.2,1.21,1.22,1.23,1.24,1.25,1.26,1.27,1.28,1.29,1.3]
curr=[-21.76336667,-21.7354,-21.72799792,-21.72048125,-21.70777083,-21.71380208,-21.73012708,-21.73093333,-21.71742083,-21.73795417,-21.72926042,-21.72003125,-21.7143375,-21.6981875,-21.69547083,-21.69702708,-21.69263542,-21.667775,-21.66355208,-21.66190417,-21.64887292,-21.65191667,-21.638225,-21.65179167,-21.66255208,-21.6514875,-21.66066667,-21.66558542,-21.67531875,-21.66271667,-21.65648125,-21.63829167,-21.6294375,-21.62378125,-21.60522083,-21.59960625,-21.61400625,-21.59261458,-21.60268333,-21.59934792,-21.60364375,-21.57440417,-21.59987083,-21.60473542,-21.59938542,-21.60238125,-21.57241667,-21.56913333,-21.57078958,-21.58075417,-21.58691667,-21.58647708,-21.57779167,-21.56548333,-21.54385417,-21.54291875,-21.53978333,-21.52116667,-21.51892708,-21.51069583,-21.50742292,-21.50538125,-21.50002917,-21.49768542,-21.51544583,-21.49897917,-21.49332292,-21.48402917,-21.48246875,-21.48244167,-21.486325,-21.45820833,-21.46185625,-21.44527917,-21.41227708,-21.4054375,-21.40767708,-21.38975417,-21.38827083,-21.38083958,-21.372075,-21.36932083,-21.3652125,-21.34550625,-21.34032083,-21.35092708,-21.32584583,-21.28245833,-21.26858958,-21.24842292,-21.20201667,-21.16607292,-21.1360125,-21.08796042,-21.01982917,-20.92189167,-20.81840208,-20.71604792,-20.57995833,-20.42081667,-20.28249792,-20.1125,-19.90666667,-19.69643958,-19.42288333,-19.1512125,-18.81950208,-18.44634167,-18.02705208,-17.58073333,-17.109775,-16.5838875,-16.02225417,-15.42504792,-14.80925,-14.2147625,-13.66043958,-13.12522708,-12.53594583,-11.91398125,-11.24181458,-10.52080833,-9.802302083,-9.066104167,-8.320691667,-7.53165,-6.680520833,-5.800813333,-4.807275417,-3.768791875,-2.681886875,-1.5419125,-0.329306271,0.963232292,2.290984375,3.6675675,5.081539375,6.499922917,7.888654167,9.09455625,10.11882292,11.22550208,12.51144167,13.9102125,15.39070417,16.88689583,18.3883,20.10757917,23.18283333,26.80872083,29.01989792]

#
# volt = np.array(volt)
# curr = np.array(curr)
#
# isc = curr[np.argmin(abs(volt))]
#
# c0 = np.argmin(abs(volt))
#
# volt[c0] = 0
#
#
# c1 = sorted(abs(curr))[0]
# c2 = sorted(abs(curr))[1]
# i1 = np.where(abs(curr)==c1)[0][0]
# i2 = np.where(abs(curr)==c2)[0][0]
#
# v1 = volt[i1]
# v2 = volt[i2]
# m = (c2-c1)/(v2-v1)
# b = c1-m*v1
# voc = -b/m
# # voc =
#
# volt[max(i1,i2)] = voc
# curr[max(i1,i2)] = 0
#
# s_curr = curr[c0:max(i1,i2)+1]
# s_volt = volt[c0:max(i1,i2)+1]
#
# mpp = np.argmax(-volt*curr)
#
# mpp_v = volt[mpp]
# mpp_c = curr[mpp]
#
# ff = mpp_v*mpp_c/(voc*isc)
# pin = 10#W/m²
# pce = voc*isc*ff/pin
#
# print(voc, mpp_v,ff,pce)
#
#
# # print(v1,voc,v2)
#
# # ivtools.sde.fit_sandia_simple(s_volt,s_curr, vlim=0.2, ilim=0.1)

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



# Linear Regression, scikit
#v_train, v_test, c_train, c_test = train_test_split(volt.reshape(-1, 1), curr.reshape(-1, 1), test_size=0.5, random_state=1)
reg_par = LinearRegression()
reg_ser = LinearRegression()
co=2
v_par = volt[v0-co : v0+co].reshape(-1, 1)
c_par = curr[v0-co : v0+co].reshape(-1, 1)
v_ser = volt[i1-1 : i2+1].reshape(-1, 1)
c_ser = curr[i1-1 : i2+1].reshape(-1, 1)

reg_par.fit(v_par, c_par)
reg_ser.fit(v_ser, c_ser)

# Calculate resistances, parallel and series
r_par = abs(1 / m_i)
r_ser = abs(1 / m_v)


print(reg_par.coef_[0][0])
print("resistencia")
print(r_par*1000,1/reg_par.coef_[0]*1000,r_ser*1000,1/reg_ser.coef_[0]*1000)

# Find mpp values
mpp = np.argmax(-volt * curr)

mpp_v = volt[mpp]
mpp_c = curr[mpp]
mpp_p = mpp_v * mpp_c

# Calculate FF
ff = mpp_v * mpp_c / (voc * isc) * 100

# Calculate PCE (this is wrong, it needs correct P_in)
# pin = 75#mW/cm²
pin = 100#float(self.pow_dens.text())  # mW/cm²
pce = abs(voc * isc * ff) / pin

jv_char = [voc, isc, ff, pce, mpp_v, mpp_c, mpp_p, r_ser, r_par]
print(jv_char)
# print(reg.coef_,reg.intercept_)

# for a in [volt,curr,v_train, v_test, c_train, c_test]:
#     print(len(a))
    #print(a)