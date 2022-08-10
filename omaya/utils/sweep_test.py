#from labjack_t7.labjackt7 import LabJackT7
import time
import pandas as pd
import numpy
#from fluke import Fluke
import datetime
from omaya.prologix.prologix_all import Prologix
import matplotlib.pyplot as plt

#In real mixer block
# Isense resis is 10 ohms
# parallel resistance is 200 ohms
RIsense_real = 10 #5 #5 #20 #5 #5  # 20
Rsafety_real = 200 #50 #91 #50  # 100
Rdiv_real = 5e3 #10e3 #5e3

def RSIS(Rsafety=Rsafety_real, RIsense=RIsense_real, Rn=40.0):
    Rsis = (Rsafety * (RIsense + Rn))/(Rsafety + RIsense + Rn)
    return Rsis

def desired_Vbias(Vsis, Rsafety=Rsafety_real,
                  RIsense=RIsense_real, Rn=40., Rdiv=Rdiv_real):
    """ 
    For a given Vsis in mV (the voltage across the junction)
    calculates the needed voltage from the bias card in volts
    """
    Rsis = RSIS(Rsafety, RIsense, Rn) # effective resistance
    voltage_div_factor = (Rsis/(Rdiv + Rsis)) * (Rn/(Rn + RIsense))
    Vb = Vsis * 1e-3/voltage_div_factor
    return Vb

def dac_voltage(Vsis, Rsafety=Rsafety_real, RIsense=RIsense_real,
                Rn=40.0, Rdiv=Rdiv_real, Rb1=3.4e3, Rb2=10.2e3, Vref=4.05):
    bias_voltage_div_factor = Rb2/(Rb2 + Rb1)
    Vb = desired_Vbias(Vsis, Rsafety=Rsafety, RIsense=RIsense,
                       Rn=Rn, Rdiv=Rdiv)
    dac_set_point_voltage = Vb/bias_voltage_div_factor
    #dac_scale_value = (dac_set_point_voltage + 4.) * 2**16/8.0
    dac_scale_value = (dac_set_point_voltage + Vref) * 2**16/(2*Vref)
    return dac_scale_value

def set_vbias(Vsis, Rsafety=Rsafety_real, RIsense=RIsense_real,
                Rn=40.0, Rdiv=Rdiv_real, Rb1=0.0, Rb2=10.2e3,return_dac_scale_val=False):
    dac_scale_value = int(dac_voltage(Vsis, Rsafety=Rsafety, RIsense=RIsense,
                                  Rn=Rn, Rdiv=Rdiv, Rb1=Rb1, Rb2=Rb2))
    if dac_scale_value < 0:            

        dac_scale_value = 0
    if dac_scale_value >= 2**16:
        dac_scale_value = 2**16 - 1
    voltage_bytes = [dac_scale_value >> 8 , dac_scale_value & 0xFF]
    if return_dac_scale_val:
        return dac_scale_value, voltage_bytes
    else:
        return voltage_bytes

def Vsense(adc_value, gain=133.33, offset=2.0, off=None):
    if off is None:
        return (adc_value - offset)/gain
    else:
        return (adc_value - off)/gain

def Isense(adc_value, gain=285.7, offset=2.0, off=None, RIsense=RIsense_real):
    if off is None:
        V_Isense = (adc_value - offset)/gain  # voltage across RIsense
    else:
        V_Isense = (adc_value - off)/gain  # voltage across RIsense
    return (V_Isense/RIsense)

def Vsense_cal(Vsense, card, channel, cal_file='CalibrationFile.csv'):
    if cal_file=='':
        print('Need calibration file')
        return
    else:
        cal_table = pd.read_csv(cal_file, index_col=0)
        slope = cal_table['mix_slope'][((cal_table.card==card)&(cal_table.channel==channel))].iloc[0]
        offset = cal_table['mix_offset'][((cal_table.card==card)&(cal_table.channel==channel))].iloc[0]
        return (Vsense-offset)/slope
    
def Isense_cal(Isense, card, channel, cal_file='CalibrationFile.csv'):
    if cal_file=='':
        print('Need calibration file')
        return
    else:
        cal_table = pd.read_csv(cal_file, index_col=0)
        slope = cal_table['mix_slope'][((cal_table.card==3)&(cal_table.channel==0))].iloc[0]
        offset = cal_table['mix_offset'][((cal_table.card==3)&(cal_table.channel==0))].iloc[0]
        return (Isense-offset)/slope   

def sweep(t7, vmin, vmax, step, channel=0, timeout=0.010, off=None, card=0, oldBoard=True,
          gain_Vs=133.33, gain_Is=285.7):
    if off is None:
        #if oldBoard:
        #    off = t7.adc_read(channel, 6, card=card) * 2.0
        #else:
        #    off = t7.adc_read(channel, 6, card=card)
        off = t7.adc_read(channel, 6, card=card) * 2.0
        print("Offset : %s" % off)
    old_bias = Vsense(t7.adc_read(channel, 0, card=card), gain=gain_Vs, off=off)/1e-3
    vlist = numpy.arange(vmin, vmax+step, step)
    lisdic = []
    for Vsis in vlist:
        dic = {}
        dic['Vsis'] = Vsis
        voltage_bytes =  set_vbias(Vsis)
        t7.set_dac(channel, voltage_bytes, card=card)
        time.sleep(timeout)
        # off = t7.adc_read(channel, 6) * 2.0
        # dic['Off'] = off
        Vs = Vsense(t7.adc_read(channel, 0, card=card), gain=gain_Vs, off=off)/1e-3
        Is = Isense(t7.adc_read(channel, 1, card=card), gain=gain_Is, off=off)/1e-6
        dic['Vs'] = Vs
        dic['Is'] = Is
        lisdic.append(dic)
    vbytes = set_vbias(old_bias)
    t7.set_dac(channel, vbytes, card=card)
    # off = t7.adc_read(channel, 6) * 2.0
    print("Setting and reading channel %d to voltage: %.3f" % (channel, Vsense(t7.adc_read(channel, 0, card=card), gain=gain_Vs, off=off)/1e-3))
    return pd.DataFrame(lisdic)


def sweep_IF(t7, vmin, vmax, step, channel=0, timeout=0.010, if_freq=6e9, oldBoard=True, card=0):
    pro = Prologix()
    pro.set_freq(if_freq)
    if oldBoard:
        off = t7.adc_read(channel, 6, card=card) * 2.0
    else:
        off = t7.adc_read(channel, 6, card=card)
    print("Offset : %s" % off)
    old_bias = Vsense(t7.adc_read(channel, 0, card=card), off=off)/1e-3
    vlist = numpy.arange(vmin, vmax+step, step)
    lisdic = []
    for Vsis in vlist:
        dic = {}
        dic['Vsis'] = Vsis
        voltage_bytes =  set_vbias(Vsis)
        t7.set_dac(channel, voltage_bytes)
        time.sleep(timeout)
        off = t7.adc_read(channel, 6) * 2.0
        Vs = Vsense(t7.adc_read(channel, 0), off=off)/1e-3
        Is = Isense(t7.adc_read(channel, 1), off=off)/1e-6
        dic['Vs'] = Vs
        dic['Is'] = Is
        tempdic = pro.read_temperature()
        time.sleep(0.025)
        for i in (1, 2, 3, 5, 6, 7):
            dic['T%d' % i ] = tempdic[i]
        power = pro.get_linear_power()
        dic['IFPower'] = power
        lisdic.append(dic)
    vbytes = set_vbias(old_bias)
    t7.set_dac(channel, vbytes)
    off = t7.adc_read(channel, 6) * 2.0
    print("Setting and reading channel %d to voltage: %.3f" % (channel, Vsense(t7.adc_read(channel, 0), off=off)/1e-3))
    return pd.DataFrame(lisdic)

def get_swept_IF(freqs):
    pro = Prologix()
    lisdic = []
    for freq in freqs:
        dic = {}
        pro.set_freq(freq*1e9)
        time.sleep(1.0)
        power = pro.get_linear_power()
        dic['Frequency'] = freq
        dic['Power'] = power
        lisdic.append(dic)
        print("%s: %s" % (freq, power))
    pro.sock.close()
    return pd.DataFrame(lisdic)

def sweep_fluke(t7, fl, vmin, vmax, step, channel=0, timeout=0.010):
    vlist = numpy.arange(vmin, vmax+step, step)
    lisdic = []
    for Vsis in vlist:
        dic = {}
        dic['Vsis'] = Vsis
        voltage_bytes =  set_vbias(Vsis)
        t7.set_dac(channel, voltage_bytes)
        time.sleep(timeout)
        Vs = Vsense(t7.adc_read(channel, 0))/1e-3
        Is = Isense(t7.adc_read(channel, 1))/1e-6
        Vs_fl = fl.measure()[0]/1e-3
        dic['Vs'] = Vs
        dic['Is'] = Is
        dic['Vs_fl'] = Vs_fl
        lisdic.append(dic)
    return pd.DataFrame(lisdic)

def sweep_fluke2(t7, fl, vmin, vmax, step, channel=0, timeout=0.010,
                 fl_meas_label='Vs', card=3, gain_Vs=80, gain_Is=200, off=None):
    vlist = numpy.arange(vmin, vmax+step, step)
    lisdic = []
    for Vsis in vlist:
        dic = {}
        dic['Vsis'] = Vsis
        dac_value, voltage_bytes =  set_vbias(Vsis,return_dac_scale_val=True)
        dic['dac_value_Vsis'] = dac_value
        t7.set_dac(channel, voltage_bytes, card=3)
        time.sleep(timeout)
        Vs_adc = t7.adc_read(channel, 0, card=3)
        Vs = Vsense(Vs_adc, gain=gain_Vs, off=off)/1e-3
        Is_adc = t7.adc_read(channel, 1, card=3)
        Is = Isense(Is_adc, gain=gain_Is, off=off)/1e-6
        Vs_fl = fl.measure()[0]
        dic['Vs'] = Vs
        dic['Vs_adc'] = Vs_adc
        dic['Is'] = Is
        dic['Is_adc'] = Is_adc
        dic['{:s}_fl'.format(fl_meas_label)] = Vs_fl
        lisdic.append(dic)
    return pd.DataFrame(lisdic)

def time_test(t7, Vsis, duration=60, timestep=10, channel=0):
    """ Measure the vsense on a period of time.
    time in seconds
    """
    voltage_bytes =  set_vbias(Vsis)
    t7.set_dac(channel, voltage_bytes)
    #time = numpy.arange(0, time+timestep, timestep)
    lisdic = []
    for t in range(int(duration/timestep)+1):
        dic = {}
        dic['Vsis'] = Vsis
        Vs = Vsense(t7.adc_read(channel, 0))/1e-3
        # Vs_fl = fl.measure()[0]/1e-3
        dic['t'] = datetime.datetime.now()
        dic['Vs'] = Vs
        # dic['Vs_fl'] = Vs_fl
        lisdic.append(dic)
        time.sleep(timestep)
    return pd.DataFrame(lisdic)


def IVcurveTest(sis, df_noLO, t7, freq, power, day, channel=0):
    figIV, axIV = plt.subplots(1,1)
    axIV.plot(df_noLO.Vs, df_noLO.Is, 'o-', label='SIS%0.0f noLO'%sis)

    t7.select_Load('hot')
    time.sleep(.5)
    df1_hot = sweep_IF(t7, -2, 16, 0.1, channel=channel) 

    t7.select_Load('cold')
    time.sleep(.5)
    df1_cold = sweep_IF(t7, -2, 16, 0.1, channel=channel)

    # power = raw_input('What is the max power in mW?')
    axIV.plot(df1_hot.Vs, df1_hot.Is, 'o-',
              label='SIS{:.0f} {:.0f}GHz {:.0f}mW'.format(sis, freq, power))
    axIV.plot(df1_hot.Vs, df1_hot.IFPower/2e-8, 's-',
              label='SIS{:.0f} IF6 {:.0f}GHz {:.0f}mW Hot'.format(sis, freq, power))
    axIV.plot(df1_cold.Vs, df1_cold.IFPower/2e-8, 's-',
              label='SIS{:.0f} IF6 {:.0f}GHz {:.0f}mW Cold'.format(sis, freq, power))

    axIV.set_xlim(0,15)
    axIV.legend()
    axIV.grid()
    axIV.set_title('{:s} 2021 SIS{:.0f} {:.0f}GHz'.format(day,sis,freq))
    figIV.show()

    figIV.savefig('{:s}_2021/{:s}_2021_sis{:.0f}_{:.0f}GHz_ivcurves.png'.format(day,day,sis,freq))

    df1_hot.to_csv('{:s}_2021/sis{:.0f}_{:s}_2021_{:.0f}GHz_{:.0f}mW_IF6_hot.txt'.format(day,sis,day,freq,power))
    df1_cold.to_csv('{:s}_2021/sis{:.0f}_{:s}_2021_{:.0f}GHz_{:.0f}mW_IF6_cold.txt'.format(day,sis,day,freq,power))
    
    return df1_hot, df1_cold, figIV, axIV

def calcTR(phot, pcold, Thot=46.3, Tcold=3.7):
    y = phot/pcold
    TR = (Thot - y*Tcold)/(y-1)
    return TR


def loPowerTest(sis, t7, freqs, freq, power, day, ax):
    if freqs is None:
        freqs = np.arange(3, 9.2, 0.2) 
        
    t7.select_Load('cold')
    time.sleep(.6)
    if_cold = get_swept_IF(freqs)

    t7.select_Load('hot')
    time.sleep(.6)
    if_hot = get_swept_IF(freqs)

    phot, pcold = if_hot.Power, if_cold.Power
    TR = calcTR(phot, pcold)
    power = float(input('What is the power? ')) # ask for power
    ax.plot(freqs, TR, 's-', label='LO {:.0f}mW'.format(power))
    
    labels = (day, sis, day, freq, power)
    if_hot.to_csv('{:s}_2021/sis{:.0f}_{:s}_2021_{:.0f}GHz_{:.0f}mW_ifhot.txt'.format(*labels))
    if_cold.to_csv('{:s}_2021/sis{:.0f}_{:s}_2021_{:.0f}GHz_{:.0f}mW_ifcold.txt'.format(*labels))
    return

def mixer_calibration(sistest, channels=[0,1,2,3,4,5,6,7], makeplot=False, Rn=39, vmin=-20, vmax=20, step=0.1,):
    df = {}
    cal_params={}
    for chan in channels:
        df[chan] = sistest.dc_iv_sweep(channel=chan, device='{:d}_cal'.format(chan),
                                       vmin=vmin, vmax=vmax, step=step,
                                       xlim=(-30, 30), ylim=(-1000, 1000), timeout=0.01, makeplot=makeplot)
        df[chan]['Isis'] = (df[chan].Vsis*1e-3/Rn)*1e6
        # setting everything to 0 before starting a new sweep
        sistest.t7.set_dac([0,1,2,3,4,5,6,7], set_vbias(0, Rn=39), card=2)
        # Voltage fit. cal_params[chan][0] = slope, cal_params[chan][1] = intercept
        cal_params[chan] = numpy.polyfit(df[chan].Vsis, df[chan].Vs, deg=1)
        # After getting the calibration parameters, make a sweep with calibration and plot the calibrated voltages. 
        # See if this changes the current measurements.
        # If necessary make a current calibration.
        # more convenient to use the voltages expected at Isense vs the measured?

    if len(channels)>4:
        nrows = 2
        ncols = int(len(channels)/2)
    else:
        nrows=1
        ncols=len(channels)
        
    fig, axes = plt.subplots(nrows, ncols, figsize=(8,6))
    axes = axes.flatten()
    for chan in channels:
        axes[chan].plot(df[chan].Vsis, df[chan].Vs, 'o', label='Pre-cal')
        slope = cal_params[chan][0]
        intercept = cal_params[chan][1]
        y_fit = df[chan].Vsis*slope + intercept 
        axes[chan].plot(df[chan].Vsis, y_fit, '--', label='Fit')
        y_cal = (df[chan].Vs-intercept)/slope
        axes[chan].plot(df[chan].Vsis, y_cal, '--', label='Cal')
        axes[chan].legend()
        axes[chan].grid()
        axes[chan].set(xlabel='Vsis [mV]', ylabel='Vsense [mV]')
    
    #WORK IN PROGRESS
    
    return df, cal_params
