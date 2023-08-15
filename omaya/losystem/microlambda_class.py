import sys
import u3
from datetime import datetime
import numpy

def freq_word(frequency):
    if frequency < 18:
        return 0x00, 0x00
    if frequency > 26.5:
        return 0xff, 0xff
    step = (26.5 - 18)/(2**16 - 1)
    b = int((frequency - 18.0)/step)
    lsb = b & 0x00ff
    msb = (b &0xff00) >> 8
    return (msb, lsb)

def send_bytes(handle, byte0, byte1, debug=True):
    #data_out = array('B', [0 for i in range(2)])
    data_out = []
    data_out.append(byte0)  # MSB
    data_out.append(byte1) # LSB
    handle.spi(data_out)
    if debug:
        print("Sent %s" % data_out)

def send_frequency(handle, frequency, debug=True):
    msb, lsb = freq_word(frequency)
    send_bytes(handle, msb, lsb, debug=debug)

class MicroLambda(object):
    def __init__(self, debug=True,
                 configU3IO=True, numIterations=1000):
        self.debug = debug
        self.u3 = u3.U3()
        self.configure_u3()
        self.numChannels = 2
        self.numIterations = numIterations
        self.quickSample = 1
        self.longSettling = 0
        self.checkHV()
        if configU3IO:
            self.configIO()

    def checkHV(self):
        # Check if the U3 is an HV
        if self.u3.configU3()['VersionInfo'] & 18 == 18:
            self.isHV = True
        else:
            self.isHV = False
        if self.debug:
            print("Device U3 is HV:%s" % self.isHV)
            
    def configure_u3(self):
        self.config = self.u3.configU3()
        print(self.config)

    def configIO(self):
        FIOEIOAnalog = (2 ** self.numChannels) - 1
        fios = FIOEIOAnalog & 0xFF
        eios = FIOEIOAnalog // 256
        self.u3.configIO(FIOAnalog=fios, EIOAnalog=eios)

        self.u3.getFeedback(u3.PortDirWrite(Direction=[0, 0, 0],
                                             WriteMask=[0, 0, 15]))

    def set_frequency(self, frequency):
        send_frequency(self.u3, frequency, debug=self.debug)

    def set_lo_power_voltage(self, voltage):
        dio_volt = voltage + 1.0
        DAC0_VALUE = self.u3.voltageToDACBits(dio_volt,
                                              dacNumber = 0, is16Bits = True)
        self.u3.getFeedback(u3.DAC0_16(Value=DAC0_VALUE))

    def getVoltages(self, numIterations=None):
        if numIterations is None:
            numIterations = self.numIterations

        self.feedbackArguments = []
        #self.feedbackArguments.append(u3.DAC0_8(Value=125))
        #self.feedbackArguments.append(u3.PortStateRead())

        for i in range(self.numChannels):
            self.feedbackArguments.append(u3.AIN(i, 31,
                                                 QuickSample=self.quickSample,
                                                 LongSettling=self.longSettling))

        self.latestAinValues = numpy.zeros((self.numChannels, numIterations),
                                           dtype='float')
        start = datetime.now()
        # Call Feedback numIterations (default) times
        i = 0
        while i < numIterations:
            results = self.u3.getFeedback(self.feedbackArguments)
            for j in range(self.numChannels):
                # Figure out if the channel is low or high voltage to use the correct calibration
                if self.isHV is True and j < 4:
                    lowVoltage = False
                else:
                    lowVoltage = True
                #self.latestAinValues[j, i] = self.u3.binaryToCalibratedAnalogVoltage(results[2 + j],
                #isLowVoltage=lowVoltage, isSingleEnded=True)
                self.latestAinValues[j, i] = self.u3.binaryToCalibratedAnalogVoltage(results[j],
                                                                              isLowVoltage=lowVoltage, isSingleEnded=True)                
            i += 1
        end = datetime.now()
        delta = end - start
        if self.debug:
            print("Time difference: %g seconds" % (delta.total_seconds()))
        if self.debug:
            for channel in range(self.numChannels):
                print("Channel: %d, voltage: %.6f +/- %.6f" % (channel, self.latestAinValues[channel, :].mean(), self.latestAinValues[channel, :].std()))
        return self.latestAinValues
        
    def close(self):
        self.u3.close()

        
