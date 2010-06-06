#!/usr/bin/env python

from JJPS.Station import Station
configFile = "/home/nknouf/Documents/Personal/Projects/JJPS/repository/server/JJPSConfig.ini"

if __name__ == "__main__":
    station = Station(configFile = configFile)

    currentPlayingProgram = station.config.get("Stream", "currentPlayingProgram")

    currentProgram, nextProgram = station.getCurrentAndNextProgram()

    if (currentPlayingProgram != currentProgram["programRef"]):
        station.switchProgram()
        station.archiveProgram(currentPlayingProgram)
        station.config.set("Stream", "currentPlayingProgram", currentProgram["programRef"])
        station.archiveProgram(currentPlayingProgram)
        fp = open(configFile, "w")
        station.config.write(fp)
        fp.close()
