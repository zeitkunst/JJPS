#!/usr/bin/env python

from JJPS.Station import Station
configFile = "/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/JJPSConfig.ini"

if __name__ == "__main__":
    station = Station(configFile = configFile)

    # TODO
    # make configurable
    #fp = open("/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/currentProgramName", "r")
    #currentProgramName = fp.read()
    #fp.close()
    currentPlayingProgram = station.config.get("Stream", "currentPlayingProgram")

    currentProgram, nextProgram = station.getCurrentAndNextProgram()

    if (currentPlayingProgram != currentProgram["programRef"]):
        station.switchProgram()
        station.config.set("Stream", "currentPlayingProgram", currentProgram["programRef"])
        fp = open(configFile, "w")
        station.config.write(fp)
        fp.close()
        #fp = open("/home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/server/currentProgramName", "w")
        #fp.write(currentProgram["programRef"])
        #fp.close()
