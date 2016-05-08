#!/usr/bin/python
#
## @file
#
# A serial interface to the W1 Spinning Disk from Yokogawa/Andor.
#
# Jeffrey Moffitt 5/16
#

import sc_library.halExceptions as halExceptions
import serial
import copy
import sc_library.parameters as params

## W1Exception
#
# Spinning disk exception.
#
class W1Exception(halExceptions.HardwareException):
    def __init__(self, message):
        halExceptions.HardwareException.__init__(self, message)

class W1SpinningDisk:

    def __init__(self, com_port, parameters, verbose = False):

        # Create serial port
        try:
            self.com = serial.Serial(port = com_port,
                                     baudrate = 115200,
                                     timeout = 0.1)
        except:
            print "Could not create serial port for spinning disk. Is it connected properly?"
            raise W1Exception("W1 Spinning Disk Initialization Error \n" + " Could not properly initialize com_port: " + str(com_port))

        # Create a local copy of the current W1 configuration
        self.params = {} # Create empty dictionary

        # Record internal verbosity (debug purposes only)
        self.verbose = verbose
        
        # Define error codes
        self.error_codes = {"30005": "Command name error",
                            "30006": "Command argument number error",
                            "30007": "Command argument value error",
                            "30141": "Command argument value error",
                            "30012": "Interlock alarm is on",
                            "30133": "Interlock alarm is on",
                            "30014": "Electricity alarm is on",
                            "30015": "Shutter alarm is on",
                            "30016": "Actuator alarm is on",
                            "30017": "Disk alarm is on",
                            "30018": "Data error alarm is on",
                            "30019": "Other alarm is on",
                            "30021": "Designated system is not defined",
                            "30022": "Designated system does not exist",
                            "30023": "Designated system is not detected",
                            "30031": "Waiting for initialization to complete",
                            "30032": "Under maintenance mode",
                            "30201": "External SYNC signal is under use",
                            "30204": "Disk rotation stopped",
                            "30301": "Shutter error",
                            "30302": "Shutter unopenable error"}

        self.initializeParameters(parameters)

    def cleanup(self):
        self.com.close()

    def initializeParameters(self, parameters):
        # Add spinning disk sub section
        sd_params = parameters.addSubSection("spinning_disk")

        # Add basic parameters
        sd_params.add("bright_field_bypass", params.ParameterSetBoolean("Bypass spinning disk for brightfield mode?",
                                                                        "bright_field_bypass", False))

        sd_params.add("spin_disk", params.ParameterSetBoolean("Spin the disk?",
                                                              "spin_disk", True))

        # Disk properties
        sd_params.add("disk", params.ParameterSetString("Disk pinhole size",
                                                        "disk",
                                                        "50-micron pinholes",
                                                        ["50-micron pinholes", "25-micron pinholes"]))

        max_speed = self.getMaxSpeed()
        sd_params.add("disk_speed", params.ParameterRangeInt("Disk speed (RPM)",
                                                             "disk_speed",
                                                             max_speed, 1, max_speed))

        # Dichroic mirror position
        sd_params.add("dichroic_mirror", params.ParameterRangeInt("Dichroic mirror position (1-3)",
                                                                  "dichroic_mirror",
                                                                  1,1,3))

        # Filter wheel positions
        sd_params.add("filter_wheel_pos1", params.ParameterRangeInt("Camera 1 Filter Wheel Position (1-10)",
                                                                    "filter_wheel_pos1",
                                                                    3,1,10))

        sd_params.add("filter_wheel_pos2", params.ParameterRangeInt("Camera 2 Filter Wheel Position (1-10)",
                                                                    "filter_wheel_pos2",
                                                                    1,1,10))

        # Camera dichroic positions
        sd_params.add("camera_dichroic_mirror", params.ParameterRangeInt("Camera dichroic mirror position (1-3)",
                                                                  "camera_dichroic_mirror",
                                                                  1,1,3))

        # Aperature settings
        sd_params.add("aperature", params.ParameterRangeInt("Aperature value (1-10; small to large)",
                                                            "aperature",
                                                            10,1,10))

        # Run new parameters to configure the spinning disk with these defaults
        self.newParameters(parameters)

    def getMaxSpeed(self):
        [success, value] = self.writeAndReadResponse("MS_MAX,?\r")
        return int(value)
        
    def newParameters(self, parameters):
        p = parameters.get("spinning_disk")

        # Update all parameters of the spinning disk, checking to see if parameters need updated

        # Set bright field bypass
        if not(self.params.get("bright_field_bypass", []) == p.get("bright_field_bypass")):
            if p.get("bright_field_bypass"):
                self.writeAndReadResponse("BF_ON\r")
            else:
                self.writeAndReadResponse("BF_OFF\r")

        # Spin disk
        if not(self.params.get("spin_disk", []) == p.get("spin_disk")):
            if p.get("spin_disk"):
                self.writeAndReadResponse("MS_RUN\r")
            else:
                self.writeAndReadResponse("MS_STOP\r")

        # Disk properties
        if not(self.params.get("disk", []) == p.get("disk")):
            if p.get("disk") == "50-micron pinholes":
                self.writeAndReadResponse("DC_SLCT,1\r")
            elif p.get("disk") == "25-micron pinholes":
                self.writeAndReadResponse("DC_SLCT,2\r")

        if not(self.params.get("disk_speed", []) == p.get("disk_speed")):
            self.writeAndReadResponse("MS,"+str(p.get("disk_speed"))+"\r")

        # Dichroic mirror position
        if not(self.params.get("dichroic_mirror", []) == p.get("dichroic_mirror")):
            self.writeAndReadResponse("DMM_POS,1,"+str(p.get("dichroic_mirror"))+"\r")
        
        # Filter wheel positions (They can be changed together)
        if (not(self.params.get("filter_wheel_pos1",[]) == p.get("filter_wheel_pos1"))) or \
           (not(self.params.get("filter_wheel_pos2",[]) == p.get("filter_wheel_pos2"))):
            self.writeAndReadResponse("FW_POS,0," + str(p.get("filter_wheel_pos1")) + "," + 
                                      str(p.get("filter_wheel_pos2")) + "\r")
                                                                    
        # Camera dichroic position
        if not(self.params.get("camera_dichroic_mirror", []) == p.get("camera_dichroic_mirror")):
            self.writeAndReadResponse("PT_POS,1," + str(p.get("camera_dichroic_mirror")) + "\r")

        # Aperature settings
        if not(self.params.get("aperature", []) == p.get("aperature")):
            self.writeAndReadResponse("AP_WIDTH,1,"+str(p.get("aperature"))+"\r")

        # Make deep copy of the passed parameters so that the spinning disk remembers its current configuration
        self.params = copy.deepcopy(p)

    def writeAndReadResponse(self, message):
        if self.verbose:
            print "Writing: " + message
        
        self.com.write(message)
        response = self.com.readline()

        if self.verbose:
            print "Response: " + response

        # Handle empty response
        if len(response) == 0:
            return [False, ""]

        # Split response and look for proper acknowledge
        try:
            [value, acknow] = response.split(":")
        except:
            print response
        
        # Handle error codes
        if acknow == "N\r":
            error_message = self.error_codes.get(value, "Unknown error")

            raise W1Exception("W1 Error " + value + ": " + error_message)

        else:
            return [True, value]


#
# The MIT License
#
# Copyright (c) 2012 Zhuang Lab, Harvard University
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
