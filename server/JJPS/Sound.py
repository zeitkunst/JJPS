import csv
import logging
import math
import os
import random
import shutil
import subprocess
import tempfile
import time
import urllib

from BeautifulSoup import BeautifulSoup
import feedparser
from mpd import MPDClient
import couchdb
import nltk

# The mapping from program IDs to processing code

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

        # Setup logging
        # TODO make this more general, perhaps put in __init__ like in MSThesis?
        self.logger = logging.getLogger('JJPS')
        logFormatter = logging.Formatter('%(asctime)s (%(process)d) %(levelname)s: %(message)s')
        fileHandler = logging.FileHandler(self.config.get("Station", "logPath"))
        fileHandler.setFormatter(logFormatter)
        level = getattr(logging, self.config.get("Station", "defaultLogLevel").upper())
        self.logger.addHandler(fileHandler)
        self.logger.setLevel(level)

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

    def __init__(self, config = None, db = None):
        self.config = config

        if db is not None:
            self.db = db

        # Setup logging
        # TODO make this more general, perhaps put in __init__ like in MSThesis?
        self.logger = logging.getLogger('JJPS')
        logFormatter = logging.Formatter('%(asctime)s (%(process)d) %(levelname)s: %(message)s')
        fileHandler = logging.FileHandler(self.config.get("Station", "logPath"))
        fileHandler.setFormatter(logFormatter)
        level = getattr(logging, self.config.get("Station", "defaultLogLevel").upper())
        self.logger.addHandler(fileHandler)
        self.logger.setLevel(level)


    def processUpcomingShows(self, nextProgram):
        if not nextProgram['programProcessed']:
            try:
                process = getattr(self, nextProgram['programRef'])
            except AttributeError:
                process = getattr(self, "Default")
            process()
            nextProgram['programProcessed'] = True


    # The default action
    def Default(self):
        pass
   
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
        id3tagPath = self.config.get("Sound", "id3tagPath")
       
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

        processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='News'", "--year=2010", outputPath + "/news.mp3"], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        # Cleanup
        os.remove(tempFilename)

    def ProgramOne(self):
        self.DummyProgram("Program One")

    def ProgramTwo(self):
        self.DummyProgram("Program Two")

    def ProgramThree(self):
        self.DummyProgram("Program Three")

    def ProgramFour(self):
        self.DummyProgram("Program Four")

    def ProgramFive(self):
        self.DummyProgram("Program Five")

    def RandomVocalPlayback(self):
        # Get list of documents
        docIDs = [item for item in self.db if item.find("_design") == -1]
        docID = random.choice(docIDs)
        self._makeTTSFileChunks(voice = None, text = self.db[docID]["text"], title = "Random Vocal Playback")

    # Processing a dummy program
    def DummyProgram(self, programText):
        # Get Paths to programs we're going to use
        text2wavePath = self.config.get("Sound", "text2wavePath")
        ffmpegPath = self.config.get("Sound", "ffmpegPath")
        outputPath = self.config.get("Sound", "outputPath")
        id3tagPath = self.config.get("Sound", "id3tagPath")

        programRef = programText.replace(" ", "")

        programText = "This is %s on Journal of Journal Performance Studies Radio." % programText       
        tempFH, tempFilename = tempfile.mkstemp(suffix = ".txt", prefix = "JJPS")
        tempFP = os.fdopen(tempFH, "wb")
        tempFP.write(programText.encode("ascii", "ignore"))
        tempFP.close()


        # TODO
        # make voice a configuration variable
        commandTTS = """%s -eval "(voice_cmu_us_slt_arctic_hts)" %s""" % (text2wavePath, tempFilename)
        commandConversion = """%s -y -i - %s/news.mp3 """ % (ffmpegPath, outputPath)

        # TODO
        # Need to figure out why I can't choose a particular voice
        processTTS = subprocess.Popen([text2wavePath, tempFilename], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        processConversion = subprocess.Popen([ffmpegPath, "-y", "-i", "-", outputPath + "/%s.mp3" % programRef], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Pass the TTS output to the communicate input
        processConversion.communicate(processTTS.communicate()[0])

        processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % programRef, "--year=2010", outputPath + "/%s.mp3" % programRef], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Cleanup
        os.remove(tempFilename)

    def _makeTTSFileChunks(self, voice = None, text = "JJPS Radio", title = "Show"):
        # TODO
        # Make platform-agnostic with os.path.join

        # Get Paths to programs we're going to use
        text2wavePath = self.config.get("Sound", "text2wavePath")
        ffmpegPath = self.config.get("Sound", "ffmpegPath")
        outputPath = self.config.get("Sound", "outputPath")
        id3tagPath = self.config.get("Sound", "id3tagPath")
        mp3wrapPath = self.config.get("Sound", "mp3wrapPath")
        chunkSize = self.config.getint("Sound", "chunkSize")

        # Tokenize input so that we can do this in chunks
        self.logger.debug("Tokenizing input")
        sentences = nltk.sent_tokenize(text)

        if (len(sentences) > chunkSize):
            numSentences = len(sentences)

            startSentence = 0
            endSentence = chunkSize - 1
            
            # Get the total number of times we should run this chunk process
            numChunks = math.ceil(float(numSentences)/float(chunkSize))

            mp3Filenames = []
            for index in xrange(numChunks):
                startSentence = index*chunkSize
                endSentence = min((index + 1)*chunkSize - 1, numSentences)

                currentSentences = sentences[startSentence:endSentence]
                chunkedText = "  ".join(currentSentences)

                # Create temp file to hold text
                tempFH, tempFilename = tempfile.mkstemp(suffix = ".txt", prefix = "JJPS")
                tempFP = os.fdopen(tempFH, "wb")
                tempFP.write(chunkedText.encode("ascii", "ignore"))
                tempFP.close()

                # Create no spaces version of show name with trailing zeros
                titleNospaces = title.replace(" ", "")
                titleNospacesChunk = "%s%03d" % (titleNospaces, index)
                

                # TODO
                # Need to figure out why I can't choose a particular voice
                self.logger.debug("Starting TTS and MP3 encoding processes for show %s and chunk %03d of %03d" % (title, index, numChunks-1))
                processTTS = subprocess.Popen([text2wavePath, tempFilename], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        
                processConversion = subprocess.Popen([ffmpegPath, "-y", "-i", "-", tempfile.tempdir + "/%s.mp3" % titleNospacesChunk], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        
                # Pass the TTS output to the communicate input
                processConversion.communicate(processTTS.communicate()[0])

                # Cleanup
                os.remove(tempFilename)

                mp3Filenames.append(tempfile.tempdir + "/%s.mp3" % titleNospacesChunk)
            
            # Wrap MP3 files
            self.logger.debug("Wrapping files")
            processCall = [mp3wrapPath, outputPath + "/%s.mp3" % titleNospaces]
            processCall.extend(mp3Filenames)
            print processCall
            # Use call so that we don't immediately go to move command below
            processMP3Wrap = subprocess.call(processCall, shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

            # Unfortunately mp3wrap adds an annoying suffix to every file
            # We need to move the file to get rid of it
            shutil.move(outputPath + "/%s_MP3WRAP.mp3" % titleNospaces, outputPath + "/%s.mp3" % titleNospaces)

            # Tag files
            self.logger.debug("Tagging file")
            processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % title, "--year=2010", outputPath + "/%s.mp3" % titleNospaces], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

            # Cleaning up
            self.logger.debug("Cleaning up")
            for file in mp3Filenames:
                os.remove(file)
