import sys
import u3

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
    def __init__(self, debug=True):
        self.debug = debug
        self.u3 = u3.U3()
        self.configure_u3()

    def configure_u3(self):
        self.config = self.u3.configU3()
        print(self.config)

    def set_frequency(self, frequency):
        send_frequency(self.u3, frequency, debug=self.debug)

    def set_lo_power_voltage(self, voltage):
        dio_volt = voltage + 1.0
        DAC0_VALUE = self.u3.voltageToDACBits(dio_volt,
                                              dacNumber = 0, is16Bits = True)
        self.u3.getFeedback(u3.DAC0_16(Value=DAC0_VALUE))
        
