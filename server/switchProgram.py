#!/usr/bin/env python

from JJPS.Station import Station
configFile = "/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/JJPSConfig.ini"

if __name__ == "__main__":
    station = Station(configFile = configFile)

    # TODO
    # make configurable
    fp = open("/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/currentProgramName", "r")
    currentProgramName = fp.read()
    fp.close()

    currentProgram, nextProgram = station.getCurrentAndNextProgram()

    if (currentProgramName != currentProgram["programRef"]):
        station.switchProgram()
        fp = open("currentProgramName", "w")
        fp.write(currentProgram["programRef"])
        fp.close()