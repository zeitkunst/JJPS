#!/usr/bin/env python

from JJPS.Station import Station
configFile = "/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/JJPSConfig.ini"

if __name__ == "__main__":
    station = Station(configFile = configFile)

    # TODO
    # make configurable
    fp = open("/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/currentProcessedProgram", "r")
    currentProgramProcessed = fp.read()
    fp.close()

    currentProgram, nextProgram = station.getCurrentAndNextProgram()

    if (currentProgramProcessed != nextProgram["programRef"]):
        station.processSound()
        fp = open("/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/currentProcessedProgram", "w")
        fp.write(nextProgram["programRef"])
        fp.close()
