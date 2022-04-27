"""
An overall class to talk to the
Labjack T7 device
"""
from labjack import ljm
import time
import numpy as np
import datetime
import os
import logging

SPI_DEVICES = {
    'MixerDAC0' : [0,0,0],
    'MixerDAC1': [1,0,0],
    'LoopControl': [0,1,0],
    'SyncLoad': [1,1,0],
    'LNADAC': [0,0,1],
    'MuxSPI': [1,0,1],
    'ADC': [0,1,1],
    'BoardID': [1,1,1],
}

ADC_READ = {
    'MixerVsense' : [0],
    'MixerIsense': [1],
    'LNAVsense': [0,1,0],
    'SyncLoad': [1,1,0],
    'LNADAC': [0,0,1],
    'MuxSPI': [1,0,1],
    'ADC': [0,1,1],
    'BoardID': [1,1,1],
}

DAC_SOFTWARE_LDAC_MODE = 0x02
DAC_UPDATE_ONE_CHANNEL_MODE = 0x01
DAC_WRITE_ONE_CHANNEL_MODE = 0x00


SPI_DIONUM_CONF = {
    'spi_mosi': 18,
    'spi_miso': 19,
    'spi_clk': 16,
    'spi_cs': 17,
    'spi_sel_0': 8,
    'spi_sel_1': 9,
    'spi_sel_2': 10,
    'spi_card_0': 13,
    'spi_card_1': 12,
    'spi_card_2': 11,
    'spi_card_3': 14,
    'reset': 15,
    }

SPI_DIONUM_CONF_OLD = {
    'spi_mosi': 2,
    'spi_miso': 3,
    'spi_clk': 0,
    'spi_cs': 1,
    'spi_sel_0': 16,
    'spi_sel_1': 17,
    'spi_sel_2': 18,
    'spi_card_0': 'NA',
    'spi_card_1': 'NA',
    'spi_card_2': 8,
    'spi_card_3': 'NA',
    'reset': 'NA',
    }




class LabJackT7(object):
    def __init__(self, debug=True, oldBoard=True):
        self.debug = debug
        self.handle = ljm.openS("ANY", "ANY", "ANY")
        self.device = [0,0,0]
        info = ljm.getHandleInfo(self.handle)
        if debug:
            print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
                  "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
                  (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
        if oldBoard:
            self.spi_dionums = SPI_DIONUM_CONF_OLD
        else:
            self.spi_dionums = SPI_DIONUM_CONF
            self.reset()
        self.setup_SPI()
        self.scanRate = 1200 # for AIN0/AIN1 sampling
        
    def reset(self):
        ljm.eWriteName(self.handle, 'DIO'+ str(self.spi_dionums['reset']), 1)
            

    def _print(self, msg, loglevel=logging.INFO, ):
        if self.debug:
            print(msg)
        logging.log(level=loglevel, msg=msg)

    def setup_motor(self, state, debug=False):
        ljm.eWriteName(self.handle, "FIO5", 1) # Enable
        print("Enabling the motor")
        ljm.eWriteName(self.handle, "FIO6", 0) # Input A
        print("Motor on Home")
        HLFBstate = ljm.eReadName(self.handle, "FIO7") # HLFB
        print("Reading HLFB: %0.0f" %(HLFBstate))

    def select_Load(self, load):
        if load == "hot":
            ljm.eWriteName(self.handle, "FIO6", 0) # Input A
            HLFBstate = ljm.eReadName(self.handle, "FIO7")
            while(HLFBstate):
                  HLFBstate = ljm.eReadName(self.handle, "FIO7")
            print("Hot load on")
            #return 'Hot'                 
        elif load == "cold":
            ljm.eWriteName(self.handle, "FIO6", 1) # Input A
            print("Cold load ON")
        else:
            print("wrong command: choose either 'cold' or 'hot'")

    def shutdown_motor(self):
        ljm.eWriteName(self.handle, "FIO6", 0) # Input A
        print("Hot load on(Safe position)")
        time.sleep(1.500)
        ljm.eWriteName(self.handle, "FIO5", 0) # Enable
        print("Disabling the motor")        

        
    def setup_SPI(self, debug=True,):
        #Set up SPI DIO lines on T7
        ljm.eWriteName(self.handle, "SPI_CLK_DIONUM", self.spi_dionums['spi_clk'])  # CLK is FIO0
        ljm.eWriteName(self.handle, "SPI_CS_DIONUM", self.spi_dionums['spi_cs'])  # CS is FIO1
        ljm.eWriteName(self.handle, "SPI_MOSI_DIONUM", self.spi_dionums['spi_mosi'])  # MOSI is FIO2
        ljm.eWriteName(self.handle, "SPI_MISO_DIONUM", self.spi_dionums['spi_miso'])  # MISO is FIO3

        # Selecting Mode CPHA=0 (bit 0), CPOL=0 (bit 1)
        ljm.eWriteName(self.handle, "SPI_MODE", 0)

        # Speed Throttle:
        # Valid speed throttle values are 1 to 65536 where 0 = 65536.
        # Configuring Max. Speed (~800 kHz) = 0
        ljm.eWriteName(self.handle, "SPI_SPEED_THROTTLE", 0) #65500)

        
        # SPI_OPTIONS:
        # bit 0:
        #     0 = Active low clock select enabled
        #     1 = Active low clock select disabled.
        # bit 1:
        #     0 = DIO directions are automatically changed
        #     1 = DIO directions are not automatically changed.
        # Bit 2: 0 = Transmit data MSB first, 1 = LSB first
        # bits 2-3: Reserved
        # bits 4-7: Number of bits in the last byte. 0 = 8.
        # bits 8-15: Reserved
        ljm.eWriteName(self.handle, "SPI_OPTIONS", 0)

        # Read back and display the SPI Configuration
        aNames = ["SPI_CS_DIONUM", "SPI_CLK_DIONUM", "SPI_MISO_DIONUM",
                  "SPI_MOSI_DIONUM", "SPI_MODE", "SPI_SPEED_THROTTLE",
                  "SPI_OPTIONS"]
        aValues = [0]*len(aNames)
        numFrames = len(aNames)
        aValues = ljm.eReadNames(self.handle, numFrames, aNames)

        if(debug):
            print("\nSPI Configuration:")
            for i in range(numFrames):
                print("  %s = %0.0f" % (aNames[i],  aValues[i]))

    def spi_mode(self, mode):
        # Selecting Mode CPHA=0 (bit 0), CPOL=0 (bit 1)
        ljm.eWriteName(self.handle, "SPI_MODE", mode)

    def spi_numbytes(self, numBytes):
        """Sets the size of SPI Tx/Rx registers on labjack"""
        ljm.eWriteName(self.handle, "SPI_NUM_BYTES", numBytes)
        
    def device_select(self, device):
        """Selects SPI controlled device on Mixer Bias Board
        # 'Device' : character string
        # 
        # 'MixerDAC0' : [0,0,0] 
        # 'MixerDAC1': [1,0,0]
        # 'LoopControl': [0,1,0]
        # 'SyncLoad': [1,1,0]
        # 'LNADAC': [0,0,1]
        # 'MuxSPI': [1,0,1]
        # 'ADC': [0,1,1]
        # 'BoardID': [1,1,1]
        """
        addr = SPI_DEVICES.get(device, None)
        if addr is not None:
            for bit in range(3):
                # dio_name = 'CIO%i'%bit
                dio_name = 'DIO'+ str(self.spi_dionums['spi_sel_%i'%bit])
                ljm.eWriteName(self.handle, dio_name, addr[bit])
            print("Selecting SPI device %s: [%i, %i, %i]" %(device, addr[0], addr[1], addr[2]))

    def card_select(self, card=0): 
        """Selects which Mixer Bias Board (set low)
        TODO: Need to also deselect other cards in this process
        """
        card_name = 'DIO'+str(self.spi_dionums['spi_card_%i'%card])
        ljm.eWriteName(self.handle, card_name, 0)


    def _spi_go(self):
        ljm.eWriteName(self.handle, "SPI_GO", 1)  # Do the SPI communications
        print("SPI GO")
        
    def _spi_write_array(self, array):
        print("Writing array %s" % array)
        ljm.eWriteNameByteArray(self.handle, "SPI_DATA_TX",
                                len(array), array)
        self._spi_go()

    def _spi_read_array(self, numBytes):
        dataRead = ljm.eReadNameByteArray(self.handle, "SPI_DATA_RX",
                                          numBytes)
        self._spi_go()
        return dataRead

    def _set_pca_in(self):
        """
        Set PCA9502 to all inputs
        """
        self.spi_numbytes(2)
        #
        # Configure all GPIO pins on PCA to INPUT (0)
        # 'IODir' (address: 0xA)
        # Number becomes 0x5 because 4 address bits are split into 2 nibbles (annoying)
        #
        dataWrite = []
        dataWrite.append(0x50)
        dataWrite.append(0x00)
        self._spi_write_array(dataWrite)

    def _set_pca_out(self):
        """
        Set PCA9502 to all outputs
        """
        self.spi_numbytes(2)
        #
        # Configure all GPIO pins on PCA to INPUT (0)
        # 'IODir' (address: 0xA)
        # Number becomes 0x5 because 4 address bits are split into 2 nibbles (annoying)
        #
        dataWrite = []
        dataWrite.append(0x50)
        dataWrite.append(0xFF)
        self._spi_write_array(dataWrite)

    def _get_pca_iodir(self):
        """
        Get PCA9502 IODdir
        """
        self.spi_numbytes(2)
        dataWrite = []
        dataWrite.append(0xD0)
        dataWrite.append(0x00)
        self._spi_write_array(dataWrite)
        return self._spi_read_array(2)

    def _load_pca_output(self, byte):
        self.spi_numbytes(2)
        dataWrite = []
        dataWrite.append(0x58)
        dataWrite.append(byte)
        self._spi_write_array(dataWrite)
        
    def _read_pca(self):
        self.spi_numbytes(2)
        dataWrite = []
        dataWrite.append(0xD8)
        dataWrite.append(0x00)
        self._spi_write_array(dataWrite)
        return self._spi_read_array(2)
    
    def get_boardID(self, card=0):
        self.device_select('BoardID')
        self.card_select(card)
        self._set_pca_in()
        dataRead = self._read_pca()
        print("BoardID: 0x%0x" % dataRead[1])
        return dataRead[1]
        
    def set_mixer_loop_control(self, channel=0, loop_control='Open', card=0):
        """
        deprecated. Do not use
        """
        self.device_select('LoopControl')
        self.card_select(card)
        self._set_pca_out()
        if loop_control == 'Open':
            byte = 0x00
        else:
            byte = 0xff
        self._load_pca_output(byte)
        #self.device_select('LoopControl')
        #self.card_select()        
        #print(self._read_pca())
        # Pull Sync Load 2 low and then High leaving other
        # channels of Mux_SPI PCA9502 alone
        self.device_select('MuxSPI')
        self.card_select(card)
        self._set_pca_out()
        byte = 0x7f & channel
        self._load_pca_output(byte)
        #time.sleep(0.010)
        #byte = 0xff & channel
        byte = 0x80
        self._load_pca_output(byte)
        #time.sleep(0.010)
        self._load_pca_output(0x00)
        #self._spi_go()
        #self.device_select('MixerDAC0')
        self._spi_go()
        #self._load_pca_output(byte)

    def adc_wake_up_ref(self, card=0):
        """
        Sets Max1168 ADC to wake up with
        references on
        """
        self.device_select('ADC')
        self.card_select(card)
        self.spi_numbytes(3)
        # 0x41 - selects channel 2 (0x4)
        # and selects internal clock and internal reference
        # and single channel mode
        self._spi_write_array([0x41, 0x00, 0x00])
        dataRead = self._spi_read_array(3)
        return dataRead

    def adc_read(self, channel=0, read_in=0, timeout=0.010, card=0, debug=False):
        """
        UPDATE: channel is the mixer# while read_in is the type 
        of reading.

        Bias_V: read_in=0 #V_sense
        Bias_I: read_in=1 #I_sense
        LNA_V:  read_in=2 
        LNA_I:  read_in=3
        MAG_V:  read_in=4
        MAG_I:  read_in=5
        2V_ref: read_in=6
        ADC_IN: read_in=7
        """
        #select channel
        self.set_mux(channel, card=card)
	#select ADC
        self.device_select('ADC')
        self.card_select(card)
        self.spi_numbytes(3)
        # 0x41 - selects channel 2 (0x4)
        # and selects internal clock and internal reference
        # and single channel mode
        first_byte = ((read_in << 5) & 0xE0) | (0x01)
        self._spi_write_array([first_byte, 0x00, 0x00])
        time.sleep(timeout)
        dataRead = self._spi_read_array(3)
        print(dataRead)
        ## construct as 16 bit number, ignore last 2 bits
        ## and shift up by 3
        counts = (((dataRead[1] << 8) + dataRead[2]) & 0xffffc) << 3
        print("Counts: %d" % counts)
        #counts = (dataRead[1] << 8) + dataRead[2]
        voltage = (counts/float(2**16)) * 4.05
        print("Voltage = %.3f" % voltage)
        if debug:
            return dataRead, counts, voltage
        else:
            return voltage
    
    def set_mux(self, channel=0, card=0):
        """
        Uses MUX_SPI to select the PCA9502 (U79)
        associated with setting MUX_A0, MUX_A1, and MUX_A2
        address pins to select one of 8 channels.
        The 9502 (chip U79) has 8 GPIO channels, 
        first 3 of which is used to select MUX_A0, MUX_A1, and MUX_A2.
        GPIO7 is used to address Sync LOAD 2 which is used 
        to latch the Mixer Loop Control. 
        """
        self.device_select('MuxSPI')
        self.card_select(card)
        self._set_pca_out()
        self._load_pca_output(channel & 0x07)

    def dac_reset_and_ldac(self, card=0):
        self.device_select('MixerDAC0')
        self.card_select(card)
        self.spi_numbytes(4)
        # clear to mid-scale
        self._spi_write_array([0x05, 0x00, 0x00, 0x01])
        # set to S/w LDAC register (ignore LDAC pin) for all channels
        self._spi_write_array([0x06, 0x00, 0x00, 0x0F])

        self.device_select('MixerDAC1')
        self.card_select(card)
        self.spi_numbytes(4)
        # clear to mid-scale
        self._spi_write_array([0x05, 0x00, 0x00, 0x01])
        # set to LDAC register for all channels
        self._spi_write_array([0x06, 0x00, 0x00, 0x0F])        
        
    def set_dac(self, channel, voltage_bytes=[0x80, 0x00], card=0):
        """ Sets mixer DAC
        """
        #voltage_bytes = self.dac_DIN(voltage)
        if type(channel)==int: 
            if channel < 4:
                self.device_select('MixerDAC0')
                channel_address = channel
            else:
                self.device_select('MixerDAC1')
                channel_address = channel % 4
            self.card_select(card)
            #first_byte = DAC_WRITE_ONE_CHANNEL_MODE
            first_byte = DAC_SOFTWARE_LDAC_MODE
            second_byte = (channel_address << 4) | (0x0f & ((voltage_bytes[0] & 0xF0) >> 4))
            third_byte = ((voltage_bytes[0] & 0x0f) << 4) | (0x0f & ((voltage_bytes[1] & 0xf0) >> 4))
            fourth_byte = ((voltage_bytes[1] & 0x0f) << 4) & 0xf0
            self.spi_numbytes(4)
            self._spi_write_array([first_byte, second_byte, third_byte, fourth_byte])
            print("Wrote %s" % (["0x%02x" % byte for byte in [first_byte, second_byte, third_byte, fourth_byte]]))
        elif type(channel)==list:
            for chan in channel:
                if chan < 4:
                    self.device_select('MixerDAC0')
                    channel_address = chan
                else:
                    self.device_select('MixerDAC1')
                    channel_address = chan % 4
                self.card_select(card)
                #first_byte = DAC_WRITE_ONE_CHANNEL_MODE
                first_byte = DAC_SOFTWARE_LDAC_MODE
                second_byte = (channel_address << 4) | (0x0f & ((voltage_bytes[0] & 0xF0) >> 4))
                third_byte = ((voltage_bytes[0] & 0x0f) << 4) | (0x0f & ((voltage_bytes[1] & 0xf0) >> 4))
                fourth_byte = ((voltage_bytes[1] & 0x0f) << 4) & 0xf0
                self.spi_numbytes(4)
                self._spi_write_array([first_byte, second_byte, third_byte, fourth_byte])
                print("Wrote %s" % (["0x%02x" % byte for byte in [first_byte, second_byte, third_byte, fourth_byte]]))

        # first_byte = DAC_UPDATE_ONE_CHANNEL_MODE
        # second_byte = (channel_address << 4) | (0x0f & ((voltage_bytes[0] & 0xF0) >> 4))
        # third_byte = ((voltage_bytes[0] & 0x0f) << 4) | (0x0f & ((voltage_bytes[1] & 0xf0) >> 4))
        # fourth_byte = ((voltage_bytes[1] & 0x0f) << 4) & 0xf0
        # self.spi_numbytes(4)
        # self._spi_write_array([first_byte, second_byte, third_byte, fourth_byte])
        # print("Wrote %s" % (["0x%02x" % byte for byte in [first_byte, second_byte, third_byte, fourth_byte]]))        

    
    def sweep_dac(self, channel, vmax=[0xff, 0xff], vmin=[0x00,0x00], timeout = 0.010, npoints=100, card=0):
        sweepV = np.linspace((vmin[0]<<8|vmin[1]), (vmax[0]<<8|vmax[1]), npoints, dtype=int)
        v_list = []
        for v in sweepV:
            voltage_bytes = [v >> 8 , v & 0xFF]
            self.set_dac(channel, voltage_bytes, card=card)
            time.sleep(timeout)
            voltage = self.adc_read(channel, read_in=0, card=card)
            current = self.adc_read(channel, read_in=1, card=card)
            v_list.append((v,voltage,current))
        return v_list
    
    def sweep_dac2(self, channel, vmax=[0xff, 0xff], vmin=[0x00,0x00], timeout = 0.010, npoints=100, card=0):
        #let us measure and input the voltage from multimeter.
        sweepV = np.linspace((vmin[0]<<8|vmin[1]), (vmax[0]<<8|vmax[1]), npoints, dtype=int)
        v_list = []
        for v in sweepV:
            voltage_bytes = [v >> 8 , v & 0xFF]
            self.set_dac(channel, voltage_bytes, card=card)
            time.sleep(timeout)
            voltage_adc = self.adc_read(channel, read_in=0, card=card)
            current_adc = self.adc_read(channel, read_in=1, card=card)
            voltage_manual = input()
            v_list.append((v,voltage_manual,voltage_adc,current_adc))
        v_list = np.array(v_list)
        v_list[:,0] = (v_list[:,0]/2**16)*4.05
        return v_list
    
    def start_up(self, channel=0, loop_control='Close', card=0):
        self.get_boardID(card)
        self.set_mux(card=card)
        if type(channel)==int:
            self.set_mixer_loop_control(channel=channel, loop_control=loop_control, card=card)
        elif type(channel)==list:
            for chan in channel:
                self.set_mixer_loop_control(channel=chan, loop_control=loop_control, card=card)
        self.adc_wake_up_ref(card=card)
        self.dac_reset_and_ldac(card=card)

    def dac_DIN(self, voltage, ref=4.05, nbits=16):
        # convert voltage value to hex value
        v = round((voltage/ref)*2**nbits)
        if v<0:
            v = 0
        elif v >= 65536:
            v = 65536-1
        voltage_bytes = [v >> 8 , v & 0xFF]
        return voltage_bytes

    def setup_diff(self, AIN_pos=0, res=0, rang=0, stream=False, buff=0):
        """
        AIN_pos is the positive analog input AIN+. It should be even.
        It needs to be an even number and its negative number will be +1. 
        """
        # validate inputs
        if AIN_pos%2 != 0:
            print('AIN_pos needs to be an even number between 0 and 12')
            return
        if (res<0 or res>8):
            print('Resolution needs to be between 0 and 8')
            return
        if rang not in (10, 1, 0.1, 0.01, 0):
            print('Range needs to be 10, 1, 0.1, 0.01 or 0.')
            return
        if stream:
            #TODO: set streaming configuration
            # Ensure triggered stream is disabled.
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

            # Enabling internally-clocked stream.
            ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

            # Set stream resolution
            res_handle = 'STREAM_RESOLUTION_INDEX'
            ljm.eWriteName(self.handle, res_handle, res)
            
            # Set buffer size. Default 0 is 4096(=2**12). Needs to be a power of 2.
            # Max is 32768(=2**15).
            buff_handle = 'STREAM_BUFFER_SIZE_BYTES'
            ljm.eWriteName(self.handle, buff_handle, buff)
            
        # set the negative counterpart
        negCH_handle = 'AIN{}_NEGATIVE_CH'.format(AIN_pos)
        posCH_handle = 'AIN{}'.format(AIN_pos)
        ljm.eWriteName(self.handle, negCH_handle , AIN_pos+1)

        # set the resolution. Default 0 set resolution to 8 for T7.
        res_handle = 'AIN{}_RESOLUTION_INDEX'.format(AIN_pos)
        ljm.eWriteName(self.handle, res_handle, res)

        # set the range. Default 0 is gain of 1 so output set range of +-10V.
        # other values are 10, 1, 0.1, 0.01 which set to their respective +- volts
        range_handle = 'AIN{}_RANGE'.format(AIN_pos)
        ljm.eWriteName(self.handle, range_handle, rang)
        

    def read_diff_volts(self, AIN_pos):
        # function use for reading differential input voltage.
        # Use for measure differential output of temperature sensor
        read = ljm.eReadName(self.handle, "AIN{}".format(AIN_pos))
        return read

    def read_diff_binary(self, AIN_pos):
        # Reads differential input voltage in binary
        b_read = ljm.eReadName(self.handle, 'AIN{}_BINARY'.format(AIN_pos))
        # b_read = int(b_read // 2**8) # Converts 24-bit output to 16-bit number
        # d_read = int(b_read,2)
        return b_read

    def start_stream_diff_volts(self, AIN_list=[0], scanRate=100,
                                MAX_REQUESTS=25, directory=None):
        numAddresses = len(AIN_list)
        aScanListNames = []
        for i in AIN_list:
            aScanListNames.append('AIN{}'.format(i))
        aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
        # scanRate = 100
        scansPerRead = int(scanRate)
        
        scanRate = ljm.eStreamStart(self.handle, scansPerRead, numAddresses, aScanList, scanRate)
        print('Stream started with scan rate of {:0f} Hz'.format(scanRate))

        # MAX_REQUESTS = 10
        i = 1
        print("\nPerforming %i stream reads." % MAX_REQUESTS)
        start = datetime.datetime.now()
        totScans = 0
        totSkip = 0  # Total skipped samples

        # open file to save data
        if directory is None:
            directory = '{}'.format(start.strftime('%b%d_%Y'))
                                         
        if not os.path.exists(directory):
            self._print("making directory %s" % directory)
            os.makedirs(directory)
        
        filename = '{}/stream_AIN_{}.txt'.format(directory,
                                                 start.strftime('%Y%b%d_%H%M'))
        data_file = open(filename,'w')
        
        while i <= MAX_REQUESTS:
            # TODO: add a timestamp to each measurement
            ret = ljm.eStreamRead(self.handle)

            aData = ret[0]
            scans = len(aData) / numAddresses
            totScans += scans

            # Count the skipped samples which are indicated by -9999 values. Missed
            # samples occur after a device's stream buffer overflows and are
            # reported after auto-recover mode ends.
            curSkip = aData.count(-9999.0)
            totSkip += curSkip

            #write data into file
            data_file.write(str(aData)[1:-1]+', ')
            
            print("\neStreamRead %i" % i)
            ainStr = ''
            for j in range(0, numAddresses):
              ainStr += "%s = %0.5f, " % (aScanListNames[j], aData[j])
              self._print("  1st scan out of %i: %s" % (scans, ainStr))
              self._print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
                    "%i" % (curSkip/numAddresses, ret[1], ret[2]))
            i += 1

        end = datetime.datetime.now()
        # close the file
        data_file.close()
        self._print("\nTotal scans = %i" % (totScans))
        tt = (end - start).seconds + float((end - start).microseconds) / 1000000
        self._print("Time taken = %f seconds" % (tt))
        self._print("LJM Scan Rate = %f scans/second" % (scanRate))
        self._print("Timed Scan Rate = %f scans/second" % (totScans / tt))
        self._print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses / tt))
        self._print("Skipped scans = %0.0f" % (totSkip / numAddresses))

        self._print('Stop Stream')
        ljm.eStreamStop(self.handle)
        self._print('Data was saved in {}'.format(filename))
        

        
    def setup_AIN0(self):
        names = ["AIN0_NEGATIVE_CH", "AIN0_RANGE", "AIN0_RESOLUTION_INDEX", "AIN0_SETTLING_US"]
        aValues = [199, 1, 0, 0]
        numFrames = len(names)
        ljm.eWriteNames(self.handle, numFrames, names, aValues)
        print("\nSet configuration:")
        for i in range(numFrames):
            print("    %s : %f" % (names[i], aValues[i]))

    def read_AIN0(self):
        # Setup and call eReadName to read AIN0 from the LabJack.
        name = "AIN0"
        result = ljm.eReadName(self.handle, name)
        
        print("\n%s reading : %f V" % (name, result))
        return result


    def read_AIN1(self):
        # Setup and call eReadName to read AIN0 from the LabJack.
        name = "AIN1"
        result = ljm.eReadName(self.handle, name)
        
        print("\n%s reading : %f V" % (name, result))
        return result

    def stream_adcs(self, max_requests=1):
        aScanListNames = ["AIN0", "AIN1"]  # Scan list names to stream
        numAddresses = len(aScanListNames)
        aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
        scanRate = self.scanRate
        scansPerRead = int(scanRate / 2)

        # Ensure triggered stream is disabled.
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

        # Enabling internally-clocked stream.
        ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

        # All negative channels are single-ended, AIN0 and AIN1 ranges are
        # +/-10 V, stream settling is 0 (default) and stream resolution index
        # is 0 (default).
        aNames = ["AIN_ALL_NEGATIVE_CH", "AIN0_RANGE", "AIN1_RANGE",
                  "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
        aValues = [ljm.constants.GND, 10.0, 10.0, 0, 0]
        
        # Write the analog inputs' negative channels (when applicable), ranges,
        # stream settling time and stream resolution configuration.
        numFrames = len(aNames)
        ljm.eWriteNames(self.handle, numFrames, aNames, aValues)

        # Configure and start stream
        scanRate = ljm.eStreamStart(self.handle, scansPerRead, numAddresses, aScanList, scanRate)
        print("\nStream started with a scan rate of %0.0f Hz." % scanRate)

        print("\nPerforming %i stream reads." % max_requests)
        start = datetime.datetime.now()
        totScans = 0
        totSkip = 0  # Total skipped samples

        i = 1
        while i <= max_requests:
            ret = ljm.eStreamRead(self.handle)
            
            aData = ret[0]
            #json.dump(aData, open('jnk.dat', 'w'))
            #print(len(aData), aData)
            scans = len(aData) / numAddresses
            totScans += scans
        
            # Count the skipped samples which are indicated by -9999 values. Missed
            # samples occur after a device's stream buffer overflows and are
            # reported after auto-recover mode ends.
            curSkip = aData.count(-9999.0)
            totSkip += curSkip

            print("\neStreamRead %i" % i)
            ainStr = ""
            for j in range(0, numAddresses):
                ainStr += "%s = %0.5f, " % (aScanListNames[j], aData[j])
            print("  1st scan out of %i: %s" % (scans, ainStr))
            print("  Scans Skipped = %0.0f, Scan Backlogs: Device = %i, LJM = "
                  "%i" % (curSkip/numAddresses, ret[1], ret[2]))
            i += 1

        end = datetime.datetime.now()

        print("\nTotal scans = %i" % (totScans))
        tt = (end - start).seconds + float((end - start).microseconds) / 1000000
        print("Time taken = %f seconds" % (tt))
        print("LJM Scan Rate = %f scans/second" % (scanRate))
        print("Timed Scan Rate = %f scans/second" % (totScans / tt))
        print("Timed Sample Rate = %f samples/second" % (totScans * numAddresses / tt))
        print("Skipped scans = %0.0f" % (totSkip / numAddresses))
        ain0 = np.array(aData[0::2])
        ain1 = np.array(aData[1::2])
        kernel_size = 40
        kernel = np.ones(kernel_size) / kernel_size
        ain0_con = np.convolve(ain0, kernel, mode='valid')
        ain1_con = np.convolve(ain1, kernel, mode='valid')
        ljm.eStreamStop(self.handle)
        return ain0_con.mean(), ain1_con.mean()

    def power_up_lna(self,card=0, channel=[0,1]):
        '''Setup for lna dac
        '''
        LNA_DAC_POWER_CTRL = 0x08
        self.device_select('LNADAC')
        self.card_select(card)
        self.spi_numbytes(4)
        if type(channel)==list:
            fourth_byte = sum([2**chan for chan in channel])
        elif type(channel) == int:
            fourth_byte = 2**channel
        self._spi_write_array([LNA_DAC_POWER_CTRL, 0x00, 0x00, fourth_byte])

    def power_down_lna(self,card=0, channel=[0,1]):
        '''Setup for lna dac
        '''
        LNA_DAC_POWER_CTRL = 0x08
        self.device_select('LNADAC')
        self.card_select(card)
        self.spi_numbytes(4)
        if type(channel)==list:
            fourth_byte = sum([2**chan for chan in channel])
        elif type(channel) == int:
            fourth_byte = 2**channel
        self._spi_write_array([LNA_DAC_POWER_CTRL, 0x00, 0x03, fourth_byte])

        
    def set_lna_drain_voltage(self, channel, voltage=0.0, card=0):
        """ Sets lna DAC
        """
        #LNA_DAC_WRITE_ONE_CHANNEL = 0X00
        #LNA_DAC_UPDATE_ONE_CHANNEL = 0X01
        LNA_DAC_WRITE_ONE_UPDATE_ONE = 0X03
        #LNA_DAC_WRITE_ONE_UPDATE_ALL = 0X02
        
        voltage_bytes = self.dac_DIN(voltage, ref=2.5, nbits=16)
        
        if type(channel)==int: 
            self.device_select('LNADAC')
            channel_address = channel
            self.card_select(card)
            first_byte = LNA_DAC_WRITE_ONE_UPDATE_ONE
            second_byte = ( (channel_address << 4) | (voltage_bytes[0] >> 4) )
            third_byte = (((voltage_bytes[0] & 0x0f) << 4) | (voltage_bytes[1] >> 4))
            fourth_byte = ((voltage_bytes[1] & 0x0f) << 4)
            self.spi_numbytes(4)
            self._spi_write_array([first_byte, second_byte, third_byte, fourth_byte])
            print("Wrote %s" % (["0x%02x" % byte for byte in [first_byte, second_byte, third_byte, fourth_byte]]))
        elif type(channel)==list:
            for chan in channel:
                self.device_select('LNADAC')
                channel_address = chan
                self.card_select(card)
                first_byte = LNA_DAC_WRITE_ONE_UPDATE_ONE
                second_byte = ( (channel_address << 4) | (voltage_bytes[0] >> 4) )
                third_byte = (((voltage_bytes[0] & 0x0f) << 4) | (voltage_bytes[1] >> 4))
                fourth_byte = ((voltage_bytes[1] & 0x0f) << 4)
                self.spi_numbytes(4)
                self._spi_write_array([first_byte, second_byte, third_byte, fourth_byte])
                print("Wrote %s" % (["0x%02x" % byte for byte in [first_byte, second_byte, third_byte, fourth_byte]]))
