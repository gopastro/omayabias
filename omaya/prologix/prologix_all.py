import socket
import time
import numpy
import logging

logger = logging.getLogger('Gpib')
logger.name = __name__

units_text = {
    0: 'KRDG?',
    1: 'CRDG?',
    }

class Prologix:
    #def __init__(self, host='172.30.51.89', port=1234,
    def __init__(self, host='172.24.44.80', port=1234,                 
                 pmeter_address=[13, 15], lake_address=12,
                 synth_address=19, lopmeter_address=14,
                 e3631a_address=5,
                 hp83650_address=18,
                 hp3478a_address=23,
                 #second_pmeter_address=13,
                 asksleep=0.01,):
        self.asksleep = asksleep
        self.host = host
        self.port = port
        self.open()
        self.lopmeter_address = lopmeter_address
        #self.n_pmeter = n_pmeter
        self.pmeter_address = pmeter_address
        self.lake_address = lake_address
        self.synth_address = synth_address
        self.e3631a_address = e3631a_address
        self.hp83650_address = hp83650_address
        self.hp3478a_address = hp3478a_address
        # self.second_pmeter_address = second_pmeter_address
        #self.set_gpib_address()
        self.temperature = {}
        #self.idstr = self.idstring()
        #self.idstr = self.idstring()
    
    def open(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        
    def close(self):
        self.sock.close()

    def byteify(self, s):
        return s.encode()

    def write(self, msg):
        """Send something"""
        self.sock.send(self.byteify('%s\r\n' % msg))

    def reset(self):
        "Instrument Reset"
        self.write("*RST")

    def trigger(self):
        "Instrument Trigger. Applies to previously addressed device"
        self.sock.send(self.byteify('++trg\r\n'))

    def set_gpib_address(self, address):
        self.sock.send(self.byteify('++addr %d\r\n' % address))
        # put in auto 0 mode
        self.sock.send(self.byteify('++auto 0\r\n'))

    def idstring(self):
        return "%s" % self.ask("*IDN?")
    
    def ask(self, msg, readlen=128):
        """Send and receive something"""
        self.sock.send(self.byteify('%s\r\n' % msg))
        #self.sock.send(self.byteify('++read eoi\r\n'))
        return self.read(readlen=readlen)
        #ret = self.sock.recv(readlen)
        #return ret.decode().strip()

    def read(self, readlen=128):
        self.sock.send(self.byteify('++read eoi\r\n'))
        ret = self.sock.recv(readlen)
        return ret.decode().strip()

    def get_power(self, mode='LN', IF=0):
        address = self.pmeter_address[IF]
        self.set_gpib_address(address)
        return float(self.ask(mode))            
    
    def get_linear_power(self, IF=0):
        return self.get_power(mode='LN', IF=IF)

    def get_db_power(self, IF=0):
        return self.get_power(mode='LG', IF=IF)

    #def get_2nd_power(self, mode='LN'):
    #    self.set_gpib_address(self.second_pmeter_address)
    #    return float(self.ask(mode))
    
    #def get_2nd_linear_power(self):
    #    return self.get_2nd_power(mode='LN')

    #def get_2nd_db_power(self):
    #    return self.get_2nd_power(mode='LG')    

    
    def get_lo_power(self, mode='LN'):
        self.set_gpib_address(self.lopmeter_address)
        return float(self.ask(mode))
    
    def get_lo_linear_power(self):
        return self.get_lo_power(mode='LN')

    def get_lo_db_power(self):
        return self.get_lo_power(mode='LG')

    def _read_temperature(self, chan=0, text=None):
        self.set_gpib_address(self.lake_address)
        if chan == 0:
            reading = self.ask(text)
            for i, val in enumerate(map(float, reading.split(','))):
                self.temperature[i+1] = val
        else:
            reading = self.ask(text+"%1d" % chan)
            self.temperature[chan] = float(reading)

    def read_temperature(self, chan=0, units=0):
        """Read temperature for given channel and store it in
        self.temperature.
        chan=0 implies all channels, otherwise specify the chan in
        a number between 1 through 8.
        units = 0 - Kelvin (default)
        units = 1 - Celsius"""
        if chan != 0:
            if chan not in range(1,9):
                print("Not valid channel")
                return None
        self._read_temperature(chan=chan, text=units_text[units])
        return self.temperature
    
    def synth_output_on(self):
        self.set_gpib_address(self.synth_address)
        self.write('POWER:STATE ON')

    def synth_output_off(self):
        self.set_gpib_address(self.synth_address)
        self.write('POWER:STATE OFF')        

    def get_freq(self):
        self.set_gpib_address(self.synth_address)
        return float(self.ask('FREQ:CW?'))

    def get_synth_power(self):
        self.set_gpib_address(self.synth_address)
        return float(self.ask('POW?'))

    def set_synth_power(self, synth_power):
        self.set_gpib_address(self.synth_address)
        self.write('POWER %sdBm' % synth_power)

    def set_freq(self, freq):
        """Set CW frequency in Hz"""
        self.set_gpib_address(self.synth_address)
        if freq<1e9:
            fstr = "%s MHz" % (freq/1.e6)
        else:
            fstr = "%s GHz" % (freq/1.e9)
        self.write('FREQ:CW %s' % fstr)

    def set_83650_freq(self, freq):
        """Set CW frequency in Hz"""
        self.set_gpib_address(self.hp83650_address)
        if freq<1e9:
            fstr = "%s MHz" % (freq/1.e6)
        else:
            fstr = "%s GHz" % (freq/1.e9)
        self.write('FREQ:CW %s' % fstr)
        
    def e3631a_output_on(self):
        self.set_gpib_address(self.e3631a_address)
        self.write('OUTPUT:STATE ON')

    def e3631a_output_off(self):
        self.set_gpib_address(self.e3631a_address)
        self.write('OUTPUT:STATE OFF')        

        
    def e3631a_dual_set_voltage(self, voltage):
        """
        account for diode drop of 0.7V
        """
        if voltage < -1.0:
            print("Cannot set less than -1.0 V")
            voltage = -1.0
        if voltage > 1.0:
            print("Cannot set more than 1.0 V")
            voltage = 1.0
        if voltage <= 0.0:
            self.set_gpib_address(self.e3631a_address)
            self.write('APPLY P25V, 24.0, DEF')
            self.set_gpib_address(self.e3631a_address)
            self.write('APPLY P6V, %s, DEF' % abs(voltage))
            #time.sleep(0.050)
            #self.measure_e3631a(chan='P6V')
        else:
            self.set_gpib_address(self.e3631a_address)
            self.write('APPLY P25V, 0.0, DEF')
            self.set_gpib_address(self.e3631a_address)
            self.write('APPLY P6V, %s, DEF' % (voltage))
            #time.sleep(0.050)            
            #self.measure_e3631a(chan='P6V')        
        print("Set E3631A to %s V" % voltage)

    def set_voltage(self, chan='P25V', voltage=None, current_rating=None):
        if chan not in ('P25V', 'N25V', 'P6V'):
            print("Channel should be one of P25V, N25V or P6V")
            return
        if voltage is None:
            voltage = 'DEF' #sets defaults voltage (0.0 V)
        if current_rating is None:
            current_rating = 'DEF'
        self.set_gpib_address(self.e3631a_address)
        self.write('APPLY %s, %s, %s' % (chan, voltage, current_rating))

    def P6V_set_voltage(self, voltage, current_rating=None):
        self.set_voltage(chan='P6V', voltage=voltage,
                         current_rating=current_rating)

    def P25V_set_voltage(self, voltage, current_rating=None):
        self.set_voltage(chan='P25V', voltage=voltage,
                         current_rating=current_rating)

    def N25V_set_voltage(self, voltage, current_rating=None):
        self.set_voltage(chan='N25V', voltage=voltage,
                         current_rating=current_rating)

    def measure_e3631a(self, chan="P25V"):
        if chan not in ("P25V", "N25V", "P6V"):
            print("Wrong channel ", chan)
            return
        self.set_gpib_address(self.e3631a_address)        
        volt = float(self.ask("MEAS:VOLT:DC? %s" % chan))
        self.set_gpib_address(self.e3631a_address)        
        curr = float(self.ask("MEAS:CURR:DC? %s" % chan))
        return (volt, curr)

    def setup_hp3478a_ac(self, nplc=10.0, range=10.0, nrdgs=2, resolution=0.001):
        """Setup for AC operations
        FIXEDZ 1 only for DC
        """
        self.nrdgs = nrdgs
        cmd = 'F2' #AC mode
        cmd += 'R1' #30V range
        cmd += 'Z1'  #autozero On
        cmd += 'N5'  #5digits on
        self.set_gpib_address(self.hp3478a_address)        
        self.write(cmd)
        time.sleep(self.asksleep)

    def take_hp3478a_readings(self, nrdgs=2):
        self.set_gpib_address(self.hp3478a_address)                
        self.write('T3')  #single trigger mode
        time.sleep(self.asksleep)
        volt = numpy.zeros(nrdgs, dtype=float)
        for i in range(nrdgs):
            self.set_gpib_address(self.hp3478a_address)            
            self.trigger()
            time.sleep(self.asksleep)
            self.set_gpib_address(self.hp3478a_address)
            rdg = float(self.read())
            volt[i] = rdg
            logger.debug("%d, %s" % (i, rdg))
        self.set_gpib_address(self.hp3478a_address)            
        self.write('T1')
        time.sleep(self.asksleep)        
        return volt.mean(), volt.std()

    def take_quick_hp3478a_readings(self, nrdgs=2):
        self.set_gpib_address(self.hp3478a_address)                
        self.write('F2R-4Z1N4')
        time.sleep(0.5)
        self.set_gpib_address(self.hp3478a_address)                        
        val = self.read()
        try:
            return float(val)
        except ValueError:
            return 0.0

    
    # def set_ferrite_voltage(self, voltage):
    #     voltage = abs(voltage)
    #     if voltage > 1.0:
    #         voltage = 1.0
    #     self.P6V_set_voltage(voltage)
    
