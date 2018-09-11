"""
Culture system test
2016-11-21
"""
from ctypes import *
from dwfconstants import *
import math
import time
import matplotlib.pyplot as plt
import sys

import fitSine as fs
import numpy as np

#Culture system parameter
Rref = 0.982e6 #Rref is a system parameter 0.982Mohm
Cs = 140e-12   #Cs is PCB stray cap. and a system parameter 140pF

if sys.platform.startswith("win32"):
	dwf = cdll.dwf
elif sys.platform.startswith("darwin"):
	dwf = cdll.LoadLibrary("libdwf.dylib")
else:
	dwf = cdll.LoadLibrary("libdwf.so")
	
#declare ctype variables
hdwf = c_int()
sts = c_byte()

#open device
print "Opening first device"
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

if hdwf.value == hdwfNone.value:
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print szerr.value
    print "failed to open device"
    quit()

# enable positive supply
dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(0), c_int(0), c_double(True))
# set voltage to 5 V
dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(0), c_int(1), c_double(5))
# enable negative supply
dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(1), c_int(0), c_double(True))
# set voltage to -5 V
dwf.FDwfAnalogIOChannelNodeSet(hdwf, c_int(1), c_int(1), c_double(-5))
# master enable
dwf.FDwfAnalogIOEnableSet(hdwf, c_int(True))



print "Generating sine wave..."
# enable just one channel
dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_int(True))

# configure enabled channels
dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcSine)
dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(1)) #1V amplitude
#dwf.FDwfAnalogOutNodeOffsetSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(0)) #LT1469 Amp
dwf.FDwfAnalogOutNodeOffsetSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(0))  #LM6172 Amp
time.sleep(1)

T=1024
nT = 2 #number of cycles in data buffer
BUFLEN = T * nT

dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(2 * BUFLEN))
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(0), c_bool(True))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(0.5))
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(1), c_bool(True))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(0.5))

#set up trigger
dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0)) #disable auto trigger
dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn) #one of the analog in channels
dwf.FDwfAnalogInTriggerTypeSet(hdwf, trigtypeEdge)
dwf.FDwfAnalogInTriggerChannelSet(hdwf, c_int(0)) # first channel
dwf.FDwfAnalogInTriggerLevelSet(hdwf, c_double(0)) # 0V
dwf.FDwfAnalogInTriggerConditionSet(hdwf, trigcondRisingPositive)

rg0Samples = (c_double * BUFLEN)() #for source channel
rg1Samples = (c_double * BUFLEN)() #destination channel

#Frequency set and get the actual frequency
freq = 4000. #4kHz impedance
dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(freq))
af = c_double()
dwf.FDwfAnalogOutNodeFrequencyGet(hdwf, c_int(0), AnalogOutNodeCarrier, byref(af))
#sampling frequency calculation, set 2*period less than BUFLEN
vlen = BUFLEN + 1
tT = T + 1
while vlen > BUFLEN:
    tT = tT - 1
    sf = af.value * tT
    asf = c_double()
    dwf.FDwfAnalogInFrequencySet(hdwf, c_double(sf))
    dwf.FDwfAnalogInFrequencyGet(hdwf, byref(asf))
    vlen = int(2 * asf.value / af.value)

print "current Frequenct, current period", af.value, tT
# now enable function generator and wait stabilization
dwf.FDwfAnalogOutConfigure(hdwf, c_int(0), c_bool(True))
time.sleep(0.5)

# enable output/mask on 8 LSB IO pins, from DIO 0 to 7
dwf.FDwfDigitalIOOutputEnableSet(hdwf, c_int(0x000F))

def measureImpedance(channels,freqs):
    nc = len(channels)
    nf = len(freqs)
    Z = [[0] * nf for _ in range(nc)]
    for ic in range(nc):
        ch = channels[ic]
        dwf.FDwfDigitalIOOutputSet(hdwf, c_int(0x08 | ch))
        time.sleep(0.1) #wait for the stable channel
        for ifr in range(nf):
            fr = freqs[ifr]
            #Frequency set and get the actual frequency
            dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(fr))
            # now enable function generator and wait stabilization
            dwf.FDwfAnalogOutConfigure(hdwf,c_int(0), c_bool(True))
            time.sleep(0.1)
            af = c_double()
            dwf.FDwfAnalogOutNodeFrequencyGet(hdwf, c_int(0), AnalogOutNodeCarrier, byref(af))
            #sampling frequency calculation, set 2*period less than BUFLEN

            vlen = BUFLEN + 1
            tT = T + 1
            while vlen > BUFLEN:
                tT = tT - 1
                sf = af.value * tT
                asf = c_double()
                dwf.FDwfAnalogInFrequencySet(hdwf, c_double(sf))
                dwf.FDwfAnalogInFrequencyGet(hdwf, byref(asf))
                vlen = int(2 * asf.value / af.value)
            #begin acquisition and wait for completion
            dwf.FDwfAnalogInConfigure(hdwf, c_bool(False), c_bool(True))
            sts = c_byte()
            while True:
                dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
                if sts.value == DwfStateDone.value :
                    break
                time.sleep(0.1)

            #get data
            dwf.FDwfAnalogInStatusData(hdwf, c_int(0), rg0Samples, BUFLEN)
            dwf.FDwfAnalogInStatusData(hdwf, c_int(1), rg1Samples, BUFLEN)

            #sine matching
            data0=list(rg0Samples[1:vlen])
            data1=list(rg1Samples[1:vlen])
            R0, T0, M0 = fs.sineFit2Cycle(data0, nT)
            R1, T1, M1 = fs.sineFit2Cycle(data1, nT)

            if R0 < 0:
                R0 = -R0
                T0 = T0 - np.pi
            if R1 < 0:
                R1 = -R1
                T1 = T1 - np.pi

            g = R1 / R0 / 100 # g*1M/100
            p = T1 - T0
            if p > np.pi:
                p -= np.pi * 2

            z = polar2RC(fr, g, p)
            Z[ic][ifr] = z
    return Z

def polar2RC(f,g,ang):
       w = 2 * np.pi * f     #freq. is input
       G = g * np.exp(1j * ang)
       Z = G / (1 - G) * Rref  #Rref is a system parameter 0.982Mohm
       Zc = 1 / (1 / Z - 1j * w * Cs)  #Cs is PCB stray cap. and a system parameter 140pF
       return Zc

def getScopeData(ch, fr):
     dwf.FDwfDigitalIOOutputSet(hdwf, c_int(0x08 | ch))
     time.sleep(0.1) #wait for the stable channel
     #Frequency set and get the actual frequency
     dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(fr))
     # now enable function generator and wait stabilization
     dwf.FDwfAnalogOutConfigure(hdwf,c_int(0), c_bool(True))
     time.sleep(0.1)
     af = c_double()
     dwf.FDwfAnalogOutNodeFrequencyGet(hdwf, c_int(0), AnalogOutNodeCarrier, byref(af))
     #sampling frequency calculation, set 2*period less than BUFLEN
     vlen = BUFLEN + 1
     tT = T + 1
     while vlen > BUFLEN:
          tT = tT - 1
          sf = af.value * tT
          asf = c_double()
          dwf.FDwfAnalogInFrequencySet(hdwf, c_double(sf))
          dwf.FDwfAnalogInFrequencyGet(hdwf, byref(asf))
          vlen = int(2 * asf.value / af.value)
     #begin acquisition and wait for completion
     dwf.FDwfAnalogInConfigure(hdwf, c_bool(False), c_bool(True))
     sts = c_byte()
     while True:
         dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
         if sts.value == DwfStateDone.value :
               break
         time.sleep(0.1)
     #get data
     dwf.FDwfAnalogInStatusData(hdwf, c_int(0), rg0Samples, BUFLEN)
     dwf.FDwfAnalogInStatusData(hdwf, c_int(1), rg1Samples, BUFLEN)

     data0 = list(rg0Samples[1:vlen])
     data1 = list(rg1Samples[1:vlen])
     return data0, data1
