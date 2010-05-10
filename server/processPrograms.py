#!/usr/bin/env python

from JJPS.Station import Station
configFile = "/home/nknouf/Documents/Personal/Projects/JJPS/repository/server/JJPSConfig.ini"

if __name__ == "__main__":
    station = Station(configFile = configFile)

    lastProcessedProgram = station.config.get("Stream", "lastProcessedProgram")

    currentProgram, nextProgram = station.getCurrentAndNextProgram()

    if (lastProcessedProgram != nextProgram["programRef"]):
        station.processSound()
        station.config.set("Stream", "lastProcessedProgram", nextProgram["programRef"])
        fp = open(configFile, "w")
        station.config.write(fp)
        fp.close()
