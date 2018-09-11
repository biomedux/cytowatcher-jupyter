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

#if sys.platform.startswith("win"):
dwf = cdll.dwf

#declare ctype variables
hdwf = c_int()
sts = c_byte()

#open device
print "Opening first device"
dwf.FDwfDeviceOpen(c_int(-1), byref(hdwf))

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

# enable output/mask on 8 LSB IO pins, from DIO 0 to 7
dwf.FDwfDigitalIOOutputEnableSet(hdwf, c_int(0x000F)) 
# set value on enabled IO pins
channel = 0x7
dwf.FDwfDigitalIOOutputSet(hdwf, c_int(0x08 | channel)) 
# fetch digital IO information from the device 

if hdwf.value == hdwfNone.value:
    szerr = create_string_buffer(512)
    dwf.FDwfGetLastErrorMsg(szerr)
    print szerr.value
    print "failed to open device"
    quit()

print "Generating sine wave..."
# enable just one channel
dwf.FDwfAnalogOutNodeEnableSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_int(True))

# configure enabled channels
dwf.FDwfAnalogOutNodeFunctionSet(hdwf, c_int(0), AnalogOutNodeCarrier, funcSine)
dwf.FDwfAnalogOutNodeAmplitudeSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(1)) #1V amplitude
dwf.FDwfAnalogOutNodeOffsetSet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(0))
time.sleep(1)

T=1024
nT = 2 #number of cycles in data buffer
BUFLEN = T*nT

dwf.FDwfAnalogInBufferSizeSet(hdwf, c_int(2*BUFLEN)) 
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(0), c_bool(True))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(0), c_double(1))
dwf.FDwfAnalogInChannelEnableSet(hdwf, c_int(1), c_bool(True))
dwf.FDwfAnalogInChannelRangeSet(hdwf, c_int(1), c_double(0.1))

#set up trigger
dwf.FDwfAnalogInTriggerAutoTimeoutSet(hdwf, c_double(0)) #disable auto trigger
dwf.FDwfAnalogInTriggerSourceSet(hdwf, trigsrcDetectorAnalogIn) #one of the analog in channels
dwf.FDwfAnalogInTriggerTypeSet(hdwf, trigtypeEdge)
dwf.FDwfAnalogInTriggerChannelSet(hdwf, c_int(0)) # first channel
dwf.FDwfAnalogInTriggerLevelSet(hdwf, c_double(0)) # 0V
dwf.FDwfAnalogInTriggerConditionSet(hdwf, trigcondRisingPositive) 

rg0Samples = (c_double*BUFLEN)() #for source channel
rg1Samples = (c_double*BUFLEN)() #destination channel

freq = 1000.
Freqs = []
while freq < 100000.*np.sqrt(2):
    Freqs.append(freq)
    freq = freq*np.sqrt(2)

aFreqs = []
gain = []
phase =[]
vbuflen = []
for F in Freqs:
    dwf.FDwfAnalogOutNodeFrequencySet(hdwf, c_int(0), AnalogOutNodeCarrier, c_double(F))
    af = c_double()
    dwf.FDwfAnalogOutNodeFrequencyGet(hdwf, c_int(0), AnalogOutNodeCarrier, byref(af))

    #sampling frequency calculation, set 2*period less than BUFLEN
    vlen = BUFLEN+1
    tT = T+1
    while vlen > BUFLEN:
        tT = tT-1
        sf = af.value*tT
        asf = c_double()
        dwf.FDwfAnalogInFrequencySet(hdwf, c_double(sf))
        dwf.FDwfAnalogInFrequencyGet(hdwf, byref(asf))
        vlen = int(2*asf.value/af.value)
    
    print "current Frequenct, current period", af.value, tT

    aFreqs.append(af.value) 
    vbuflen.append(vlen)
    
    # now enable function generator and wait stabilization
    dwf.FDwfAnalogOutConfigure(hdwf,c_int(0), c_bool(True))
    time.sleep(0.5)

    #begin acquisition
    dwf.FDwfAnalogInConfigure(hdwf, c_bool(False), c_bool(True))

    print "   waiting to finish"
    while True:
        dwf.FDwfAnalogInStatus(hdwf, c_int(1), byref(sts))
        print "STS VAL: " + str(sts.value) + "STS DONE: " + str(DwfStateDone.value)
        if sts.value == DwfStateDone.value :
            break
        time.sleep(0.1)
    print "Acquisition finished"

    dwf.FDwfAnalogInStatusData(hdwf, c_int(0), rg0Samples, BUFLEN)
    dwf.FDwfAnalogInStatusData(hdwf, c_int(1), rg1Samples, BUFLEN)

#
#sine matching  �̿�
    data0=list(rg0Samples[1:vlen])
    data1=list(rg1Samples[1:vlen])
    R0, T0, M0 = fs.sineFit2Cycle(data0,nT)
    R1, T1, M1 = fs.sineFit2Cycle(data1,nT)

    if R0 < 0:
        R0 = -R0
        T0 = T0-np.pi
    if R1 < 0:
        R1 = -R1
        T1 = T1-np.pi

    g = R1/R0 #저항은 g*1M/100
    p = T1-T0
    if p > np.pi:
        p -= np.pi*2
            
    gain.append(g)
    phase.append(p)
#locking
    #data0=list(rg0Samples[1:vlen])
    #data1=list(rg1Samples[1:vlen])
    #R0, T0, M0 = fs.sineFit2Cycle(data0,nT)
    #R1, T1, M1 = fs.sineFit2Cycle(data1,nT)
    #data1 = list(x-M1 for x in data1)
    ## here make the sine and cos function with R0, T0
    #N = len(data0)  # number of data points
    #t = np.linspace(0, 2*nT*np.pi, N)
    #data_fit0 = np.sin(t+T0)
    #rsum = 0
    #isum = 0
    #T=vlen/2
    #for i in range(1,T+1):
    #    rsum = rsum + data_fit0[i]*data1[i]
    #    isum = isum + data_fit0[i+T/4]*data1[i]
    #rsum = 2*rsum/T
    #isum = 2*isum/T
    #g= np.sqrt(rsum*rsum+isum*isum)
    #ang = 0 # find later
    #gain.append(g)
    #phase.append(ang)
    
# recreate the fitted curve using the optimized parameters
    #N = len(data0)  # number of data points
    #t = np.linspace(0, 2*nT*np.pi, N)
    #data_fit0 = R0*np.sin(t+T0) # + M0
    #data_fit1 = R1*np.sin(t+T1) # + M1
    #plt.figure()
    #plt.plot(data0, '.')
    #plt.plot([1*x for x in data1], '.')
    #plt.plot(data_fit0, label='s0 after fitting')
    #plt.plot([1*x for x in data_fit1], label='s1 after fitting')
    #plt.legend()
    #plt.show()

plt.plot(aFreqs,gain)
plt.show()

file = open("response.txt",'w')
file.write("Freq, Gain, Phase\n")
for i in range(len(aFreqs)):
   file.write("%d,%f,%f,%f\n" % (aFreqs[i], gain[i], phase[i],vbuflen[i] ) )

file.close()
dwf.FDwfDeviceCloseAll()
