import codecs
import ConfigParser
import datetime, time
import os
import random
import shutil

import lxml
import eyeD3
from lxml import etree
import mpd
import memcache
import couchdb

# Local imports
import Sound
import Log

NAMESPACES= {"JJPS": "http://journalofjournalperformancestudies.org/ns/1.0/#"}

# All of the JJPS station methods
class Station(object):
    DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    def __init__(self, configFile = "JJPSConfig.ini"):
        self.config = ConfigParser.ConfigParser()
        self.config.read(configFile)

        # Setup logging
        # TODO make this more general, perhaps put in __init__ like in MSThesis?
        self.logger = Log.getLogger(config = self.config)

        # Setup database
        self.logger.debug("Setting up database connection")
        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        self.db = self.dbServer[self.config.get("Database", "name")]

        self.logger.debug("Parsing station XML file")
        self.stationXML = self.config.get("Station", "xmlPath")
        self.stationTree = etree.parse(self.stationXML)

        self.logger.debug("Setting up sound processor")
        self.soundProcess = Sound.Process(config = self.config, db = self.db)

        self.logger.debug("Setting up sound stream")
        self.soundStream = Sound.Stream(config = self.config)

        # Setup memcache
        self.mc = memcache.Client([self.config.get("memcache", "server")], debug = int(self.config.get("memcache", "debug")))

    def reloadXML(self):
        self.stationTree = etree.parse(self.stationXML)

    def processSound(self):
        currentProgram, nextProgram = self.getCurrentAndNextProgram()

        # TODO
        # Add in proper exception handling
        self.soundProcess.processUpcomingShows(nextProgram)

        # Update processed variables
        currentProgramRef = currentProgram["programRef"]
        xpathString = "//JJPS:program[@id='%s']" % currentProgramRef
        currentProgram = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)
        currentProgram[0].set("processed", "0")

        nextProgramRef = nextProgram["programRef"]
        xpathString = "//JJPS:program[@id='%s']" % nextProgramRef
        nextProgram = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)
        nextProgram[0].set("processed", "1")

        # Write out XML file
        fp = open(self.config.get("Station", "xmlPath"), "w")
        fp.write(etree.tostring(self.stationTree))
        fp.close()

    def archiveProgram(self, programName):
        """Archive the program."""
        self.logger.debug("Archiving %s" % programName)

        xpathString = "//JJPS:program[@id='%s']/JJPS:archives" % programName 
        archives = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)[0]
        xpathString = "//JJPS:program[@id='%s']/JJPS:archives/JJPS:archive" % programName 
        archiveList = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)

        numArchives = self.config.get("Station", "numArchives")
        archivePath = self.config.get("Sound", "archivePath")

        # TODO
        # fix for when we have switched programs after midnight, but the program took place the day before...
        today = time.strftime("%Y%m%d")
        
        mp3PathSrc = os.path.join(archivePath, programName, programName + "Current" + ".mp3")
        mp3PathDest = os.path.join(archivePath, programName, programName + "_" + today + ".mp3")
        try:
            os.stat(mp3PathSrc)
        except OSError:
            self.logger.error("MP3 file doesn't exist; need to setup archiving for this show: %s" % programName)
            return

        shutil.move(mp3PathSrc, mp3PathDest)
        ns = "{%s}" % NAMESPACES["JJPS"]
        archive = etree.Element(ns + "archive", nsmap = NAMESPACES)
        archive.set("date", today)
        archive.set("href", programName + "_" + today + ".mp3")
        archive.set("hidden", "0")

        try:
            playlistSrc = os.path.join(archivePath, programName, programName + "CurrentPlaylist" + ".txt")
            playlistDest = os.path.join(archivePath, programName, programName + "Playlist" + "_" + today + ".txt")
            os.stat(playlistSrc)
            shutil.move(playlistSrc, playlistDest)
            archive.set("playlistHref", programName + "Playlist" + "_" + today + ".txt")
        except OSError:
            archive.set("playlistHref", "")

        try:
            notesSrc = os.path.join(archivePath, programName, programName + "CurrentNotes" + ".txt")

            fp = codecs.open(notesSrc, "r", "utf-8")
            notes = fp.read()
            fp.close()
            archive.set("notes", notes)
        except IOError:
            archive.set("notes", "")
      
        # Cull archives if necessary
        if (len(archiveList) >= int(numArchives)):
            self.logger.debug("Culling archives for %s" % programName)
            archives.remove(archiveList[0])
        archives.append(archive)

        # Write out XML file
        fp = open(self.config.get("Station", "xmlPath"), "w")
        fp.write(etree.tostring(self.stationTree))
        fp.close()

    def restartStream(self):
        currentProgram, nextProgram = self.getCurrentAndNextProgram()
        self.soundStream.restart(currentProgram)

    def switchProgram(self):
        program, nextProgram = self.getCurrentAndNextProgram()
        self.soundStream.restart(program)

    def getScheduleHTML(self):
        self.scheduleDict = self.constructScheduleDict()
        #self.scheduleHTML = self.constructScheduleHTML(self.scheduleDict, days=["sunday"])
        self.scheduleHTML = self.constructScheduleHTML(self.scheduleDict)
        return self.scheduleHTML

    def constructScheduleDict(self, days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]):
    
        scheduleDict = {}
    
        for day in days:
            scheduleDict[day] = {}
            xpathString = "/JJPS:station/JJPS:schedule/JJPS:%s" % day
    
            # Should only get one result here, so taking the first one
            currentDayTree = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)[0]
            
            # Now loop throuch each slot 
            for slot in currentDayTree.xpath("JJPS:slot", namespaces = NAMESPACES):
                startTime = slot.get("startTime")
                endTime = slot.get("endTime")
                programRef = slot.get("program")

                if (programRef == ""):
                    continue

                scheduleDict[day][startTime] = {"endTime": endTime}

                programDict = self.getProgramInfoDict(programRef)

                # Update schedule with program information
                if programDict is not None:
                    scheduleDict[day][startTime].update(self.getProgramInfoDict(programRef))
    
        return scheduleDict
    
    def constructScheduleHTML(self, scheduleDict, days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]):
        # TODO
        # Make configurable
        # If we make each minute a pixel, that means that the full schedule will be 1440 pixels high, at least.  So, add in a scaling factor so that this is more reasonable, say 800 high.
        HOUR_PIXEL_CONVERSION = 0.60
    
        scheduleDiv = etree.Element("div")
        scheduleDiv.set("id", "scheduleDiv")
    
        # Create times
        timeDiv = etree.Element("div")
        timeDiv.set("id", "timeDiv")
        timeDiv.set("style", "width: 50px; float: left;")
        blankP = etree.Element("p")
        blankP.set("class", "blankHeader")
        blankP.text = "    "
        #blankP.set("style", "min-height: 2em;")
        timeDiv.append(blankP)
    
        for hour in xrange(0, 24):
            hourP = etree.Element("p")
            hourP.text = "%02d:00" % hour
            #hourP.set("style", "min-height: %spx" % str(int(60 * HOUR_PIXEL_CONVERSION)))
            timeDiv.append(hourP)
    
        scheduleDiv.append(timeDiv)

        nowDay = time.strftime("%A").lower()
        nowHour = time.strftime("%H:%M")


        for day in days:
            currentDaySchedule = scheduleDict[day]
    
            dayDiv = etree.Element("div")
            dayDiv.set("id", day + "Div")
            dayDiv.set("class", "dayClass")
    
            dayNameH3 = etree.Element("h3")
            dayNameH3.text = day.capitalize()
            #dayNameH2.set("style", "min-height: 2em;")
            dayDiv.append(dayNameH3)
    
            startTimes = currentDaySchedule.keys()
            startTimes.sort()
    
            for startTime in startTimes:
                endTime = scheduleDict[day][startTime]["endTime"]

                # Find out if this block is highlighted or not
                if (day == nowDay):
                    if ((nowHour >= startTime) and (nowHour < endTime)):
                        highlightProgram = True
                    else:
                        highlightProgram = False
                else:
                    highlightProgram = False

    
                # First, convert from 00:00 format
                time1 = time.strptime(startTime, "%H:%M")
                time2 = time.strptime(endTime, "%H:%M")
    
                # Then, put in datetime format
                time1 = datetime.datetime(2001, 01, 01, time1[3], time1[4], 0)
                time2 = datetime.datetime(2001, 01, 01, time2[3], time2[4], 0)
                duration = time2 - time1
                # Get duration in minutes
                totalMinutes = (duration.seconds)/60
                totalHours = int(round(float(totalMinutes)/float(60)))
                
                totalMinutes = totalMinutes * HOUR_PIXEL_CONVERSION
    
                programDiv = etree.Element("div")
                programName = scheduleDict[day][startTime]["programName"]
                programRef = scheduleDict[day][startTime]["programRef"]
                programNameID = programName.replace(" ", "_")
                programDiv.set("class", programNameID)
                
                # length to css class mapping
                classMapping = ["oneHour", "twoHours", "threeHours", "fourHours", "fiveHours", "sixHours"]

                hourClass = classMapping[int(totalHours) - 1]
                programDiv.set("class", hourClass)
                if highlightProgram:
                    programDiv.set("class", "%s programItem highlightProgram" % hourClass)
                else:
                    programDiv.set("class", "%s programItem" % hourClass)
                #programDiv.set("style", "min-height: %spx" % str(int(totalMinutes)))
    
                programTitleH4 = etree.Element("h4")
                programTitleA = etree.Element("a")
                programTitleA.text = programName
                programTitleA.set("href", "/radio/programs/" + programRef)
                programTitleH4.append(programTitleA)
                programDiv.append(programTitleH4)
    
                dayDiv.append(programDiv)
    
            scheduleDiv.append(dayDiv)
    
        return etree.tostring(scheduleDiv)

    def getProgramInfoDict(self, programRef):
        programDict = {}

        xpathString = "//JJPS:program[@id='%s']" % programRef
        # Also assuming program ids are unique
        # TODO need some way to enforce this in XML file...can we do it in RELAX NG?
        program = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)
        if (program == []):
            return None
    
        programName = program[0].xpath("JJPS:name/text()", namespaces = NAMESPACES)[0]
        programProcessed = program[0].xpath("@processed", namespaces = NAMESPACES)[0]
        programDescription = program[0].xpath("JJPS:description/text()", namespaces = NAMESPACES)[0]
        programCurrentLink = program[0].xpath("JJPS:current", namespaces = NAMESPACES)[0].get("href")
        programHostedBy = program[0].xpath("JJPS:hostedBy/JJPS:person", namespaces = NAMESPACES)
    
        hostedBy = {}
        for person in programHostedBy:
            hostRef = person.get("ref")
            xpathString = "/JJPS:station/JJPS:personalities/JJPS:personality[@id='%s']" % hostRef
            personality = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)
            # TODO
            # Assuming the personality ids are unique
            personalityLink = personality[0].get("href")
            personalityName = personality[0].xpath("JJPS:name/text()", namespaces = NAMESPACES)[0]
            personalityBio = personality[0].xpath("JJPS:bio/text()", namespaces = NAMESPACES)[0]
    
            hostedBy[personalityName] = {"bio": personalityBio, "homepage": personalityLink}

        programDict["programName"] = programName
        programDict["programDescription"]= programDescription
        programDict["programCurrentLink"] = programCurrentLink
        programDict["programHostedBy"] = hostedBy
        programDict["programRef"] = programRef
        programDict["programProcessed"] = int(programProcessed)
        
        return programDict

    def getAllProgramsList(self):
        """Get all of the programs, sorted by programRef"""
        programRefs = []

        xpathString = "//JJPS:program"
        programs = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)

        for program in programs:
            xpathString = "JJPS:name"
            name = program.xpath(xpathString, namespaces = NAMESPACES)[0]

            id = program.get("id")
            programRefs.append((id, name.text))
        programRefs.sort()

        return programRefs
    
    def getAllProgramsHTML(self):
        """Get all of the programs, HTML formatted."""

        programRefs = self.getAllProgramsList()

        div = etree.Element("div")
        div.set("id", "menu")
        div.set("class", "prepend-11 span-7 append-6 last")

        for programRef in programRefs:
            divM = etree.Element("div")
            divM.set("class", "menuItem")
            h1 = etree.Element("h1")
            a = etree.Element("a")
            a.set("href", "/radio/programs/" + programRef[0])
            a.text = programRef[1]
            h1.append(a)
            divM.append(h1)
            div.append(divM)

        return etree.tostring(div, pretty_print = True)

    def getPodcastItemsList(self):
        """Get a list of entries for our podcast."""

        # TODO
        # implement memcached
        #returnValue = self.mc.get(journalNameFormatted.encode("ascii") + "_xml")
        #if returnValue:
        #    return etree.fromstring(returnValue)

        programRefs = self.getAllProgramsList()

        # Get all of the archives and their information
        archiveItems = []
        archivesByDate = {}
        for programRef in programRefs:
            programID = programRef[0]
            programName = programRef[1]
            archives = self.getProgramArchivesList(programID)

            if (archives != []):
                for archive in archives:
                    archiveDate = archive[0]
                    if (archivesByDate.has_key(archiveDate)):
                        archivesByDate[archiveDate].append([programID, programName, archive[1], archive[2]])
                    else:
                        archivesByDate[archiveDate] = []
                        archivesByDate[archiveDate].append([programID, programName, archive[1], archive[2]])
            
        # Select an item by random for each date
        finalArchiveList = []
        
        archiveDates = archivesByDate.keys()
        archiveDates.sort()
        archiveDates.reverse()
        archivePath = self.config.get("Sound", "archivePath")
        for archiveDate in archiveDates:
            selectedArchive = random.choice(archivesByDate[archiveDate])
            programID = selectedArchive[0]
            programName = selectedArchive[1]
            programMP3 = selectedArchive[2]
            programPlaylist = selectedArchive[3]

            mp3Path = os.path.join(archivePath, programID, programID + "_" + archiveDate + ".mp3")
            playtime = eyeD3.Mp3AudioFile(mp3Path).getPlayTime()
            size = os.path.getsize(mp3Path)

            description = programName
            
            dateTuple = time.strptime(archiveDate, "%Y%m%d")
            dateFormatted = time.strftime("%a, %d %b %Y %H:%M:%S", dateTuple)
            entryDict = {}
            entryDict["title"] = programName
            entryDict["description"] = "Check out the <a href='http://journalofjournalperformancestudies.org%s'>playlist</a>." % programPlaylist
            entryDict["size"] = size
            entryDict["playtime"] = playtime
            entryDict["url"] = programMP3
            entryDict["date"] = dateFormatted
            entryDict["playlist"] = programPlaylist
            finalArchiveList.append(entryDict)

        return finalArchiveList

    def getAllProgramsTechnical(self):
        """Get all of the technical information about the programs, sorted by programRef"""
        programRefs = self.getAllProgramsList()

        technical = {}

        for programRef in programRefs:
            xpathString = "//JJPS:program[@id='%s']/JJPS:technical" % programRef[0]
            technicalList = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)

            for result in technicalList:
                technical[programRef[1]] = result.text.strip()
        
        return technical

    def getAllProgramsTechnicalHTML(self):
        """Get all of the technical information about the programs, sorted by programRef"""
        technical = self.getAllProgramsTechnical()
        
        divE = etree.Element("div")
        ids = technical.keys()
        ids.sort() 
        for id in ids:
            h2E = etree.Element("h2")
            h2E.text = id
            divE.append(h2E)
            text = technical[id]
            pTE = etree.Element("p")
            pTE.text = text
            pTE.set("id", id.replace(" ", "").replace("'", ""))
            divE.append(pTE)
        
        return etree.tostring(divE, pretty_print = True)

    def getProgramArchivesList(self, programRef):
        """Get the archives for the given program"""

        programArchivesList = []
        xpathString = "//JJPS:program[@id='%s']/JJPS:archives/JJPS:archive" % programRef
        archiveList = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)
        stem = "/static/archives/" + programRef + "/"

        for archive in archiveList:
            programArchivesList.append([archive.get("date"), stem + archive.get("href"), stem + archive.get("playlistHref"), archive.get("notes")])

        return programArchivesList
    
    def getProgramArchivesHTML(self, programRef):
        """Get an HTML formatted version of the archives."""
        
        programArchivesList = self.getProgramArchivesList(programRef)

        if (len(programArchivesList) == 0):
            return None

        div = etree.Element("div")
        div.set("id", "archives")
        
        for archive in programArchivesList:
            date = archive[0]
            mp3 = archive[1]
            playlist = archive[2]
            notes = archive[3]
            timeTuple = time.strptime(date, "%Y%m%d")
            archiveDate = time.strftime("%d %B %Y", timeTuple)
            p = etree.Element("p")
            p.text = archiveDate + ": "

            if (notes != "" and notes is not None):
                notesSpan = etree.Element("span")
                notesSpan.text = notes + "; "
                p.append(notesSpan)

            a = etree.Element("a")
            a.set("href", mp3)
            a.text = "MP3 Archive"
            a.tail = ", "
            p.append(a)
            # TODO
            # Deal with the case when we don't have a playlist
            a = etree.Element("a")
            a.set("href", playlist)
            a.text = "Playlist"
            p.append(a)
            div.append(p)

        return etree.tostring(div)

    def getProgramInfoHTML(self, programRef):
        # Retrieve information about a particular program and format it for HTML display
        programDict = self.getProgramInfoDict(programRef)

        programDiv = etree.Element("div")
        programName = programDict["programName"]
        programNameID = programName.replace(" ", "_")
        programDiv.set("id", programNameID)
        programDiv.set("class", "programItem")
    
        programTitleH1 = etree.Element("h1")
        programTitleH1.text = programName
        programDiv.append(programTitleH1)

        hostedBy = programDict["programHostedBy"]
        programPersonsDiv = etree.Element("div")
        programPersonsDiv.set("class", "hostedBy")

        personH2 = etree.Element("h2")
        personH2.text = "Hosted by "
        for person in hostedBy.keys():
            # TODO
            # Make link to person's page
            #personH2 = etree.Element("h2")
            personH2.text += person
            programPersonsDiv.append(personH2)

        programDiv.append(programPersonsDiv)

        programDescription = programDict["programDescription"]
        programDescP = etree.Element("p")
        programDescP.text = programDescription
        programDiv.append(programDescP)

        return (etree.tostring(programTitleH1), etree.tostring(programPersonsDiv), etree.tostring(programDescP))

    def getProgramIDsAndNames(self):
        """Return a list of program IDs and names for construction of a select box on the station website."""
        xpath = "//JJPS:program"
        nodes = self.stationTree.xpath(xpath, namespaces = NAMESPACES)
        programList = []
        
        for node in nodes:
            id = node.get("id")
            name = node.xpath("JJPS:name/text()", namespaces = NAMESPACES)[0]
            programList.append((id, name))

        return sorted(programList)

    def getCurrentAndNextProgram(self):
        currentDay = time.strftime("%A").lower()
        currentHour = time.strftime("%H")

        currentDayScheduleDict = self.constructScheduleDict(days = [currentDay])

        startTimes = currentDayScheduleDict[currentDay].keys()
        startTimes.sort()

        # Keep track of current and next programs
        # TODO
        # Fix for when we are moving to the next day
        # Probably could make this much simpler somehow...
        counter = 0
        for startTime in startTimes:
                # First, convert from 00:00 format
            time1 = time.strptime(startTime, "%H:%M")
            time1Hour = time1[3]

            if int(currentHour) >= int(time1Hour):
                counter += 1
                continue
            else:
                pass

        if (counter == len(startTimes)):
            # This means we have to move to the next day
            currentDayIndex = self.DAYS.index(currentDay)
            tomorrowDayIndex = (currentDayIndex + 1) % 7
            tomorrow = self.DAYS[tomorrowDayIndex]
            tomorrowDayScheduleDict = self.constructScheduleDict(days = [tomorrow])
            startTimesTomorrow = tomorrowDayScheduleDict[tomorrow].keys()
            startTimesTomorrow.sort()
            
            # Assume that if we've sorted the keys, the first one will point to the first program of the day
            currentProgram =  currentDayScheduleDict[currentDay][startTimes[counter - 1]]
            nextProgram = tomorrowDayScheduleDict[tomorrow][startTimesTomorrow[0]]
        else:
            # This means we haven't made it to the next day yet
            currentProgram =  currentDayScheduleDict[currentDay][startTimes[counter - 1]]
            nextProgram = currentDayScheduleDict[currentDay][startTimes[counter]]

        return (currentProgram, nextProgram)
