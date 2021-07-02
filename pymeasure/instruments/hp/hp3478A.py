#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2021 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import ctypes
import logging
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_discrete_set,strict_range



log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


c_uint8 = ctypes.c_uint8

class Status_bytes(ctypes.Structure):
    """
    Support-Class for the 5 status byte of the HP3478A
    """
    _fields_ = [
        ("byte1",   c_uint8),
        ("byte2",   c_uint8),
        ("byte3",   c_uint8),
        ("byte4",   c_uint8),
        ("byte5",   c_uint8)
    ]

class Status_bits(ctypes.LittleEndianStructure):
    """
    Support-Class with the bit assignments for the 5 status byte of the HP3478A
    """

    _fields_ = [
        #Byte 1: Function, Range and Number of Digits
        ("digits",     c_uint8, 2), # bit 0..1
        ("range",      c_uint8, 3), # bit 2..4
        ("function",   c_uint8, 3), # bit 5..7

        #Byte 2: Status Bits
        ("int_trig",   c_uint8, 1),
        ("auto_range", c_uint8, 1),
        ("auto_zero",  c_uint8, 1),
        ("fifty_hz",   c_uint8, 1),
        ("front_rear", c_uint8, 1),
        ("cal_enable", c_uint8, 1),
        ("ext_trig",   c_uint8, 1),
        ("res1",       c_uint8, 1),

        #Byte 3: Serial Poll Mask (SRQ)
        ("SRQ_data_rdy",         c_uint8, 1),
        ("res2",                 c_uint8, 1),
        ("SRQ_syntax_error",     c_uint8, 1),
        ("SRQ_internal_error",   c_uint8, 1),
        ("SRQ_front_panel",      c_uint8, 1),
        ("SRQ_cal_error",        c_uint8, 1),
        ("res3",                 c_uint8, 1),
        ("SRQ_PON",              c_uint8, 1),

        #Byte 4: Error Information
        ("ERR_cal",        c_uint8, 1),
        ("ERR_RAM",        c_uint8, 1),
        ("ERR_ROM",        c_uint8, 1),
        ("ERR_slope",      c_uint8, 1),
        ("ERR_AD",         c_uint8, 1),
        ("ERR_AD_Link",    c_uint8, 1),
        ("res4",           c_uint8, 1),
        ("res5",           c_uint8, 1),

        #Byte 5: DAC Value
        ("DAC_value",       c_uint8, 8),
    ]
    def __str__(self):
        """
        Returns a pretty formatted (human readable) string showing the status of the instrument

        """
        inv_modes = dict(zip(HP3478A.MODES.values(),HP3478A.MODES.keys()))
        cur_mode = inv_modes["F" + str(self.function)]
        cur_range = list(HP3478A.RANGES[cur_mode].keys())[self.range - 1]
        if cur_range >= 1E6:
            r_str = str(cur_range / 1E6) + ' M'
        elif cur_range >= 1000:
            r_str = str(cur_range / 1000) + ' k'
        elif cur_range <= 1:
            r_str=str(cur_range * 1000) + ' m'
        else:
            r_str=str(cur_range) + ' '
        return (
            "function: {}, range: {}, digits: {}\
                \nStatus:\n  internal | external trigger: {} | {}\n  Auto ranging: {}\n  AutoZero: {}\
                \n  50Hz mode: {}\n  Front/Rear selection: {}\n  Calibration enable: {}\
                \nSerial poll mask (SRQ):\n  SRQ for Data ready: {}\
                \n  SRQ for Syntax error: {}\n  SRQ for Internal error: {}\n  SRQ Front Panel button: {}\
                \n  SRQ for Cal err: {}\n  SQR for Power on: {}\
                \nError information: \n Calibration: {}  RAM: {}  ROM: {}  AD Slope: {} AD: {} AD-Link: {} \
                \nDAC value: {}".format(
                cur_mode, r_str, 6-self.digits, self.int_trig, self.ext_trig, self.auto_range,
                self.auto_zero, self.fifty_hz, self.front_rear , self.cal_enable,
                self.SRQ_data_rdy, self.SRQ_syntax_error, self.SRQ_internal_error, self.SRQ_front_panel, self.SRQ_cal_error, self.SRQ_PON,
                self.ERR_cal, self.ERR_RAM, self.ERR_ROM, self.ERR_slope, self.ERR_AD, self.ERR_AD_Link,
                self.DAC_value)
            )

class Status(ctypes.Union):
    """Union type element for the decoding of the status bit-fields"""
    _fields_ = [
        ("B", Status_bytes),
        ("b", Status_bits)
    ]

# @staticmethod does not work ?!
def get_status(status_bytes, field=None):
    """Method to handle the decoding of the status bytes into something meaningfull..

    :param status_bytes:    list of bytes to be decoded
    :return ret_val:

    """
    ret_val = Status(Status_bytes(*status_bytes))
    if field is None:
        return ret_val.b
    elif field == "SRQ":
        return getattr(ret_val.B, "byte3")
    else:
        return getattr(ret_val.b, field)

def get_mode(status_bytes):
    """Method to decode current mode

    :param status_bytes:   list of bytes to be decoded
    :return cur_mode: string with the current trigger mode
    :rtype cur_mode: str

    """
    cur_stat = Status(Status_bytes(*status_bytes))
    function = cur_stat.b.function
    inv_modes = dict(zip(HP3478A.MODES.values(),HP3478A.MODES.keys()))
    cur_mode = inv_modes["F"+str(function)]
    return cur_mode

def get_range(status_bytes):
    """Method to decode current range

    :param status_bytes:   list of bytes to be decoded
    :return cur_range: string with the current trigger mode
    :rtype cur_range: float

    """
    cur_stat = Status(Status_bytes(*status_bytes))
    function = cur_stat.b.function
    inv_modes = dict(zip(HP3478A.MODES.values(),HP3478A.MODES.keys()))
    cur_mode = inv_modes["F"+str(function)]
    rnge = cur_stat.b.range
    cur_range = list(HP3478A.RANGES[cur_mode].keys())[rnge-1]
    return cur_range

def get_trigger(status_bytes):
    """Method to decode trigger mode
    :param status_bytes:   list of bytes to be decoded
    :return trigger_mode: string with the current trigger mode
    :rtype trigger_mode: str

    """
    cur_stat= Status(Status_bytes(*status_bytes))
    i_trig = cur_stat.b.int_trig
    e_trig = cur_stat.b.ext_trig
    if i_trig == 0:
        if e_trig == 0:
            trigger_mode = "hold"
        else:
            trigger_mode = "external"
    else:
        trigger_mode = "internal"
    return trigger_mode

class HP3478A(Instrument):
    """ Represents the Hewlett Packard 3748A 5 1/2 digit multimeter
    and provides a high-level interface for interacting
    with the instrument.

    As this unit predates SCPI some tricks are required to get this working

    """

    def __init__(self, resourceName, **kwargs):
        super(HP3478A, self).__init__(
            resourceName,
            "Hewlett-Packard HP3478A",
            includeSCPI = False,
            send_end = True,
            read_termination = "\r\n",
            **kwargs
        )

    # Definitions for different specifics of this instrument
    MODES={"DCV": "F1",
           "ACV": "F2",
           "R2W": "F3",
           "R4W": "F4",
           "DCI": "F5",
           "ACI": "F6",
           "Rext": "F7",
           }

    RANGES={"DCV": {3E-2: "R-2", 3E-1: "R-1",3: "R0",30: "R1",300:"R2",
                    "auto": "RA"},
            "ACV": {3E-1: "R-1", 3: "R0",30: "R1" ,300: "R2","auto": "RA"},
            "R2W": {30: "R1", 300: "R2", 3E3: "R3",3E4: "R4",3E5: "R5",
                    3E6: "R6", 3E7: "R7","auto": "RA"},
            "R4W": {30: "R1",300: "R2", 3E3: "R3",3E4: "R4",3E5: "R5",
                    3E6: "R6", 3E7: "R7","auto": "RA"},
            "DCI": {3E-1: "R-1",3: "R0","auto": "RA"},
            "ACI": {3E-1: "R-1",3: "R0","auto": "RA"},
            "Rext": {3E7: "R7","auto": "RA"},
            }

    TRIGGERS={
            "auto": "T1",
            "internal": "T1",
            "external": "T2",
            "single": "T3",
            "hold": "T4",
            "fast": "T5",
            }

    ERRORS={
            1: "Calibration error",
            2: "RAM error",
            4: "ROM error",
            8: "AD slope error",
            16: "AD converter error",
            32: "AD link error",
           }

    active_connectors = Instrument.measurement(
        "B",
        """Return selected connectors ("front"/"back"), based on front-panel selector switch
        """,
        get_process = (lambda x: get_status(x.encode(encoding="ASCII"), "front_rear")),
        values={"back":0, "front":1},
        map_values = True,
        )

    auto_range = Instrument.measurement(
        "B",
        """ Return auto-ranging status, returns False if manual range and True if auto-range active.
        For manual range control the range property can be set
        """,
        get_process = (lambda x: get_status(x.encode(encoding="ASCII"), "auto_range")),
        values={False:0, True:1},
        map_values = True,
        )

    auto_zero = Instrument.control(
        "B",
        "Z%d",
        """ Returns autozero settings on the HP3478, this property can be set 
        (False: disabled, True: enabled) 
        """,
        get_process = (lambda x: get_status(x.encode(encoding="ASCII"), "auto_zero")),
        validator = strict_discrete_set,
        values={False:0, True:1},
        map_values = True,
        )

    cal_enable = Instrument.measurement(
        "B",
        """Return calibration enable switch setting (False: cal disabled, True: cablibration possible),
        based on front-panel selector switch
        """,
        get_process = (lambda x: get_status(x.encode(encoding="ASCII"), "cal_enable")),
        values={False:0, True:1},
        map_values = True,
        )

    def check_errors(self):
        """
        Method to read the error status register

        :return error_status: one byte with the error status register content
        :rtype error_status: int
        """

        if self.error_status != 0:
            log.critical("HP3478A error detected: $s", self.ERRORS[self.error_status] )
        return self.error_status

    error_status = Instrument.measurement(
        "E",
        """Checks the error status register
        """,
        get_process = (lambda x: int(x)),
        )

    disp_reset = Instrument.setting(
        "D%d",
        """Resets the display of the instrument if 1 is written to it.
        """,
        set_process = (lambda x: int(x)),
        validator = strict_discrete_set,
        values = [1],
        )

    #TODO: find a proper validator for the next two methods (without using regex, if possible)
    disp_text = Instrument.setting(
        "D2%s",
        """Displays up to 12 upper-case ASCII characters on the display.
        """,
        set_process = (lambda x: str.upper(x[0:12])),
        )

    disp_text_no_symbol = Instrument.setting(
        "D3%s",
        """Displays up to 12 upper-case ASCII characters on the display and disables all symbols on the display.
        """,
        set_process = (lambda x: str.upper(x[0:12])),
        )

    #TODO: find a good way to cache the latest measurment and use it to incease speed (if actually needed)
    measure_ACI = Instrument.measurement(
        MODES["ACI"],
        """Return the measured value for AC current
        """,
        get_process = (lambda x: float(x)),
        )

    measure_ACV = Instrument.measurement(
        MODES["ACV"],
        """Return the measured value for AC Voltage
        """,
        get_process = (lambda x: float(x)),
        )

    measure_DCI = Instrument.measurement(
        MODES["DCI"],
        """Return the measured value for DC current
        """,
        get_process = (lambda x: float(x)),
        )

    measure_DCV = Instrument.measurement(
        MODES["DCV"],
        """Return the measured value for DC Voltage
        """,
        get_process = (lambda x: float(x)),
        )

    measure_R2W = Instrument.measurement(
        MODES["R2W"],
        """Return the measured value for 2-wire resistance
        """,
        get_process = (lambda x: float(x)),
        )

    measure_R4W = Instrument.measurement(
        MODES["R4W"],
        """Return the measured value for 4-wire resistance
        """,
        get_process = (lambda x: float(x)),
        )

    measure_Rext = Instrument.measurement(
        MODES["Rext"],
        """Return the measured value for extended resistance mode (>30M, 2-wire) resistance
        """,
        get_process = (lambda x: float(x)),
        )

    mode = Instrument.control(
        "B",
        "%s",
        """Return current selected measurment mode, this propery can be set.
        Allowed values are ACI,ACV,DCI,DCV,R2W,R4W,Rext
        """,
        get_process = (lambda x: get_mode(x.encode(encoding="ASCII"))),
        set_process = (lambda x: HP3478A.MODES[x]),
        validator = strict_discrete_set,
        values = MODES,
        )

    range = Instrument.measurement(
        "B",
        """Returns the current measurment range, this property can be set.
        Valid settings are 3*powers of ten (e.g 0.3,3,30)"
        for all valid ranges look at HP3478A.RANGES structure
        """,
        get_process = (lambda x: get_range(x.encode(encoding="ASCII"))),
        )

    @range.setter
    def range(self,value):
        cur_mode = self.mode
        set_range = strict_discrete_set(value, self.RANGES[cur_mode])
        set_range = self.RANGES[cur_mode][value]
        print(set_range)
        self.write(set_range)

    resolution = Instrument.control(
        "B",
        "N%d",
        """Return current selected resolution, this property can be set.
        Allowed values are 3,4 or 5
        """,
        get_process = (lambda x: 6-get_status(x.encode(encoding="ASCII"),"digits")),
        validator = strict_discrete_set,
        values = [3,4,5],
        )

    status = Instrument.measurement(
        "B",
        """Checks the status registers
        """,
        get_process = (lambda x: get_status(x.encode(encoding="ASCII"))),
        )

    SRQ_mask = Instrument.control(
        "B",
        "M%o",
        """Return current SRQ mask, this property can be set,
        
        bit assigment for SQR:
        
            1(dec) - SRQ when Data ready,
            4(dec) - SRQ when Syntax error,
            8(dec) - SRQ when internal error,
            16(dec) - front panel SQR,
            32(dec) - SRQ by invalid calibration,
        
        """,
        get_process = (lambda x: get_status(x.encode(encoding="ASCII"),"SRQ")),
        validator = strict_range,
        values = [0,63],
        )

    trigger = Instrument.control(
        "B",
        "%s",
        """Return current selected trigger mode, this property can be set
        Possibe values are: "auto"/"internal", "external", "hold", "fast"
        """,
        get_process = (lambda x: get_trigger(x.encode(encoding="ASCII"))),
        set_process = (lambda x: HP3478A.TRIGGERS[x]),
        validator = strict_discrete_set,
        values = TRIGGERS,
        )

    #Functions using low-level access via instrument.adapter.connection methods

    def GPIB_trigger(self):
        """
        Initate trigger via low-level GPIB-command (aka GET- group execute trigger)

        """
        self.adapter.connection.assert_trigger()

    def reset(self):
        """
        Initatiates a reset of the HP3478A

        """
        self.adapter.connection.clear()

    def shutdown(self):
        """
        provides a way to gracefully close the connection to the HP3478A

        """
        self.adapter.connection.clear()
        self.adapter.connection.close()
