import csv
import os
import subprocess
import tempfile
import time
import urllib

from BeautifulSoup import BeautifulSoup
import feedparser
from mpd import MPDClient

# The mapping from program IDs to processing code
# TODO
# Implement propper logging facility

# What is the sequence?
# * Lookup upcoming programs
# * Do whatever processing code is necessary for that program
# * Write MP3 for program, update current URL in schedule XML if necessary 
# ** This shouldn't be necessary; the path to each should should be the same no matter what, we just overwrite that MP3 as necessary
# ** After shows (or after we have created the show MP3), we upload it to some sort of file sharing service, saving the created URL in the XML file
# * We need to see if we can use mpd to create a set of playlists that switch at various times; the playlists can be made based on the present list of programs

class Stream(object):
    # TODO
    # write some docs

    def __init__(self, config = None):
        self.config = config

        self.mpdHost = self.config.get("Sound", "mpdHost")
        self.mpdPort = self.config.getint("Sound", "mpdPort")
        self.mpdClient = MPDClient()
        self.mpdClient.connect(self.mpdHost, self.mpdPort)
        self.mpdClient.update()

    def stop(self):
        self.mpdClient.stop()

    def reconnect(self):
        self.mpdClient.disconnect()
        self.mpdClient.connect(self.mpdHost, self.mpdPort)

    def restart(self, currentProgram):
        if (currentProgram['programCurrentLink'] == ''):
            self.mpdClient.stop()
            self.mpdClient.clear()
            self.mpdClient.add("stationID.mp3")
            self.mpdClient.repeat(1)
            self.mpdClient.play()
        else:
            # We seem to have an actual path, so play it
            currentProgramPath = currentProgram['programCurrentLink']
            self.mpdClient.stop()
            self.mpdClient.clear()
            self.mpdClient.add(currentProgramPath)
            self.mpdClient.repeat(1)
            self.mpdClient.play()


class Process(object):
    # TODO
    # Write some documentation

    def __init__(self, config = None):
        self.config = config

    def processUpcomingShows(self, nextProgram):
        print "here"
        if not nextProgram['programProcessed']:
            try:
                process = getattr(self, nextProgram['programRef'])
            except AttributeError:
                process = getattr(self, "Default")
            process()
            nextProgram['programProcessed'] = True


    # The default action
    def Default(self):
        print "foo"
   
    # Processing the news
    def NewsProgram(self):
        quotesURL = "http://download.finance.yahoo.com/d/quotes.csv?s=ENL+RUK&f=snl1d1t1c1ohgv&e=.csv"
        quotesCSV = urllib.urlopen(quotesURL)
        
        reader = csv.reader(quotesCSV)
        
        currentTime = time.strftime("%A, %d %B, %Y")
        newsString = "This is the news for " + currentTime + "\n\n"

        newsString += "And now, for the markets.\n\n"
        
        for row in reader:
            code = row[0]
            name = row[1]
            price = row[2]
            date = row[3]
            timeTraded = row[4]
            change = row[5]
            volume = row[9]
            newsString += "%s, with stock code %s, had a price of %s at %s on a change of %s and volume of %s" % (name, code, str(price), timeTraded, str(change), str(volume))
            newsString += "\n\n"
        
        newsString += "And now, for the news.\n\n"
        
        #d = feedparser.parse("http://news.google.com/news?pz=1&cf=all&ned=us&hl=en&q=reed+elsevier&cf=all&output=rss") 
        d = feedparser.parse("http://finance.yahoo.com/rss/headline?s=ENL") 
        entries = d['entries'][0:9]
        
        for entry in d['entries']:
            title = entry['title']
            newsString += "%s\n\n" % title
            summary = entry['summary']
            #soup = BeautifulSoup(entry['summary'])
            #print soup.contents[0]
            #summary = soup.getText()
            newsString += "%s\n\n" % summary
       
        tempFH, tempFilename = tempfile.mkstemp(suffix = ".txt", prefix = "JJPS")
        tempFP = os.fdopen(tempFH, "wb")
        tempFP.write(newsString.encode("ascii", "ignore"))
        tempFP.close()

        text2wavePath = self.config.get("Sound", "text2wavePath")
        ffmpegPath = self.config.get("Sound", "ffmpegPath")
        outputPath = self.config.get("Sound", "outputPath")
       
        # TODO
        # make voice a configuration variable
        commandTTS = """%s -eval "(voice_cmu_us_slt_arctic_hts)" %s""" % (text2wavePath, tempFilename)
        commandConversion = """%s -y -i - %s/news.mp3 """ % (ffmpegPath, outputPath)

        # TODO
        # Need to figure out why I can't choose a particular voice
        processTTS = subprocess.Popen([text2wavePath, tempFilename], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        processConversion = subprocess.Popen([ffmpegPath, "-y", "-i", "-", outputPath + "/news.mp3"], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Pass the TTS output to the communicate input
        processConversion.communicate(processTTS.communicate()[0])

        # Cleanup
        os.remove(tempFilename)
