from omaya.bias.labjackt7 import LabJackT7
import time
import pandas as pd
import numpy
import os
import logging
import sys
import datetime
import numpy as np
from omaya.prologix.prologix_all import Prologix
from omaya.losystem.microlambda_class import MicroLambda
from omaya.utils.sweep_test import get_swept_IF, Vsense, Isense, sweep_IF, \
    sweep, set_vbias, RIsense_real, Rsafety_real, IVcurveTest, \
    loPowerTest
import matplotlib.pyplot as plt
from omaya.omayadb.dblog import logOmaya, calOmaya

class SISTestSuite(object):
    def __init__(self, directory, if_freq=6, oldBoard=True, card=2,
                 channels=[0,1,2,3,4,5,6,7],
                 debug=True):
        self.debug = debug
        logdir = os.path.join(os.getcwd(), 'logs')
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        logfile = os.path.join(logdir, datetime.datetime.now().strftime('sistest_%Y_%m_%d_%H%M.log'))
        logging.basicConfig(filename=logfile,
                            level=logging.INFO,
                            format='%(asctime)s %(levelname)s: %(message)s')
        if not os.path.exists(directory):
            self._print("making directory %s" % directory)
            os.makedirs(directory)
        self.oldBoard = oldBoard
        self.card = card
        self.directory = directory
        # self.t7 = LabJackT7(oldBoard=self.oldBoard)
        # self.t7.start_up(channel=[0, 1], loop_control='Closed', card=self.card)
        # #self.t7.start_up(channel=1, loop_control='Closed')
        # # Startup motor
        # self.t7.setup_motor(0)
        # self.t7.select_Load('hot')
        self.start_all()

        self.if_freq = if_freq
        self.if_frequencies = np.arange(3, 9.2, 0.2) 
        self.offsets = {}
        self._get_offsets(channels) 
        plt.ion() # this command allows to show the plot inside a loop

    def start_all(self):
        self.t7 = LabJackT7(oldBoard=self.oldBoard, api_mode=True)
        self.t7.start_up(channel=[0, 1], loop_control='Closed', card=self.card)
        # #self.t7.start_up(channel=1, loop_control='Closed')
        # # Startup motor
        self.t7.setup_motor(0)
        self.t7.select_Load('hot')        
        self.pro = Prologix()
        #self.pro.e3631a_output_on()
        self.ml = MicroLambda()
        
    def close_all(self):
        self.t7.close()
        self.pro.close()
        self.ml.close()
        self._print("Connection Closed.")

    def _print(self, msg, loglevel=logging.INFO, ):
        if self.debug:
            print(msg)
        logging.log(level=loglevel, msg=msg)
        try:
            logOmaya(loglevel, msg)
        except:
            # Fail silently
            pass
        
    def _get_offsets(self,channels=[0,1,2,3,4,5,6,7]):
        for channel in channels:
            self.offsets[channel] = self.t7.adc_read(channel, 6, card=self.card) * 2.0
        self._print('Offsets: {}'.format(str(self.offsets)))  
        
    def dc_iv_sweep(self, channel=0, device='3',
                    vmin=-2, vmax=16, step=0.1,
                    gain_Vs=80, gain_Is=200,
                    timeout=0.010, off=None,
                    makeplot=True, save=True, xlim=(0,25), ylim=(-10,200), Rn=39,
                    calibrated=False, slope=1, offset=0):
        """
        Function to get the IV sweep with no LO. 
        """
        self._print('Performing DC IV Sweep on channel %d device %s' % (channel, device))
        if off is None:
            #off = self.t7.adc_read(channel, 6) * 2.0
            off = self.offsets[channel]
            self._print("Offset : %s" % off)
        old_bias = Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3
        vlist = numpy.arange(vmin, vmax+step, step)
        lisdic = []
        for Vsis in vlist:
            dic = {}
            dic['Vsis'] = Vsis
            voltage_bytes =  set_vbias(Vsis, Rn=Rn, calibrated=calibrated,
                                       slope=slope, offset=offset)
            self.t7.set_dac([channel], voltage_bytes, card=self.card)
            time.sleep(timeout)
            # off = t7.adc_read(channel, 6) * 2.0
            # dic['Off'] = off
            Vs = Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3
            Is = Isense(self.t7.adc_read(channel, 1, card=self.card), gain=gain_Is, off=off)/1e-6
            dic['Vs'] = Vs
            dic['Is'] = Is
            lisdic.append(dic)
        vbytes = set_vbias(old_bias)
        self.t7.set_dac([channel], vbytes, card=self.card)
        # off = t7.adc_read(channel, 6) * 2.0
        self._print("Setting and reading channel %d to voltage: %.3f" % (channel, Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3))
        df = pd.DataFrame(lisdic)
        if makeplot:
            figIV, axIV = plt.subplots(1,1,figsize=(8,6))
            axIV.plot(df.Vs, df.Is, 'o-', label='SIS%s cold' % device)
            axIV.legend(loc='best')
            axIV.set_xlim(xlim)
            axIV.set_xlabel('Voltage [mV]')
            axIV.set_ylim(ylim)
            axIV.set_ylabel(r'Current [$\mu$A]')
            axIV.grid()
        if save:
            fname = os.path.join(self.directory, 'sis%s_cold.csv' % device)
            df.to_csv(fname)
            self._print('Saving DC IV sweep to %s' % fname)
        return df

    def sweep_IF_both(self, vmin=-2, vmax=16, step=0.1,
                      timeout=0.010, gain_Vs=80, gain_Is=200,
                      channel=0, if_freq=None, off=None,):
        if if_freq is None:
            if_freq = self.if_freq
        self._print('Setting IF frequency to %s GHz' % if_freq)
        #self.pro.set_freq(if_freq*1e9)
        self.pro.set_83650_freq(if_freq*1e9)
        if off is None:
            off = self.offsets[channel]
        old_bias = Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3
        vlist = numpy.arange(vmin, vmax+step, step)
        lisdic = []
        for Vsis in vlist:
            dic = {}
            dic['Vsis'] = Vsis
            voltage_bytes =  set_vbias(Vsis)
            self.t7.set_dac([channel], voltage_bytes, card=self.card)
            time.sleep(timeout)
            off = self.t7.adc_read(channel, 6, card=self.card) * 2.0
            Vs = Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3
            Is = Isense(self.t7.adc_read(channel, 1, card=self.card), gain=gain_Is, off=off)/1e-6
            dic['Vs'] = Vs
            dic['Is'] = Is
            tempdic = self.pro.read_temperature()
            time.sleep(0.025)
            for i in (1, 2, 3, 5, 6, 7):
                dic['T%d' % i ] = tempdic[i]
            for ifchannel in range(2):
                power = self.pro.get_linear_power(IF=ifchannel)
                dic['IFPower_%d' % ifchannel] = power
            lisdic.append(dic)
        vbytes = set_vbias(old_bias)
        self.t7.set_dac([channel], vbytes, card=self.card)
        off = self.t7.adc_read(channel, 6, card=self.card) * 2.0
        self._print("Setting and reading channel %d to voltage: %.3f" % (channel, Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3))
        return pd.DataFrame(lisdic)

    def sweep_IF(self, vmin=-2, vmax=16, step=0.1,
                 timeout=0.010, gain_Vs=80, gain_Is=200,
                 channel=0, ifchannel=0, off=None,):
        self._print('Setting IF frequency to %s GHz' % self.if_freq)
        self.pro.set_83650_freq(self.if_freq*1e9)
        if off is None:
            off = self.offsets[channel]
        old_bias = Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3
        vlist = numpy.arange(vmin, vmax+step, step)
        lisdic = []
        for Vsis in vlist:
            dic = {}
            dic['Vsis'] = Vsis
            voltage_bytes =  set_vbias(Vsis)
            self.t7.set_dac([channel], voltage_bytes, card=self.card)
            time.sleep(timeout)
            off = self.t7.adc_read(channel, 6, card=self.card) * 2.0
            Vs = Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3
            Is = Isense(self.t7.adc_read(channel, 1, card=self.card), gain=gain_Is, off=off)/1e-6
            dic['Vs'] = Vs
            dic['Is'] = Is
            tempdic = self.pro.read_temperature()
            time.sleep(0.025)
            for i in (1, 2, 3, 5, 6, 7):
                dic['T%d' % i ] = tempdic[i]
            power = self.pro.get_linear_power(IF=ifchannel)
            dic['IFPower'] = power
            lisdic.append(dic)
        vbytes = set_vbias(old_bias)
        self.t7.set_dac([channel], vbytes, card=self.card)
        off = self.t7.adc_read(channel, 6, card=self.card) * 2.0
        self._print("Setting and reading channel %d to voltage: %.3f" % (channel, Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=off)/1e-3))
        return pd.DataFrame(lisdic)
    
    def PIV_Curves(self, channel=0, device='3',
                   ifchannel=0,
                   df_noLO=None, lofreq=216,
                   vmin=-2, vmax=16, step=0.1,
                   gain_Vs=80, gain_Is=200, 
                   makeplot=True, save=True):
        figIV, axIV = plt.subplots(1,1,figsize=(8,6))
        axIV.plot(df_noLO.Vs, df_noLO.Is, 'o-', label='SIS%s noLO' % device)

        self._print("Moving to Hot Load")
        self.t7.select_Load('hot')
        time.sleep(.5)
        df1_hot = self.sweep_IF(vmin=vmin, vmax=vmax, step=step,
                                gain_Vs=gain_Vs, gain_Is=gain_Is,
                                channel=channel, ifchannel=ifchannel) 
        self.t7.select_Load('cold')
        time.sleep(.5)
        self._print("Moving to Cold Load")
        df1_cold = self.sweep_IF(vmin=vmin, vmax=vmax, step=step,
                                 gain_Vs=gain_Vs, gain_Is=gain_Is,
                                 channel=channel, ifchannel=ifchannel) 

        power = float(self.pro.get_lo_power())/1e-3
        # power = raw_input('What is the max power in mW?')
        axIV.plot(df1_hot.Vs, df1_hot.Is, 'o-',
                  label='SIS{:s} {:.0f}GHz {:.0f}mW'.format(device, lofreq, power))
        axIV.plot(df1_hot.Vs, df1_hot.IFPower/1e-8, 's-',
                  label='SIS{:s} IF{:.0f} {:.0f}GHz {:.0f}mW Hot'.format(device, self.if_freq, lofreq, power))
        axIV.plot(df1_cold.Vs, df1_cold.IFPower/1e-8, 's-',
                  label='SIS{:s} IF{:.0f} {:.0f}GHz {:.0f}mW Cold'.format(device, self.if_freq, lofreq, power))

        #axIV.set_xlim(0, 25)
        axIV.set_xlabel('mV')
        #if df1_hot.Is.max()>500:
        #    axIV.set_ylim(-10,1000)
        #else:
        #    axIV.set_ylim(-10, 500)
        axIV.set_ylim(-10, 400)
        axIV.set_ylabel('uA')
        axIV.legend()
        axIV.grid()
        axIV.set_title('{:s} SIS{:s} {:.0f}GHz'.format(self.directory, device, lofreq))
        #figIV.show()
        plt.draw()
        plt.show()
        plt.pause(0.001)

        figname = os.path.join(self.directory, '{:s}_sis{:s}_{:.0f}GHz_ivcurves.png'.format(self.directory, device, lofreq))
        figIV.savefig(figname, dpi=150)
        self._print("Saving figure for PIV Curve to %s" % figname)

        fname_hot = os.path.join(self.directory,
                                 'sis{:s}_{:s}_{:.0f}GHz_{:.0f}mW_IF6_hot.txt'.format(device, self.directory, lofreq, power))
        fname_cold = os.path.join(self.directory,
                                  'sis{:s}_{:s}_{:.0f}GHz_{:.0f}mW_IF6_cold.txt'.format(device, self.directory, lofreq, power))
        df1_hot.to_csv(fname_hot)
        df1_cold.to_csv(fname_cold)
        self._print("Saving hot and cold PIV csv files to %s and %s" % (fname_hot, fname_cold))
        return df1_hot, df1_cold, figIV, axIV
        
    def get_and_set_optimal_bias(self, channel=0, device='3', 
                                 ifchannel=0,
                                 df_noLO=None, lofreq=216,
                                 vmin=-2, vmax=16, step=0.1,
                                 gain_Vs=80, gain_Is=200,
                                 makeplot=True, save=True, stepvmin=9, stepvmax=12):
        
        df_hot, df_cold, figIV, axIV = self.PIV_Curves(channel=channel, device=device,
                                                       ifchannel=ifchannel,
                                                       df_noLO=df_noLO, lofreq=lofreq,
                                                       vmin=vmin, vmax=vmax, step=step,
                                                       gain_Vs=gain_Vs, gain_Is=gain_Is,
                                                       makeplot=makeplot, save=save)
        #phot = df_hot[(df_hot.Vs>7.8)&(df_hot.Vs<12)].IFPower
        #pcold = df_cold[(df_cold.Vs>7.8)&(df_cold.Vs<12)].IFPower
        #if device=='4':
        #    stepvmin = 11.0
        phot = df_hot[(df_hot.Vs>stepvmin)&(df_hot.Vs<stepvmax)].IFPower
        pcold = df_cold[(df_cold.Vs>stepvmin)&(df_cold.Vs<stepvmax)].IFPower        
        Th = df_hot.T3.mean()
        Tc = df_cold.T7.mean()
        y = phot/pcold
        TR = (Th - y*Tc)/(y-1) 
        opt_voltage = df_hot.Vsis[TR[TR>0].idxmin()]
        self._print('Optimum Voltage for channel %d ifchannel %d SIS %s is %s V' % (channel, ifchannel, device, opt_voltage))
        self.t7.set_dac([channel], set_vbias(opt_voltage), card=self.card)
        time.sleep(0.010)
        Vs = Vsense(self.t7.adc_read(channel, 0, card=self.card), gain=gain_Vs, off=self.offsets[channel])/1e-3
        self._print('Voltage read back %s mV' % Vs)
        return(opt_voltage)
    
    def get_swept_IF(self, freqs, ifchannels=[0,1]):
        lisdic = []
        for freq in freqs:

            dic = {}
            self.pro.set_83650_freq(freq*1e9)
            time.sleep(1.0)
            dic['Frequency'] = freq
            for IFchan in ifchannels:
                power = self.pro.get_linear_power(IF=IFchan)
                dic['Power_{}'.format(IFchan)] = power
                self._print("%s:  %s IF_%s" % (freq, power,IFchan))
            lisdic.append(dic)
        return pd.DataFrame(lisdic)

    def calcTR(self, phot, pcold, Thot=47.6, Tcold=3.8):
        y = phot/pcold
        TR = (Thot - y*Tcold)/(y-1)
        return TR
    
    def loPowerTest(self, lofreq=216,
                    refresh=False, update_current=True, sis=['1','2'],
                    gain_Vs=80, gain_Is=200,
                    channels=[0,1], ifchannels=[0,1]):
        nchans = len(ifchannels)
        self._print("Sweeping across channels: %s, ifchannels: %s, sis: %s" % (channels, ifchannels, sis))
        if not hasattr(self, 'axLO') or refresh:
            figLO, self.axLO = plt.subplots(1, nchans, figsize=(8*nchans,6))
            if nchans == 1:
                self.axLO = [self.axLO]
        else:
            figLO = self.axLO[0].get_figure()
        if refresh:
            self.lo_current = []

        self.t7.select_Load('cold')
        time.sleep(.6)
        if_cold = self.get_swept_IF(self.if_frequencies, ifchannels)
        # if_cold = self.get_swept_IF(self.if_frequencies, ifchan)

        self.t7.select_Load('hot')
        time.sleep(.6)
        if_hot = self.get_swept_IF(self.if_frequencies, ifchannels)
        #if_hot = self.get_swept_IF(self.if_frequencies, ifchan)

        for i in range(nchans):
            self._print('Calculating TR for sis{}, if{} and chan{}'.format(sis[i], ifchannels[i], channels[i]))
            pow_key = 'Power_{}'.format(ifchannels[i])
            phot, pcold = if_hot[pow_key], if_cold[pow_key]
            TR = self.calcTR(phot, pcold)
            lopower = float(self.pro.get_lo_power()/1e-3)
            dic = {}
            dic['lopower'] = lopower
            dic['Vs'] = Vsense(self.t7.adc_read(channels[i], 0, card=self.card), gain=gain_Vs,
                               off=self.offsets[channels[i]])/1e-3
            dic['Is'] = Isense(self.t7.adc_read(channels[i], 1, card=self.card), gain=gain_Is,
                               off=self.offsets[channels[i]])/1e-6
            #self.lo_current.append(dic) 
            self.axLO[i].plot(self.if_frequencies, TR, 's-', label='LO {:.0f}mW {:.0f}uA'.format(lopower,dic['Is']))

            fname_hot = os.path.join(self.directory, 'sis{:s}_{:s}_{:.0f}GHz_{:.0f}mW_if{}_hot.txt'.format(sis[i], self.directory, lofreq, lopower,ifchannels[i]))
            fname_cold = os.path.join(self.directory, 'sis{:s}_{:s}_{:.0f}GHz_{:.0f}mW_if{}_cold.txt'.format(sis[i], self.directory, lofreq, lopower, ifchannels[i]))
            self.save_lo_current(dic=dic, old=False, filename=fname_hot)
            self.save_lo_current(dic=dic, old=False, filename=fname_cold)
            if_hot.to_csv(fname_hot, mode='a')
            if_cold.to_csv(fname_cold, mode='a')
            self._print('Saved files %s and %s' % (fname_hot, fname_cold))
        return figLO

    
    def save_lo_current(self, device='3', lofreq=216, filename=None, old=True, dic=''):
        if old:
            if filename is None:
                filename = os.path.join(self.directory, 'sis%s_%sGHz_lopower_Vs_Is.txt' % (device, lofreq))
            dflo = pd.DataFrame(self.lo_current)
            dflo.to_csv(filename)
        else:
            if filename is None:
                filename = os.path.join(self.directory, 'sis{:s}_{:s}_{:.0f}GHz_{:.0f}mW_ifhot.txt'.format(device, self.directory, lofreq, lopower))
            f = open(filename,'w')
            f.write('# '+ str(dic) + '\n')
            f.close()
            
            
    def set_lo_frequency(self, frequency):
        """
        frequency in GHz
        """
        if frequency < 216:
            frequency = 216
        if frequency > 285:
            frequency = 285
        self._print('Setting LO Frequency to %s GHz' % frequency)
        self.ml.set_frequency(frequency/12.0)

    def get_lo_power(self):
        return self.pro.get_lo_power()

    def set_lo_power_voltage(self, voltage):
        #self.pro.e3631a_dual_set_voltage(voltage)
        self.ml.set_lo_power_voltage(voltage)
        
    # def full_loPowerTest(self, fmin=216, fmax=279, optPow=30):
    #     lopowlist = np.arrange(.7, -8, .2) 
    #     for lopow in pows:
    #         if lopow>0:
    #             var = input('connector in correct position?')
    #         self.pro.set_ferrite_voltage(lopow)
    #         loPowerTest(self, device='3', lofreq=216, refresh=False)

    def _check_current(self, Is, imin=50.0, imax=70.0):
        self._print("Current now is %s uA" % Is)
        if Is >= imin and Is <= imax:
            check = 0
        elif Is > imax:
            check = -1
        elif Is < imin:
            check = 1
        return check

    def _check_voltage(self, Vs, vsmin=10.2, vsmax=10.4):
        self._print("Voltage now is %s mV" % Vs)
        if Vs >= vsmin and Vs <= vsmax:
            check = 0
        elif Vs > vsmax:
            check = -1
        elif Vs < vsmin:
            check = 1
        return check
    
    def lopower_servo_loop(self, channel=1, device='1',
                           start_ferr=0.7, gain_Is=200,
                           imin=50.0, imax=70.0, vbias=5.0,
                           ferr_min=-1.0, ferr_max=0.7,
                           ferr_step=0.1):
        vb = set_vbias(vbias)
        self.t7.set_dac([channel], vb, card=self.card)
        time.sleep(0.050)
        Is = Isense(self.t7.adc_read(channel, 1, card=self.card), gain=gain_Is, off=self.offsets[channel])/1e-6
        check = self._check_current(Is, imin=imin, imax=imax)
        self._print("Check: %s" % check)
        if check == 0:
            self._print("Current at %s. Done" % Is)
            return 
        ferr = start_ferr
        self.set_lo_power_voltage(ferr)
        time.sleep(10.0)
        lopower = self.get_lo_power()
        Is = Isense(self.t7.adc_read(channel, 1, card=self.card), gain=gain_Is, off=self.offsets[channel])/1e-6
        check = self._check_current(Is, imin=imin, imax=imax)
        self._print("Check: %s" % check)        
        while check != 0:
            if check == -1:
                if ferr >= ferr_min:
                    ferr -= ferr_step
                else:
                    print("No more range available in ferrite. Already at %s" % ferr)
                    return
            if check == 1:
                if ferr <= ferr_max:
                    ferr += ferr_step
                else:
                    print("No more range available in ferrite. Already at %s" % ferr)
                    return
            self.set_lo_power_voltage(ferr)
            time.sleep(10.0)
            lopower = self.get_lo_power()
            Is = Isense(self.t7.adc_read(channel, 1, card=self.card), gain=gain_Is, off=self.offsets[channel])/1e-6
            check = self._check_current(Is, imin=imin, imax=imax)            
            self._print("Check: %s" % check)

    def lopower_servo_loop_at_set_voltage(self, channel=1, device='1',
                                          start_ferr=0.7, gain_Is=200,
                                          imin=50.0, imax=70.0, 
                                          ferr_min=-1.0, ferr_max=0.7,
                                          ferr_step=0.05):
        Is = Isense(self.t7.adc_read(channel, 1, card=self.card),
                    gain=gain_Is, off=self.offsets[channel])/1e-6
        check = self._check_current(Is, imin=imin, imax=imax)
        self._print("Check: %s" % check)
        if check == 0:
            self._print("Current at %s. Done" % Is)
            return start_ferr
        ferr = start_ferr
        self.set_lo_power_voltage(ferr)
        time.sleep(10.0)
        lopower = self.get_lo_power()
        Is = Isense(self.t7.adc_read(channel, 1, card=self.card),
                    gain=gain_Is, off=self.offsets[channel])/1e-6
        check = self._check_current(Is, imin=imin, imax=imax)
        self._print("Check: %s" % check)        
        while check != 0:
            if check == -1:
                if ferr >= ferr_min:
                    ferr -= ferr_step
                else:
                    print("No more range available in ferrite. Already at %s" % ferr)
                    return ferr_min
            if check == 1:
                if ferr <= ferr_max:
                    ferr += ferr_step
                else:
                    print("No more range available in ferrite. Already at %s" % ferr)
                    return ferr_max
            self.set_lo_power_voltage(ferr)
            time.sleep(10.0)
            lopower = self.get_lo_power()
            Is = Isense(self.t7.adc_read(channel, 1, card=self.card), gain=gain_Is,
                        off=self.offsets[channel])/1e-6
            check = self._check_current(Is, imin=imin, imax=imax)            
            self._print("Check: %s" % check)
        return ferr
    
    def full_test(self, lofreqs, channels=[0,1], sis=['1','2'],
                  ifchannels=[0, 1],
                  df_noLO=[], ferrmax=0.7, ferrmin=-0.4,
                  ferrstep=-0.2, imin=40, imax=70, vbias=3.8,
                  vmin=3.0, vmax=5.0, gain_Vs=80, gain_Is=200,
                  yig=True, stepvmin=9, stepvmax=12):
        #lofreqs = np.arrange(fmin, fmax+1, 3)
        nchans = len(ifchannels)
        for lofreq in lofreqs:
            tt=time.time()
            if yig:
                self.set_lo_frequency(lofreq)
            time.sleep(0.5)
            self.lopower_servo_loop(channel=channels[0], device=sis[0],
                                    start_ferr=ferrmax, gain_Is=gain_Is,
                                    imin=imin, imax=imax, vbias=vbias)
            time.sleep(1.0)
            for chan in range(nchans):
                self.get_and_set_optimal_bias(channel=channels[chan], device=sis[chan],
                                              ifchannel=ifchannels[chan],
                                              df_noLO=df_noLO[chan],
                                              lofreq=lofreq, vmin=vmin, vmax=vmax,
                                              stepvmin=stepvmin, stepvmax=stepvmax,
                                              gain_Vs=gain_Vs, gain_Is=gain_Is)
            time.sleep(1.0)
            plt.draw()
            plt.show()
            plt.pause(0.001)
            for i, ferr in enumerate(np.arange(ferrmax, ferrmin, ferrstep)):
                self.set_lo_power_voltage(ferr) 
                time.sleep(10.0) 
                if i == 0:
                    figLO = self.loPowerTest(channels=channels, sis=sis,
                                             ifchannels=ifchannels,
                                             gain_Vs=gain_Vs, gain_Is=gain_Is,
                                             lofreq=lofreq, refresh=True)
                    axLO = self.axLO
                    for j, ax in enumerate(axLO):
                        ax.legend(loc='best')
                        ax.grid()
                        if yig:
                            title ='%s SIS%s %sGHz YIG' % (self.directory, sis[j],
                                                             lofreq)
                        else:
                            title ='%s SIS%s %sGHz Gunn' % (self.directory, sis[j],
                                                             lofreq)
                        ax.set(ylim=(0, 300),
                               title=title)
                    plt.draw()
                    plt.show()
                    plt.pause(0.001)
                else: 
                    figLO = self.loPowerTest(channels=channels, sis=sis,
                                             ifchannels=ifchannels,
                                             lofreq=lofreq, refresh=False)
                    for j, ax in enumerate(self.axLO):
                        ax.legend(loc='best')
                    plt.draw()
                    plt.show()
                    plt.pause(0.001)
                filename = os.path.join(self.directory, 'sis_%s_%sGHz_IF_sweep_lopowers.png' % (self.directory,lofreq))    
                figLO.savefig(filename,dpi=150)
                for chan in range(nchans):
                    self.save_lo_current(device=sis[chan], lofreq=lofreq)
            print('total time of test: {:.3f}s'.format(time.time()-tt))

    def full_test_both_old(self, lofreqs, channels=[0,1], sis=['1','2'],
                           ifchannels=[0, 1],
                           df_noLO=[], ferrmax=0.7, ferrmin=-0.4,
                           ferrstep=-0.2, imin=40, imax=70, vbias=3.8,
                           vmin=3.0, vmax=5.0, gain_Vs=80, gain_Is=200,
                           yig=True, stepvmin=9, stepvmax=12):
        #lofreqs = np.arrange(fmin, fmax+1, 3)
        nchans = len(ifchannels)
        for lofreq in lofreqs:
            tt=time.time()
            if yig:
                self.set_lo_frequency(lofreq)
            time.sleep(0.5)
            self.lopower_servo_loop(channel=channels[0], device=sis[0],
                                    start_ferr=ferrmax, gain_Is=gain_Is,
                                    imin=imin, imax=imax, vbias=vbias)
            time.sleep(1.0)
            chan_opt_bias = {}
            for chan in range(nchans):
                for chan2 in range(nchans):
                    vb = set_vbias(0.0)
                    self.t7.set_dac([chan2], vb, card=self.card)
                    time.sleep(0.050)                
                opt_bias = self.get_and_set_optimal_bias(channel=channels[chan], device=sis[chan],
                                                         ifchannel=ifchannels[chan],
                                                         df_noLO=df_noLO[chan],
                                                         lofreq=lofreq, vmin=vmin, vmax=vmax,
                                                         stepvmin=stepvmin, stepvmax=stepvmax,
                                                         gain_Vs=gain_Vs, gain_Is=gain_Is)
                chan_opt_bias[channels[chan]] = opt_bias

            for chan in range(nchans):
                vb = chan_opt_bias[channels[chan]]
                self.t7.set_dac([chan], set_vbias(vb), card=self.card)
                time.sleep(0.050)
            time.sleep(1.0)
            plt.draw()
            plt.show()
            plt.pause(0.001)
            for i, ferr in enumerate(np.arange(ferrmax, ferrmin, ferrstep)):
                self.set_lo_power_voltage(ferr) 
                time.sleep(10.0) 
                if i == 0:
                    figLO = self.loPowerTest(channels=channels, sis=sis,
                                             ifchannels=ifchannels,
                                             gain_Vs=gain_Vs, gain_Is=gain_Is,
                                             lofreq=lofreq, refresh=True)
                    axLO = self.axLO
                    for j, ax in enumerate(axLO):
                        ax.legend(loc='best')
                        ax.grid()
                        if yig:
                            title ='%s SIS%s %sGHz YIG' % (self.directory, sis[j],
                                                             lofreq)
                        else:
                            title ='%s SIS%s %sGHz Gunn' % (self.directory, sis[j],
                                                             lofreq)
                        ax.set(ylim=(0, 300),
                               title=title)
                    plt.draw()
                    plt.show()
                    plt.pause(0.001)
                else: 
                    figLO = self.loPowerTest(channels=channels, sis=sis,
                                             ifchannels=ifchannels,
                                             lofreq=lofreq, refresh=False)
                    for j, ax in enumerate(self.axLO):
                        ax.legend(loc='best')
                    plt.draw()
                    plt.show()
                    plt.pause(0.001)
                filename = os.path.join(self.directory, 'sis_%s_%sGHz_IF_sweep_lopowers.png' % (self.directory,lofreq))    
                figLO.savefig(filename,dpi=150)
                for chan in range(nchans):
                    self.save_lo_current(device=sis[chan], lofreq=lofreq)
            print('total time of test: {:.3f}s'.format(time.time()-tt))


    def full_test_both(self, lofreqs, channels=[0,1], sis=['1','2'],
                       ifchannels=[0, 1], ferrmax=0.7, ferrmin=-0.4,
                       ferrstep=-0.2,
                       df_noLO=[], ismax=60, ismin=10,
                       isstep=-5, imin=40, imax=70, vbias=3.8,
                       vmin=3.0, vmax=5.0, gain_Vs=80, gain_Is=200,
                       yig=True, stepvmin=9, stepvmax=12,
                       current_servo=True):
        #lofreqs = np.arrange(fmin, fmax+1, 3)
        nchans = len(ifchannels)
        for lofreq in lofreqs:
            tt=time.time()
            if yig:
                self.set_lo_frequency(lofreq)
            time.sleep(0.5)
            self.lopower_servo_loop(channel=channels[0], device=sis[0],
                                    start_ferr=ferrmax, gain_Is=gain_Is,
                                    imin=imin, imax=imax, vbias=vbias)
            time.sleep(1.0)
            chan_opt_bias = {}
            for chan in range(nchans):
                for chan2 in range(nchans):
                    vb = set_vbias(25.0)
                    self.t7.set_dac([chan2], vb, card=self.card)
                    time.sleep(0.050)                
                opt_bias = self.get_and_set_optimal_bias(channel=channels[chan], device=sis[chan],
                                                         ifchannel=ifchannels[chan],
                                                         df_noLO=df_noLO[chan],
                                                         lofreq=lofreq, vmin=vmin, vmax=vmax,
                                                         stepvmin=stepvmin, stepvmax=stepvmax,
                                                         gain_Vs=gain_Vs, gain_Is=gain_Is)
                chan_opt_bias[channels[chan]] = opt_bias

            for chan in range(nchans):
                vb = chan_opt_bias[channels[chan]]
                self.t7.set_dac([chan], set_vbias(vb), card=self.card)
                time.sleep(0.050)
            time.sleep(1.0)
            plt.draw()
            plt.show()
            plt.pause(0.001)
            ferr = ferrmax
            if current_servo:
                for i, is_current in enumerate(np.arange(ismax, ismin, isstep)):
                    #self.set_lo_power_voltage(ferr)
                    ferr = self.lopower_servo_loop_at_set_voltage(channel=channels[0],
                                                                  device=sis[0], start_ferr=ferr,
                                                                  gain_Is=gain_Is,
                                                                  imin=is_current-(abs(isstep)*0.5),
                                                                  imax=is_current+(abs(isstep)*0.5),
                                                                  ferr_step=0.05)
                    time.sleep(10.0) 
                    if i == 0:
                        figLO = self.loPowerTest(channels=channels, sis=sis,
                                                 ifchannels=ifchannels,
                                                 gain_Vs=gain_Vs, gain_Is=gain_Is,
                                                 lofreq=lofreq, refresh=True)
                        axLO = self.axLO
                        for j, ax in enumerate(axLO):
                            ax.legend(loc='best')
                            ax.grid()
                            if yig:
                                title ='%s SIS%s %sGHz YIG' % (self.directory, sis[j],
                                                                 lofreq)
                            else:
                                title ='%s SIS%s %sGHz Gunn' % (self.directory, sis[j],
                                                                 lofreq)
                            ax.set(ylim=(0, 300),
                                   title=title,
                                   ylabel='TR',
                                   xlabel='IF [GHz]',
                                   )
                        plt.draw()
                        plt.show()
                        plt.pause(0.001)
                    else: 
                        figLO = self.loPowerTest(channels=channels, sis=sis,
                                                 ifchannels=ifchannels,
                                                 lofreq=lofreq, refresh=False)
                        for j, ax in enumerate(self.axLO):
                            ax.legend(loc='best')
                        plt.draw()
                        plt.show()
                        plt.pause(0.001)
                    filename = os.path.join(self.directory, 'sis_%s_%sGHz_IF_sweep_lopowers.png' % (self.directory,lofreq))    
                    figLO.savefig(filename,dpi=150)
                    for chan in range(nchans):
                        self.save_lo_current(device=sis[chan], lofreq=lofreq)
            else:
                for i, ferr in enumerate(np.arange(ferrmax, ferrmin, ferrstep)):
                    self.set_lo_power_voltage(ferr) 
                    time.sleep(10.0) 
                    if i == 0:
                        figLO = self.loPowerTest(channels=channels, sis=sis,
                                                 ifchannels=ifchannels,
                                                 gain_Vs=gain_Vs, gain_Is=gain_Is,
                                                 lofreq=lofreq, refresh=True)
                        axLO = self.axLO
                        for j, ax in enumerate(axLO):
                            ax.legend(loc='best')
                            ax.grid()
                            if yig:
                                title ='%s SIS%s %sGHz YIG' % (self.directory, sis[j],
                                                                 lofreq)
                            else:
                                title ='%s SIS%s %sGHz Gunn' % (self.directory, sis[j],
                                                                 lofreq)
                            ax.set(ylim=(0, 300),
                                   title=title)
                        plt.draw()
                        plt.show()
                        plt.pause(0.001)
                    else: 
                        figLO = self.loPowerTest(channels=channels, sis=sis,
                                                 ifchannels=ifchannels,
                                                 lofreq=lofreq, refresh=False)
                        for j, ax in enumerate(self.axLO):
                            ax.legend(loc='best')
                        plt.draw()
                        plt.show()
                        plt.pause(0.001)
                    filename = os.path.join(self.directory, 'sis_%s_%sGHz_IF_sweep_lopowers.png' % (self.directory,lofreq))    
                    figLO.savefig(filename,dpi=150)
                    for chan in range(nchans):
                        self.save_lo_current(device=sis[chan], lofreq=lofreq)
                
            print('total time of test: {:.3f}s'.format(time.time()-tt))
            

    def voltage_servo_loop(self, channel=1, device='1',
                           gain_Vs=80,
                           vsmin=10.1, vsmax=10.3,
                           vstep=0.05, start_vb=7.9,
                           vbmin=-20, vbmax=20.):
        Vs = Vsense(self.t7.adc_read(channel, 0, card=self.card),
                    gain=gain_Vs, off=self.offsets[channel])/1e-3
        check = self._check_voltage(Vs, vsmin=vsmin, vsmax=vsmax)
        self._print("Check: %s" % check)
        if check == 0:
            self._print("Voltage for device %s (channel %d) at %s. Done" % (device, channel, Vs))
            return 
        vb = start_vb
        self.t7.set_dac([channel], set_vbias(vb), card=self.card)
        time.sleep(0.005)
        Vs = Vsense(self.t7.adc_read(channel, 0, card=self.card),
                    gain=gain_Vs, off=self.offsets[channel])/1e-3
        check = self._check_voltage(Vs, vsmin=vsmin, vsmax=vsmax)
        self._print("Check: %s" % check)        
        while check != 0:
            if check == -1:
                if vb >= vbmin:
                    vb -= vstep
                else:
                    print("No more range available in bias. Already at %s" % vb)
                    return 
            if check == 1:
                if vb <= vbmax:
                    vb += vstep
                else:
                    print("No more range available in bias. Already at %s" % vb)
                    return
            self.t7.set_dac([channel], set_vbias(vb), card=self.card)
            time.sleep(0.005)
            Vs = Vsense(self.t7.adc_read(channel, 0, card=self.card),
                        gain=gain_Vs, off=self.offsets[channel])/1e-3
            check = self._check_voltage(Vs, vsmin=vsmin, vsmax=vsmax)
            self._print("Check: %s" % check)
        return 
            
    def sideband_test(self, lofreq, channels=[1, 0],
                      sis=['3', '4'], ifchannels=[0, 1],
                      opt_Vs=[10.5, 10.5],
                      vmin=-2, vmax=22, gain_Vs=80,
                      gain_Is=200, if_freq=6):
        # Generate 4 CSV files.

        figIV, axIV = plt.subplots(1, 1, figsize=(8,6))

        power = float(self.get_lo_power())/1e-3
        power_s = "%.1f" % power
        ifs = "%.1f" % if_freq
        
        # Turn 1 device on, other dev max - sweep for both IF powers hot and cold
        ind = 0
        channel1 = channels[ind]
        device1 = sis[ind]
        channel2 = channels[ind+1]
        device2 = sis[ind+1]
        opt_voltage = opt_Vs[ind]
        self._print("Setting device %s to it opt voltage %s mV" % (device1, opt_voltage))
        self.voltage_servo_loop(channel=channel1, device=device1, vsmin=opt_voltage-0.1,
                                vsmax=opt_voltage+0.1)
        self._print("Setting device %s to it max voltage %s mV" % (device2, 25))
        self.t7.set_dac([channel2], set_vbias(25, Rn=40.0), card=self.card)

        #hot then cold
        self.t7.select_Load('hot')
        time.sleep(0.1)
        df_hot = self.sweep_IF_both(vmin=vmin, vmax=vmax, gain_Vs=gain_Vs,
                                    gain_Is=gain_Is, channel=channel1, if_freq=if_freq)
        filename = os.path.join(self.directory, 'sis%s_on_sis%s_max_%s_%sGHz_%smW_IF%s_hot.csv' % (device1, device2, self.directory, lofreq, power_s, ifs))    
        df_hot.to_csv(filename)
        
        self.t7.select_Load('cold')
        time.sleep(0.1)
        df_cold = self.sweep_IF_both(vmin=vmin, vmax=vmax, gain_Vs=gain_Vs,
                                     gain_Is=gain_Is, channel=channel1, if_freq=if_freq)
        df_cold.to_csv(filename.replace('hot', 'cold'))

        axIV.plot(df_hot.Vs, (df_hot.IFPower_0 - df_cold.IFPower_0)/1e-6, 's-', label="SIS%s ON IF0" % device1)
        axIV.plot(df_hot.Vs, (df_hot.IFPower_1 - df_cold.IFPower_1)/1e-6, 's-', label="SIS%s ON IF1" % device1)
        plt.draw()
        plt.show()
        plt.pause(0.001)

        
        # Turn 2 device on, other dev max - sweep for both IF powers hot and cold
        ind = 1
        channel1 = channels[ind]
        device1 = sis[ind]
        channel2 = channels[ind-1]
        device2 = sis[ind-1]
        opt_voltage = opt_Vs[ind]
        self._print("Setting device %s to it opt voltage %s mV" % (device1, opt_voltage))
        self.voltage_servo_loop(channel=channel1, device=device1, vsmin=opt_voltage-0.1,
                                vsmax=opt_voltage+0.1)
        self._print("Setting device %s to it max voltage %s mV" % (device2, 25))
        self.t7.set_dac([channel2], set_vbias(25, Rn=40.0), card=self.card)

        #hot then cold
        self.t7.select_Load('hot')
        time.sleep(0.1)
        df_hot = self.sweep_IF_both(vmin=vmin, vmax=vmax, gain_Vs=gain_Vs,
                                    gain_Is=gain_Is, channel=channel1, if_freq=if_freq)
        filename = os.path.join(self.directory, 'sis%s_on_sis%s_max_%s_%sGHz_%smW_IF%s_hot.csv' % (device1, device2, self.directory, lofreq, power_s, ifs))    
        df_hot.to_csv(filename)
        
        self.t7.select_Load('cold')
        time.sleep(0.1)
        df_cold = self.sweep_IF_both(vmin=vmin, vmax=vmax, gain_Vs=gain_Vs,
                                     gain_Is=gain_Is, channel=channel1, if_freq=if_freq)
        df_cold.to_csv(filename.replace('hot', 'cold'))        
        
        axIV.plot(df_hot.Vs, (df_hot.IFPower_0 - df_cold.IFPower_0)/1e-6, 's-', label="SIS%s ON IF0" % device1)
        axIV.plot(df_hot.Vs, (df_hot.IFPower_1 - df_cold.IFPower_1)/1e-6, 's-', label="SIS%s ON IF1" % device1)
        
            
        #axIV.set_xlim(0, 25)
        axIV.set_xlabel('mV')
        #axIV.set_ylim(-10,200)
        axIV.set_ylabel('PH - PC')
        axIV.legend()
        axIV.grid()
        axIV.set_title('Sideband Optimize {:s} {:.0f}GHz'.format(self.directory, lofreq))
        #figIV.show()
        plt.draw()
        plt.show()
        plt.pause(0.001)
        
        figname = os.path.join(self.directory, '{:s}_sideband_test_{:.1f}GHz_{:s}mW_IF{:s}_HminusC.png'.format(self.directory, lofreq, power_s, ifs))
        figIV.savefig(figname, dpi=150)
        self._print("Saving figure for PIV Curve to %s" % figname)

    def dc_lna_drain_sweep(self, channel=0, label='0a',
                           vmin=0, vmax=2.5, step=0.005,
                           timeout=0.010, makeplot=True, save=True,
                           xlim=(0,2.6), ylim=(0,55), Igain=199.272):
        """
        Function to get the IV sweep with the drain voltage for LNA. 
        """
        self._print('Performing LNA IV Sweep on drain voltage and current channel %d label %s' % (channel, label))
        old_Vdrain = self.t7.adc_read(channel, 2, card=self.card)
        if vmin<0:
            vmin=0
            self._print('LNA minimum Vdrain is 0 V')
        if vmax>2.5:
            vmax=2.5
            self._print('LNA maximum Vdrain is 2.5V')
        vlist = numpy.arange(vmin, vmax+step, step)
        lisdic = []
        for Vdrain in vlist:
            dic = {}
            dic['Vdrain'] = Vdrain
            self.t7.set_lna_drain_voltage(channel, voltage=Vdrain, card=self.card)
            time.sleep(timeout)
            Vds = self.t7.adc_read(channel, 2, card=self.card)
            Ids = self.t7.adc_read(channel, 3, card=self.card)*1e3/Igain
            dic['Vds'] = Vds
            dic['Ids'] = Ids
            lisdic.append(dic)
        self.t7.set_lna_drain_voltage(channel, voltage=old_Vdrain, card=self.card)
        time.sleep(timeout)
        read_Vdrain = self.t7.adc_read(channel,2,card=self.card)
        self._print("Setting and reading LNA channel %d to voltage: %.3f" % (channel, read_Vdrain))
        df = pd.DataFrame(lisdic)
        if makeplot:
            figIV, axIV = plt.subplots(1,1,figsize=(8,6))
            axIV.plot(df.Vds, df.Ids, 'o-', label='LNA%s' % label)
            axIV.legend(loc='best')
            axIV.set(xlim=xlim, ylim=ylim, xlabel='Vdrain [V]', ylabel='Idrain [mA]', )
            axIV.grid()
        if save:
            fname = os.path.join(self.directory, 'lnaVdrain%s.csv' % label)
            df.to_csv(fname)
            self._print('Saving DC IV sweep to %s' % fname)
        return df
