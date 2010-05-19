import binascii
import csv
import logging
import math
from operator import itemgetter
import os
import random
import re
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

# Dictionary for our hex to binary mapping
hexDict = {
        '0':'0000', '1':'0001', '2':'0010', '3':'0011', '4':'0100', '5':'0101',
        '6':'0110', '7':'0111', '8':'1000', '9':'1001', 'a':'1010', 'b':'1011',
        'c':'1100', 'd':'1101', 'e':'1110', 'f':'1111', 'L':''}

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
            #self.mpdClient.stop()
            #self.mpdClient.clear()
            self.mpdClient.update()
            self.mpdClient.add("stationID.mp3")
            self.mpdClient.delete(0)
            self.mpdClient.repeat(1)
            self.mpdClient.play()
        else:
            # We seem to have an actual path, so play it
            currentProgramPath = currentProgram['programCurrentLink']
            #self.mpdClient.stop()
            #self.mpdClient.clear()
            self.mpdClient.update()
            self.mpdClient.add(currentProgramPath)
            currentPlaylist = self.mpdClient.playlistinfo()

            if (len(currentPlaylist) == 1):
                # If we're just starting, setup repeat and start playing
                self.mpdClient.repeat(1)
                self.mpdClient.play()
            else:
                # Otherwise, remove the first element in the playlist
                firstID = currentPlaylist[0]["id"]
                self.mpdClient.next()
                self.mpdClient.deleteid(firstID)
                self.mpdClient.repeat(1)
                self.mpdClient.play()


"""Counting syllables
from nltk_contrib.readability import syllables_en
syllableCount = []
for word in tokens:
    syllableCount.append(syllables_en.count(word))
                        
foo = zip(tokens, syllableCount)
"""
class Process(object):
    # TODO
    # Write some documentation
    # Setup pre- and post-processing hooks, especially for the text
    # Add "playlist" attribute to station.xml file

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

    def _makeTokens(self, text, clean = True):
        """Helper function to tokenize our input text."""
        tokens = []
        sentences = nltk.sent_tokenize(text)
        for sentence in sentences:
            words = nltk.word_tokenize(sentence)
            for word in words:
                tokens.append(word)

        # If we want to get rid of punctuation...
        if (clean):
            clean_tokens = []
            for token in tokens:
                if len(token) < 2: # Only save words longer than 2 chars
                    continue
                clean_tokens.append(token.lower()) # Always lower case
            return clean_tokens

        else:
            # Or just get everything, in lowercase of course
            clean_tokens = []
            for token in tokens:
                clean_tokens.append(token.lower())
            return clean_tokens

    def processUpcomingShows(self, nextProgram):
        """Main method to process the upcoming show."""
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
        self.logger.info("Random Vocal Playback: starting processing...")
        # Get list of documents
        docIDs = [item for item in self.db if item.find("_design") == -1]
        docID = random.choice(docIDs)
        self.logger.debug("Random Vocal Playback: TTS")
        self._makeTTSFileChunks(voice = None, text = self.db[docID]["text"], title = "Random Vocal Playback")

        self.logger.info("Random Vocal Playback: done")

    def CutupHour(self):
        self.logger.info("Cutup Hour: starting processing...")

        docIDs = [item for item in self.db if item.find("_design") == -1]
        totalNumSentences = 350
        numSentencesToGet = int(totalNumSentences)/int(len(docIDs))
        
        self.logger.debug("Cutup Hour: getting fragments")
        cutupSentences = []
        for docID in docIDs:
            sentences = nltk.sent_tokenize(self.db[docID]["text"])
            cutupSentences.extend(random.sample(sentences, numSentencesToGet))
        
        random.shuffle(cutupSentences)
        text = "This is the Cutup Hour, where we select random fragments from our archives and reassemble them into something new.  Enjoy.  "
        text += "  ".join(cutupSentences)
        
        self.logger.debug("Cutup Hour: TTS")
        self._makeTTSFileChunks(voice = None, text = text, title = "Cutup Hour")

        self.logger.info("Cutup Hour: done")

    def WhatsTheFrequencyKenneth(self):
        self.logger.info("What's the Frequency Kenneth: starting processing...")
        
        docIDs = [item for item in self.db if item.find("_design") == -1]
        
        docID = random.choice(docIDs)
        self.logger.debug("What's the Frequency Kenneth: calculating the number of words")
        data = self.db[docID]
        numWords = [(word, round(data["numTokens"] * tf)) for word, tf in data["tf"].items()]
        numWords = sorted(numWords, key=itemgetter(1), reverse = True)

        output = ""
        for key, value in numWords:
            if (int(value) == 1):
                output += "The word %s occurred %d time in the text.  " % (key, int(value)) 
            else:                
                output += "The word %s occurred %d times in the text.  " % (key, int(value)) 

        text = "Now on the air: What's the Frequency Kenneth.  A program where we recite the number of words in a particular text.  See if you can guess which text it is!  "
        text += output
        
        self.logger.debug("What's the Frequency Kenneth: TTS")
        self._makeTTSFileChunks(voice = None, text = text, title = "What's the Frequency Kenneth")

        self.logger.info("What's the Frequency Kenneth: done")


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
        #commandTTS = """%s -eval "(voice_cmu_us_slt_arctic_hts)" %s""" % (text2wavePath, tempFilename)
        #commandConversion = """%s -y -i - %s/news.mp3 """ % (ffmpegPath, outputPath)

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
        self.logger.debug("TTS Chunks: Tokenizing input")
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
                self.logger.debug("TTS Chunks: Starting TTS and MP3 encoding processes for show %s and chunk %03d of %03d" % (title, index, numChunks-1))
                processTTS = subprocess.Popen([text2wavePath, tempFilename], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        
                processConversion = subprocess.Popen([ffmpegPath, "-y", "-i", "-", tempfile.tempdir + "/%s.mp3" % titleNospacesChunk], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        
                # Pass the TTS output to the communicate input
                processConversion.communicate(processTTS.communicate()[0])

                # Cleanup
                os.remove(tempFilename)

                mp3Filenames.append(tempfile.tempdir + "/%s.mp3" % titleNospacesChunk)
            
            # Wrap MP3 files
            self.logger.debug("TTS Chunks: Wrapping files")
            processCall = [mp3wrapPath, outputPath + "/%s.mp3" % titleNospaces]
            processCall.extend(mp3Filenames)
            
            # Use call so that we don't immediately go to move command below
            processMP3Wrap = subprocess.call(processCall, shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

            # Unfortunately mp3wrap adds an annoying suffix to every file
            # We need to move the file to get rid of it
            shutil.move(outputPath + "/%s_MP3WRAP.mp3" % titleNospaces, outputPath + "/%s.mp3" % titleNospaces)

            # Tag files
            self.logger.debug("TTS Chunks: Tagging file")
            processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % title, "--year=2010", outputPath + "/%s.mp3" % titleNospaces], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

            # Cleaning up
            self.logger.debug("Cleaning up")
            for file in mp3Filenames:
                os.remove(file)

    def Telegraph(self):
        # Get Paths to programs we're going to use
        ffmpegPath = self.config.get("Sound", "ffmpegPath")
        outputPath = self.config.get("Sound", "outputPath")
        id3tagPath = self.config.get("Sound", "id3tagPath")
        mp3wrapPath = self.config.get("Sound", "mp3wrapPath")
        csoundPath = self.config.get("Sound", "csoundPath")
        # TODO
        # Probably get this from couchdb later
        pdfPath = self.config.get("Sound", "pdfPath")

        pdfFP = open(os.path.join(pdfPath, "Land1993.pdf"), "r")

        instrumentList = ["morseSimple.instr"]


        fTables = []
        fTables.append("f1 0 512 10 1 ; sine wave")
        fTables.append("f2  0 4096 10   1  .5 .333 .25 .2 .166 .142 .125 .111 .1 .09 .083 .076 .071 .  066 .062 ; sawtooth wave")
       
        # 1000 bits is about 15 min
        chunkSize = 1000
        numChunks = 7
        mp3Filenames = []
        oneDuration = 0.1
        zeroDuration = 0.05
        offset = 0.03
        amp = 4000
        freq = 440
        fTableToUse = 1
        for chunkNumber in xrange(numChunks):
            # We don't have to figure out the start and end chunks...we just continue reading!

        
            # Create our binary string
            binaryString = ""
            for x in xrange(chunkSize):
                data = binascii.b2a_hex(pdfFP.read(1))
                binaryString += hexDict[data[0]]
                binaryString += hexDict[data[1]]

            # Clear out the notes
            notes = []
            time = 0
            for value in binaryString:
                if (value == "0"):
                    notes.append("i1 %f %f %f %f %d" % (time, zeroDuration, amp, freq, fTableToUse))
                    time += offset + zeroDuration
                elif (value == "1"):
                    notes.append("i1 %f %f %f %f %d" % (time, oneDuration, amp, freq, fTableToUse))
                    time += offset + oneDuration
            
            csdMaker = CsoundProcessor(config = self.config)
            instruments = csdMaker.loadInstruments(instrumentList, instrumentPrefix = csdMaker.instrumentPrefix)
            csd = csdMaker.makeCSD(instruments, fTables, notes)
            
            self.logger.debug("Telegraph: on chunk %d of %d" % (chunkNumber, numChunks))
            mp3File = self._makeCsoundChunks(csd, chunkNumber)
            mp3Filenames.append(mp3File)

        # Okay, got all of our mp3 files, let's finish wrapping them            
        self.logger.debug("Telegraph: wrapping mp3")
        self._wrapMp3Files(mp3Filenames, "Telegraph")

        # Close our PDF file
        pdfFP.close()

    def GrainCombine(self):
        docIDs = [item for item in self.db if item.find("_design") == -1]
        docID = random.choice(docIDs)
        data = self.db[docID]

        self.logger.debug("Grain Combine: tokenizing words")
        # Tokenize our data into an ordered list of words
        text = data["text"]
        tokens = self._makeTokens(text)
        
        # Then, get a syllable mapping
        self.logger.debug("Grain Combine: counting syllables")
        from nltk_contrib.readability import syllables_en
        words = data["tf_idf"].keys()
        syllables = {}
        for word in data["tf_idf"].keys():
            syllables[word] = syllables_en.count(word)

        # our instrument
        instrumentList = ["grainSimple.instr"]

        self.logger.debug("Grain Combine: creating TTS words")
        # Get a list of TTSed words to use
        tempDir = tempfile.mkdtemp()
        # Bias the words
        numWords = [(word, round(data["numTokens"] * tf)) for word, tf in data["tf"].items()]
        numWords = sorted(numWords, key=itemgetter(1), reverse = True)
        wordList = [word[0] for word in numWords]
        totalWords = 150
        wordList = wordList[0:totalWords]

        TTSWords = self.makeTTSWords(tempDir, wordList, numWords = totalWords)
        TTSPossibleWords = [word[0] for word in TTSWords]

        fTables = []
        fTables.append("f1 0 512 10 1 ; sine wave")
        fTables.append("f5 0 512 20 2 ; hanning window")

        # Create a list of ftables that use these words
        # Start counter (and thus these ftables) at 100
        counter = 100
        for word in TTSWords:
            fTables.append("f%d 0 32768 1 \"%s\" 0 0 0" % (counter, word[1]))
            counter += 1

        # Now, create our notes using, as a default, instr 1
        self.logger.debug("Grain Combine: Making notes")
        notes = []
        from numpy import array
        a = array(data["tf"].values())
        a = a * 20
       
        # 200 words is about 5 minutes
        chunkSize = 200
        numChunks = 12
        numTokens = len(tokens)

        mp3Filenames = []
        for chunkNumber in xrange(numChunks):
            startToken = chunkNumber*chunkSize
            endToken = min((chunkNumber+ 1)*chunkSize - 1, tokens)

            currentTokens = tokens[startToken:endToken]

            # Clear out time and notes before each run
            time = 0
            notes = []
            for token in currentTokens:
                try:
                    index = data["tf"].keys().index(token)
                    tf = a[index]
                except ValueError:
                    print "error on token ", token
                    tf = 0
    
                try:
                    syllableCount = syllables[token]
                except KeyError:
                    syllableCount = 0
    
                try:
                    TTSWord = TTSPossibleWords.index(token)
                    # i1 0 12 1000 1 5 10.1 200 200 0.1 0.1
                    notes.append("i1 %f %f 5000 %d 5 0.1 200 200 %f %f" % (time, syllableCount * 1, TTSWord + 100, tf, tf))
                except ValueError:
                    notes.append("i1 %f %f 2500 %d 5 0.1 200 200 %f %f" % (time, 1 + syllableCount * 1, 1, 0.01, 0.01))
                time += syllableCount * 1
    
            # Give me the csd file, please
            csdMaker = CsoundProcessor(config = self.config)
            instruments = csdMaker.loadInstruments(instrumentList, instrumentPrefix = csdMaker.instrumentPrefix)
            csd = csdMaker.makeCSD(instruments, fTables, notes)
            
            self.logger.debug("Grain Combine: on chunk %d of %d" % (chunkNumber, numChunks))
            mp3File = self._makeCsoundChunks(csd, chunkNumber, tempDir = tempDir)
            mp3Filenames.append(mp3File)

        # Okay, got all of our mp3 files, let's finish wrapping them            
        self.logger.debug("Grain Combine: wrapping mp3")
        self._wrapMp3Files(mp3Filenames, "Grain Combine")

    def Feldman(self):
        """In the sparse style of Morton Feldman"""

        # Get random text from database
        docIDs = [item for item in self.db if item.find("_design") == -1]
        docID = random.choice(docIDs)
        data = self.db[docID]

        tokens = self._makeTokens(data["text"], clean = False)

        # Make regex for matching letters
        allLetters = re.compile("[a-zA-Z0-9]+")

        # Go through and count up the number of letters or numbers before a punctionation; save it and the punctuation
        numCharacters = 0
        numbersPunct = []
        for token in tokens:
            if (allLetters.match(token) is not None):
                numCharacters += len(token)
            else:
                numbersPunct.append((numCharacters, token))
                numCharacters = 0

        instrumentList = ["CasconeFMReverseEnv.instr", "Reverb.instr"]

        fTables = []
        fTables.append("f11 0 2048 10 1 ;SINE WAVE hi-res")
        fTables.append("f18 0 512   5 1 512 256 ;reverse exp env")

        # Temporary mapping based on durations
        durationDict = {",": 0.2, ";": 0.4, ":": 0.8, ".": 1.6, "(": 3.2, ")":3.2, "[": 6.4, "]": 6.4, "\"": 6.4}

        time = 0
        notes = []
        for numberPunct in numbersPunct:
            """;;instr    strt dur  frq  car  mod  kpan kndx kamp rvbsnd
            ;i5   0   1   4500 3.25 1.10 0    9.7  4    .09"""
            try:
                freq = 10.0 * numberPunct[0] + 80
                notes.append("i1 %f %f %f 3.25 1.10 0.2 9.7 4 0.09" % (time, durationDict[numberPunct[1]], freq))
                time += durationDict[numberPunct[1]] + (numberPunct[0] * 0.1)
            except KeyError, e:
                print "Key error", e

        # Add reverb
        notes.append("i2 0 %f 2 0.2" % time)

        # Give me the csd file, please
        globalInits = []
        globalInits.append("garvbsig  init      0")
        csdMaker = CsoundProcessor(config = self.config)
        instruments = csdMaker.loadInstruments(instrumentList, instrumentPrefix = csdMaker.instrumentPrefix)
        csd = csdMaker.makeCSD(instruments, fTables, notes, globalInits = globalInits)

        return csd


    def _makeCsoundChunks(self, csd, chunkNumber, tempDir = None, useStdout = False):
        # Write csd file
        if (tempDir is None):
            # TODO
            # make cross-platform
            tempDir = "/tmp"
        
        csdPath = os.path.join(tempDir, "chunk.csd")
        fp = open(csdPath, "w")
        fp.write(csd)
        fp.close()

        # Get paths
        ffmpegPath = self.config.get("Sound", "ffmpegPath")
        csoundPath = self.config.get("Sound", "csoundPath")
        outputPathWav = os.path.join(tempDir, "chunk%03d.wav" % chunkNumber)
        outputPathMp3 = os.path.join(tempDir, "chunk%03d.mp3" % chunkNumber)

        self.logger.debug("Csound chunks: calling csound and ffmpeg")
        if (useStdout):
            processCsound = subprocess.call([csoundPath, "-d", "-o", "stdout", "-W", csdPath, ">", outputPathWav], shell=True, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            processConversion = subprocess.call([ffmpegPath, "-y", "-i", outputPathWav, outputPathMp3], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

            #processConversion.communicate(processCsound.communicate()[0])
        else:
            # TODO
            # Getting rid of the stdout redirect makes the command work...why?
            processCsound = subprocess.call([csoundPath, "-d", "-o", outputPathWav, "-W", csdPath], shell=False, stdin = subprocess.PIPE)
            processConversion = subprocess.call([ffmpegPath, "-y", "-i", outputPathWav, outputPathMp3], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            
            # Cleanup
            os.remove(outputPathWav)

        # Cleanup
        os.remove(csdPath)

        # Return path to mp3file
        return outputPathMp3

    def _wrapMp3Files(self, mp3Filenames, title):
        titleNospaces = title.replace(" ", "")

        # Get Paths to programs we're going to use
        outputPath = self.config.get("Sound", "outputPath")
        id3tagPath = self.config.get("Sound", "id3tagPath")
        mp3wrapPath = self.config.get("Sound", "mp3wrapPath")
        chunkSize = self.config.getint("Sound", "chunkSize")

        # Wrap MP3 files
        # Use call so that we don't immediately go to move command below
        self.logger.debug("Wrap Mp3")
        processCall = [mp3wrapPath, outputPath + "/%s.mp3" % titleNospaces]
        processCall.extend(mp3Filenames)

        processMP3Wrap = subprocess.call(processCall, shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Unfortunately mp3wrap adds an annoying suffix to every file
        # We need to move the file to get rid of it
        shutil.move(outputPath + "/%s_MP3WRAP.mp3" % titleNospaces, outputPath + "/%s.mp3" % titleNospaces)

        # Tag files
        self.logger.debug("TTS Chunks: Tagging file")
        processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % title, "--year=2010", outputPath + "/%s.mp3" % titleNospaces], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Cleaning up
        self.logger.debug("Cleaning up")
        for file in mp3Filenames:
            os.remove(file)

    def makeTTSWords(self, tempDir, wordList, numWords = 100):
        """Make a set of TTS words saved as wave files in a temp diretory.""" 
        
        self.logger.debug("Make TTS Words: making a set of TTS words")
        # Get a random sample of the input words
        wordList = random.sample(wordList, numWords)

        # Create list to hold paths to words
        wordPaths = []
        for word in wordList:
            self._makeTTSWord(tempDir, word)
            wordPaths.append((word, os.path.join(tempDir, word + ".wav")))
        self.logger.debug("Make TTS Words: done")

        return wordPaths

    def _makeTTSWord(self, tempDir, word):
        """Make wave files for a particular word."""

        # TODO
        # Make platform-agnostic with os.path.join

        # Get Paths to programs we're going to use
        text2wavePath = self.config.get("Sound", "text2wavePath")
        ffmpegPath = self.config.get("Sound", "ffmpegPath")
        outputPath = self.config.get("Sound", "outputPath")
        id3tagPath = self.config.get("Sound", "id3tagPath")
        mp3wrapPath = self.config.get("Sound", "mp3wrapPath")
        chunkSize = self.config.getint("Sound", "chunkSize")

        # TODO
        # Sadly we need to write this single _word_ out to a file before we can run text2wave on it; there's got to be a better way!

        # Create temp file to hold text
        tempFH, tempFilename = tempfile.mkstemp(suffix = ".txt", prefix = "JJPS", dir=tempDir)
        tempFP = os.fdopen(tempFH, "wb")
        tempFP.write(word.encode("ascii", "ignore"))
        tempFP.close()

        # TODO
        # Need to figure out why I can't choose a particular voice
        processTTS = subprocess.call([text2wavePath, tempFilename, "-o", os.path.join(tempDir, word + ".wav")], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        os.remove(tempFilename)

class CsoundProcessor(object):
    FTABLES = """
; Initial condition
;f1 0 128 7 0 64 1 64 0
f1 0 128 7 0 32 2 0 -1 32 0 32 2 32 0
; Masses
f2 0 128 -7 1 128 1
; Spring matrices
f3 0 16384 -23 "circularstring-128"
; Centering force
f4  0 128 -7 0 128 2
; Damping
f5 0 128 -7 1 128 1
; Initial velocity
f6 0 128 -7 0 128 0
; Trajectories
f7 0 128 -6 .001 128 64 64
; Sine
f8 0 512 7 0 6 1 5 1 6 0
"""

    def __init__(self, config = None, orcOptions = {'sr': 44100, 'kr': 4410, 'ksmps': 10, 'nchnls': 2}, commandOptions = None):
        self.config = config
        # TODO
        self.instrumentPrefix = self.config.get("Sound", "instrumentPrefix")

        self.orcOptions = orcOptions
        self.commandOptions = commandOptions

    def loadInstruments(self, instrumentList, instrumentPrefix = None):
        instruments = []
        for instrumentPath in instrumentList:
            # Add our prefix if necessary
            if (instrumentPrefix is not None):
                instrumentPath = os.path.join(instrumentPrefix, instrumentPath)
            fp = open(instrumentPath)
            instruments.append(fp.read())
            fp.close()

        return instruments

    def makeCSD(self, instruments, fTables, notes, globalInits = None):
        csd = "<CsoundSynthesizer>\n"

        # Setup options
        csd += "<CsOptions>\n"
        if (self.commandOptions is not None):
            csd += "\n" + self.commandOptions + "\n"
        else:
            csd += "\n"
        csd += "</CsOptions>\n"
       
        # Setup the orc options
        csd += "<CsInstruments>\n"
        csd += """sr = %d
kr = %d
ksmps = %d
nchnls = %d\n\n""" % (self.orcOptions['sr'], self.orcOptions['kr'], self.orcOptions['ksmps'], self.orcOptions['nchnls'])

        if (globalInits is not None):
            for globalInit in globalInits:
                csd += globalInit + "\n"

        count = 1
        for instrument in instruments:
            csd += instrument % count
            count += 1

        csd += "</CsInstruments>\n"

        csd += "<CsScore>\n"

        # Write ftables
        for fTable in fTables:
            csd += fTable + "\n"
        csd += "\n"

        # Write notes
        for note in notes:
            csd += note + "\n"
        csd += "\n"

        csd += "</CsScore>\n"

        csd += "</CsoundSynthesizer>\n"

        return csd
