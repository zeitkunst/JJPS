import datetime, time

import lxml
from lxml.html import builder as E
from lxml import etree

NAMESPACES= {"JJPS": "http://journalofjournalperformancestudies.org/ns/1.0/#"}

# All of the JJPS station methods
class JJPSStation(object):
    DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    def __init__(self, stationXML = "station.xml"):
        self.stationXML = stationXML
        self.stationTree = etree.parse(self.stationXML)

    def reloadXML(self):
        self.stationTree = etree.parse(self.stationXML)

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
        HOUR_PIXEL_CONVERSION = 0.42
    
        scheduleDiv = etree.Element("div")
        scheduleDiv.set("id", "scheduleDiv")
    
        # Create times
        timeDiv = etree.Element("div")
        timeDiv.set("id", "timeDiv")
        timeDiv.set("style", "width: 50px; float: left;")
        blankP = etree.Element("p")
        blankP.set("style", "min-height: 2em;")
        timeDiv.append(blankP)
    
        for hour in xrange(0, 24):
            hourP = etree.Element("p")
            hourP.text = "%02d:00" % hour
            hourP.set("style", "min-height: %spx" % str(int(60 * HOUR_PIXEL_CONVERSION)))
            timeDiv.append(hourP)
    
        scheduleDiv.append(timeDiv)
    
        for day in days:
            currentDaySchedule = scheduleDict[day]
    
            dayDiv = etree.Element("div")
            dayDiv.set("id", day + "Div")
            dayDiv.set("class", "dayClass")
    
            dayNameH2 = etree.Element("h2")
            dayNameH2.text = day.capitalize()
            dayNameH2.set("style", "min-height: 2em;")
            dayDiv.append(dayNameH2)
    
            startTimes = currentDaySchedule.keys()
            startTimes.sort()
    
            for startTime in startTimes:
                endTime = scheduleDict[day][startTime]["endTime"]
    
                # First, convert from 00:00 format
                time1 = time.strptime(startTime, "%H:%M")
                time2 = time.strptime(endTime, "%H:%M")
    
                # Then, put in datetime format
                time1 = datetime.datetime(2001, 01, 01, time1[3], time1[4], 0)
                time2 = datetime.datetime(2001, 01, 01, time2[3], time2[4], 0)
                duration = time2 - time1
                # Get duration in minutes
                totalMinutes = (duration.seconds)/60
                totalMinutes = totalMinutes * HOUR_PIXEL_CONVERSION
    
                programDiv = etree.Element("div")
                programName = scheduleDict[day][startTime]["programName"]
                programRef = scheduleDict[day][startTime]["programRef"]
                programNameID = programName.replace(" ", "_")
                programDiv.set("id", programNameID)
                programDiv.set("class", "programItem")
                programDiv.set("style", "min-height: %spx" % str(int(totalMinutes)))
    
                programTitleH3 = etree.Element("h3")
                programTitleA = etree.Element("a")
                programTitleA.text = programName
                programTitleA.set("href", "/programs/" + programRef)
                programTitleH3.append(programTitleA)
                programDiv.append(programTitleH3)
    
                dayDiv.append(programDiv)
    
            scheduleDiv.append(dayDiv)
    
        return lxml.html.tostring(scheduleDiv)

    def getProgramInfoDict(self, programRef):
        programDict = {}

        xpathString = "//JJPS:program[@id='%s']" % programRef
        # Also assuming program ids are unique
        # TODO need some way to enforce this in XML file...can we do it in RELAX NG?
        program = self.stationTree.xpath(xpathString, namespaces = NAMESPACES)
        if (program == []):
            return None
    
        programName = program[0].xpath("JJPS:name/text()", namespaces = NAMESPACES)[0]
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
        
        return programDict


    def getProgramInfoHTML(self, programRef):
        # Retrieve information about a particular program and format it for HTML display
        programDict = self.getProgramInfoDict(programRef)

        programDiv = etree.Element("div")
        programName = programDict["programName"]
        programNameID = programName.replace(" ", "_")
        programDiv.set("id", programNameID)
        programDiv.set("class", "programItem")
    
        programTitleH3 = etree.Element("h3")
        programTitleH3.text = programName
        programDiv.append(programTitleH3)

        hostedBy = programDict["programHostedBy"]
        programPersonsDiv = etree.Element("div")
        programPersonsDiv.set("class", "hostedBy")

        for person in hostedBy.keys():
            # TODO
            # Make link to person's page
            personP = etree.Element("p")
            personP.text = person
            programPersonsDiv.append(personP)

        programDiv.append(programPersonsDiv)

        programDescription = programDict["programDescription"]
        programDescP = etree.Element("p")
        programDescP.text = programDescription
        programDiv.append(programDescP)

        return lxml.html.tostring(programDiv)

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
