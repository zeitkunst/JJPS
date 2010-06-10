import binascii
import codecs
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

from lxml import etree
from mpd import MPDClient
import nltk

# Local imports
from Companies import Companies
from Documents import ArticleDocuments, CopyrightDocuments, OpenAccessDocuments, PPCDocuments
from Model import Model
import Log

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
        self.logger = Log.getLogger(config = self.config)

        # Setup media player daemon (mpd)
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

        self.articleDocuments = ArticleDocuments(config = config)

        if db is not None:
            self.db = db

        # Setup logging
        self.logger = Log.getLogger(config = self.config)

    def createTextTransmission(self, text):
        """Create a representation of the text for transmission."""
        tokens = self._makeTokens(text, clean = False)
        uniq = self.uniqify(tokens)
        uniq.sort()
        nums = [uniq.index(token) for token in tokens]
        output = ""
        for num in nums:
            output += "%04x " % (num)

        textTransmission = " ".join(uniq)
        textTransmission += "\n"
        textTransmission += output

        return textTransmission

    def uniqify(self, seq):
        """Keep only the unique items in a list.  Taken from: http://www.peterbe.com/plog/uniqifiers-benchmark"""
        seen = set()
        seen_add = seen.add
        return [x for x in seq if x not in seen and not seen_add(x)]

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
    
    # TODO
    # better name :-)
    def Drone(self):
        """A drone-style program."""
        
        docID = self.articleDocuments.docIDs[18]
        data = self.articleDocuments.get(docID)
        text = data["articleText"]
        tf_idf = data["tf_idf"]

        # Do all of our computations first
        sentences = nltk.sent_tokenize(text)

        tokens = []
        for sentence in sentences:
            tokens.append(self._makeTokens(sentence))
        
        allSyllables = []
        numChunks = 4
        for tokenSet in tokens:
            if (len(tokenSet) < numChunks):
                continue

            chunkSize = int(math.floor(len(tokenSet)/3.0))
            remainder = len(tokenSet) % (numChunks - 1)

            syllables = []
            from nltk_contrib.readability import syllables_en
            for i in xrange(numChunks):
                if (i == (numChunks - 1)):
                    words = tokenSet[i*chunkSize:(i*chunkSize) + remainder]
                else:
                    words = tokenSet[i*chunkSize:(i + 1)*chunkSize]
                
                num = 0
                for word in words:
                    num += syllables_en.count(word)
                
                if (num == 0.0):
                    syllables.append(0.1)
                else:
                    syllables.append(num / 4.0)
            maxValue = max(syllables)
            allSyllables.append([syllable / (maxValue * 2.0) for syllable in syllables])
        
        sentenceLengths = []
        for tokenSet in tokens:
            if (len(tokenSet) < numChunks):
                continue
            else:
                sentenceLengths.append(len(tokenSet))
        
        avgTFIDF = []
        for tokenSet in tokens:

            if (len(tokenSet) < numChunks):
                continue

            counter = 0
            
            total = 0
            for word in tokenSet:
                try:
                    total += math.log(tf_idf[word])
                    counter += 1
                except KeyError:
                    pass
            
            try:
                value = (-1.0 * (float(total) / counter))
            except ZeroDivisionError:
                value = (-1.0 * (-11.0))
            avgTFIDF.append(value * 9)
    
        # Then start making the csd
        tempDir = tempfile.mkdtemp()
        mp3Filenames = []

        # our instrument
        instrumentList = ["droneSimple.instr", "droneReverb.instr"]
        fTables = []
        fTables.append("f1 0 65536 10 1")
        #fTables.append("f   2       0           65536       10      3   0   1   0   0   2")
        fTables.append("f   2       0           65536       10      5   2   7   3   1   2")
        fTables.append("f   3       0           65536       13      1   1   0   3   0   2")

        # divide the input into 6 parts
        numParts = 6
        totalNumbers = min(len(avgTFIDF), 200)
        partSize = int(round(float(totalNumbers)/numParts))

        mp3Filenames = []
        values = zip(allSyllables, sentenceLengths, avgTFIDF)
        for partNumber in xrange(numParts):
            startNumber = partNumber*partSize
            endNumber = min((partNumber + 1)*partSize- 1, totalNumbers)

            currentValues = values[startNumber:endNumber]

            notes = []
            timer = 0
            for value in currentValues:
                s1, s2, s3, s4 = value[0]
                noteDur = value[1] * 2.0
                freq = value[2]
    
                notes.append("i1  %f %f 100 %f 2 0.5 %f %f %f %f" % (timer, noteDur, freq, s1, s2, s3, s4))
                notes.append("i1  %f %f 1000 %f 2 0.8 %f %f %f %f" % (timer, noteDur, freq, s1, s2, s3, s4))
                notes.append("i1  %f %f 1000 %f 2 0.2 %f %f %f %f" % (timer, noteDur, freq, s1, s2, s3, s4))
                timer += value[1] * 0.9
            
            notes.append("i2 0 -1")

            # Give me the csd file, please
            csdMaker = CsoundProcessor(config = self.config)
            instruments = csdMaker.loadInstruments(instrumentList, instrumentPrefix = csdMaker.instrumentPrefix)
            csd = csdMaker.makeCSD(instruments, fTables, notes)
            
            chunkNumber = 0
            self.logger.debug("Drone: Working on part %d of %d" % (partNumber, numParts - 1))
            mp3File = self._makeCsoundChunks(csd, partNumber, tempDir = tempDir)
            mp3Filenames.append(mp3File)

        # Okay, got all of our mp3 files, let's finish wrapping them            
        self.logger.debug("Drone: wrapping mp3")
        self._wrapMp3Files(mp3Filenames, "Drone")

        # And finally, cleanup
        shutil.rmtree(tempDir)


    # Processing the news
    def NewsProgram(self):
        """Make a news program."""
        self.logger.info("News Program: Making the News")
        newsString = ""
        currentTime = time.strftime("%A, %d %B, %Y")
        newsString += "This is the news for " + currentTime + "\n\n"
      
        # For later headlines and summaries
        # TODO
        # make configurable somewhere?
        interestingCompanies = ["Sage Publications", "Springer Verlag", "Taylor and Francis", "MIT Press", "Nature Publishing", "Emerald Group Publishing", "Bentham Science Publishers", "Maney Publishing"]

        # Get the news data for the companies with stock symbols
        newsData = {}
        c = Companies(config = self.config)
        
        for company in c.companyDict.keys():
            newsData[company] = c.getCompanyInfo(company, numEntries = 5)

        newsString += "We start, as always, with the markets.\n\n"
        
        for company in newsData.keys():
            data = newsData[company]
            stocks = data["stocks"]
            for stock in stocks:
                name = stock[0]
                code = stock[1]
                price = stock[2]
                change = stock[3]
                date = stock[4]
                timeTraded = stock[5]
                volume = stock[6]
                newsString += "%s, with stock code %s, had a price of %s at %s on a change of %s and volume of %s" % (name, code, str(price), timeTraded, str(change), str(volume))
                newsString += "\n\n"
        
        newsString += "And now, for the news.\n\n"
        
        # Now add the other companies
        for company in interestingCompanies:
            newsData[company] = c.getCompanyInfo(company, numEntries = 5)
        
        # And create our strings
        for company in newsData.keys():
            newsString += "This is the news for %s\n\n" % company 

            items = zip(newsData[company]["headlines"], newsData[company]["summaries"])

            for item in items:
                newsString += "The headline is %s.\n\n%s\n\n\n" % (item[0], item[1])
        
        # And finally, the trending words
        newsString += "And finally, the top trending words by price, taken from the words in the journal names and their owners in our database of over 16000 journals.\n\n"
        p = PPCDocuments(config = self.config)
        pXML = p.getTrendingWordsByPrice()
        for element in list(pXML):
            name = element.get("name")
            price = element.get("price")
            newsString += "%s has a price of %s cents.\n" % (name, price) 
        
        self._makeTTSFileChunks(voice = None, text = newsString, title = "NewsProgram")

        self.archiveShow("NewsProgram", playlist = newsString)

    # TODO
    # better name :-)
    def Noise(self):
        """Taking the model files and turning them into noise!"""
        self.logger.info("Starting processing for Noise")
        soxPath = self.config.get("Sound", "soxPath")
        ffmpegPath = self.config.get("Sound", "ffmpegPath")
        outputPath = self.config.get("Sound", "outputPath")
        id3tagPath = self.config.get("Sound", "id3tagPath")

        stem = self.config.get("Model", "storagePath")
        dataPath = self.config.get("Model", "dataPath")
        suffixes = ["-po2s.db", "-so2p.db", "-sp2o.db"]
        sampwidths = [1, 2, 4]

        tempDir = tempfile.mkdtemp()

        waveFiles = []
        
        count = 0
        for suffix in suffixes:
            fp = open(stem + suffix, "r")
            data = fp.read()
            fp.close()
            for sampwidth in sampwidths:
                waveFiles.append(self._makeWaveFile(data, tempDir, filename = "wave" + str(count), sampwidth = sampwidth))
                count += 1

        # Add in output.rdf
        fp = open(os.path.join(dataPath, "output.rdf"), "rb")
        data = fp.read()
        fp.close()

        for sampwidth in sampwidths:
            waveFiles.append(self._makeWaveFile(data, tempDir, filename = "rdf" + str(count), sampwidth = sampwidth))
            count += 1

        # Add 2s padding at end of each file
        newWaveFiles = []
        self.logger.debug("Noise: Padding input files")
        for file in waveFiles:
            processPad = subprocess.call([soxPath, os.path.join(tempDir, file), os.path.join(tempDir, "pad_" + file), "pad", "0", "2"], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            newWaveFiles.append(os.path.join(tempDir, "pad_" + file))

        # Reorder
        random.shuffle(newWaveFiles)
        
        # Concatenate
        self.logger.debug("Noise: Concatenating files")
        command = [soxPath]
        for file in newWaveFiles:
            command.append(file)
        command.append(os.path.join(tempDir, "output.wav"))
        # Do the concatenation
        processConcat = subprocess.call(command, shell=False)

        # Convert
        programRef = "Noise"
        outputFilename = os.path.join(tempDir, "output.wav")
        processConversion = subprocess.call([ffmpegPath, "-y", "-i", outputFilename, outputPath + "/%s.mp3" % programRef], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Tag
        processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % programRef, "--year=2010", "--comment='Visit http://journalofjournalperformancestudies.org for more information.'", outputPath + "/%s.mp3" % programRef], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        self.archiveShow("Noise", playlist = None)

        # And finally, cleanup
        shutil.rmtree(tempDir)

    def Genealogies(self):
        """Genealogy of a particular owner."""

        model = Model(config = self.config)

        options = ["Elsevier", "SagePublications", "Springer", "JohnWileyAndSons", "TaylorAndFrancis"]

        # Inefficient, I know...
        company = random.choice(options)
        self.logger.debug("Genealogies: Getting owner info for %s" % company)
        dataXML = etree.fromstring(model.getJournalsOwnedBy(company))
        
        ownerText = "Welcome to Genealogies, where we let you know how journals are related to owners are related to parents.  Listen as the list continues on forever...\n\n"
        for item in list(dataXML):
            parent = item.get("parent")
            journal = item.get("journal")
            ownerText += "%s owns %s that owns %s.\n\n" % (company, parent, journal)

        self._makeTTSFileChunks(voice = None, text = ownerText, title = "Genealogies")
        self.archiveShow("Genealogies", playlist = ownerText)
    
    def Conjunctional(self):
        """Reading out only the conjunctions.  Other words are played backwards."""
        # Get a random document from the database
        #docIDs = [item for item in self.db if item.find("_design") == -1]
        docID = random.choice(self.articleDocuments.docIDs)
        data = self.articleDocuments.get(docID)

        self.logger.debug("Conjunctional: tokenizing words")
        # Tokenize our data into an ordered list of words
        text = data["articleText"]
        tokens = self._makeTokens(text)
        
        # Then, get a syllable mapping
        self.logger.debug("Conjunctional: counting syllables")
        from nltk_contrib.readability import syllables_en
        words = data["tf_idf"].keys()
        syllables = {}
        for word in data["tf_idf"].keys():
            syllables[word] = syllables_en.count(word)

        # Get a list of stopwords
        stopwords = nltk.corpus.stopwords.words("english")

        self.logger.debug("Conjunctional: creating TTS words")
        # Get a list of TTSed words to use
        tempDir = tempfile.mkdtemp()
        # Bias the words
        numWords = [(word, tfIdf) for word, tfIdf in data["tf_idf"].items()]
        numWords = sorted(numWords, key=itemgetter(1), reverse = True)
        wordList = [word[0] for word in numWords]
        totalWords = 400
        wordList = wordList[0:totalWords]
        wordList.extend(stopwords)

        TTSWords = self.makeTTSWords(tempDir, wordList, numWords = len(wordList))
        TTSPossibleWords = [word[0] for word in TTSWords]

        self.logger.debug("Conjunctional: creating instruments")
        
        instruments = []
        for word in TTSWords:
            if (word[0] in stopwords):
                direction = 1
            else:
                direction = -1
            instr = "instr %d\n"
            instr += """asig diskin "%s", %d
outs asig, asig
    endin\n\n""" % (word[1], direction)
            instruments.append(instr)
        
        # 200 words is about ?
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
                    instrNumber = wordList.index(token)
                except ValueError:
                    instrNumber = 0
    
                try:
                    syllableCount = syllables[token]
                except KeyError:
                    syllableCount = 0
    
                if (instrNumber != 0):
                    notes.append("i%d %f %f" % (instrNumber, time, syllableCount * 1))
                time += syllableCount * 1
    
            # Give me the csd file, please
            csdMaker = CsoundProcessor(config = self.config,  orcOptions = {'sr': 16000, 'kr': 1600,    'ksmps': 10, 'nchnls': 2})
            csd = csdMaker.makeCSD(instruments, "", notes)
            
            self.logger.debug("Conjunctional: on chunk %d of %d" % (chunkNumber, numChunks - 1))
            mp3File = self._makeCsoundChunks(csd, chunkNumber, tempDir = tempDir, resample = 44100)
            mp3Filenames.append(mp3File)

        # Okay, got all of our mp3 files, let's finish wrapping them            
        self.logger.debug("Conjunctional: wrapping mp3")
        self._wrapMp3Files(mp3Filenames, "Conjunctional")

        # And finally, cleanup
        shutil.rmtree(tempDir)

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

    def RecitationHour(self):
        self.logger.info("Recitation Hour: starting processing...")
        # Get list of documents
        #docIDs = [item for item in self.db if item.find("_design") == -1]
        docID = random.choice(self.articleDocuments.docIDs)
        #doc = self.db[docID]
        doc = self.articleDocuments.get(docID)
        title = doc["title"]
        try:
            journalName = doc["journal"]
        except KeyError:
            journalName = "nowhere"
        authors = doc["authors"].replace(",", "and ")
        text = doc["articleText"]
        self.logger.debug("Recitation Hour: TTS")
        self._makeTTSFileChunks(voice = None, text = "Now, %s from %s by %s.  %s" % (title, journalName, authors, text), title = "Recitation Hour")
        
        codedText = self.createTextTransmission(text)
        self.archiveShow("RecitationHour", playlist = codedText)

        self.logger.info("Recitation Hour: done")

    def CopyHour(self):
        self.logger.info("CopyHour: starting processing...")
        d = CopyrightDocuments(config = self.config)
        docID = random.choice(d.docIDs)
        doc = d.get(docID)
        title = doc["title"]
        text = doc["articleText"]
        self.logger.debug("Copy Hour: TTS")
        self._makeTTSFileChunks(voice = None, text = "Now on the air: a recitation of copyright agreements.  Make sure your legal-speak to normal-speak dictionary is handy.  Enjoy.  %s.  %s" % (title, text), title = "Copy Hour")
        
        self.archiveShow("CopyHour", playlist = text)

        self.logger.info("Copy Hour: done")

    def OpenAccess(self):
        self.logger.info("OpenAccess: starting processing...")
        d = OpenAccessDocuments(config = self.config)
        docID = random.choice(d.docIDs)
        doc = d.get(docID)
        title = doc["title"]
        text = doc["articleText"]
        journal = doc["journal"]
        authors = doc["authors"]
        self.logger.debug("Open Access: TTS")
        self._makeTTSFileChunks(voice = None, text = "Now on the air: a recitation of articles that are available in open access journals.  These documents are freely available on the internet.  Be sure to visit the site of the journal for more information.  Enjoy.  %s, by %s from %s.  %s" % (title, authors, journal, text), title = "Open Access Hour")
        
        self.archiveShow("OpenAccessHour", playlist = text)

        self.logger.info("Open Access: done")


    def CutupHour(self):
        self.logger.info("Cutup Hour: starting processing...")

        #docIDs = [item for item in self.db if item.find("_design") == -1]
        docIDs = self.articleDocuments.docIDs
        totalNumSentences = 350
        numSentencesToGet = int(totalNumSentences)/int(len(docIDs))
        
        self.logger.debug("Cutup Hour: getting fragments")
        cutupSentences = []
        for docID in docIDs:
            doc = self.articleDocuments.get(docID)
            sentences = nltk.sent_tokenize(doc["articleText"])
            if (numSentencesToGet >= len(sentences)):
                numSentencesToGet = len(sentences)
            cutupSentences.extend(random.sample(sentences, numSentencesToGet))
        
        random.shuffle(cutupSentences)
        text = "This is the Cutup Hour, where we select random fragments from our archives and reassemble them into something new.  Enjoy.  "
        text += "  ".join(cutupSentences)
        
        self.logger.debug("Cutup Hour: TTS")
        self._makeTTSFileChunks(voice = None, text = text, title = "Cutup Hour")

        self.archiveShow("CutupHour", playlist = text)
        self.logger.info("Cutup Hour: done")

    def WhatstheFrequencyKenneth(self):
        self.logger.info("What's the Frequency Kenneth: starting processing...")
        
        #docIDs = [item for item in self.db if item.find("_design") == -1]
        docIDs = self.articleDocuments.docIDs
        
        docID = random.choice(docIDs)
        self.logger.debug("What's the Frequency Kenneth: calculating the number of words")
        #data = self.db[docID]
        data = self.articleDocuments.get(docID)
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

        self.archiveShow("WhatstheFrequencyKenneth", playlist = text)
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

        processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % programRef, "--year=2010", "--comment='Visit http://journalofjournalperformancestudies.org for more information.'", outputPath + "/%s.mp3" % programRef], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Cleanup
        os.remove(tempFilename)

    def _makeWaveFile(self, data, tempDir, filename = "test", nchannels = 2, sampwidth = 1, framerate = 44100):
        """Make a wave file in the given temp directory."""
        import wave

        filename = filename + ".wav"
        w = wave.open(os.path.join(tempDir, filename), "wb")
        w.setnchannels(nchannels)
        w.setsampwidth(sampwidth)
        w.setframerate(framerate)
        w.writeframes(data)
        w.close()

        return filename

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
        
        mp3Filenames = []
        if (len(sentences) > chunkSize):
            numSentences = len(sentences)

            startSentence = 0
            endSentence = chunkSize - 1
            
            # Get the total number of times we should run this chunk process
            numChunks = int(math.ceil(float(numSentences)/float(chunkSize)))

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
                titleNospaces = title.replace(" ", "").replace("'", "")
                titleNospacesChunk = "%s%03d" % (titleNospaces, index)
                

                # TODO
                # Need to figure out why I can't choose a particular voice
                self.logger.debug("TTS Chunks: Starting TTS and MP3 encoding processes for show %s and chunk %03d of %03d" % (title, index, numChunks-1))
                processTTS = subprocess.Popen([text2wavePath, tempFilename], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        
                processConversion = subprocess.Popen([ffmpegPath, "-y", "-i", "-", "-ar", "44100", tempfile.tempdir + "/%s.mp3" % titleNospacesChunk], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        
                # Pass the TTS output to the communicate input
                processConversion.communicate(processTTS.communicate()[0])

                # Cleanup
                os.remove(tempFilename)

                mp3Filenames.append(tempfile.tempdir + "/%s.mp3" % titleNospacesChunk)
            
        else:
            # Create temp file to hold text
            tempFH, tempFilename = tempfile.mkstemp(suffix = ".txt", prefix = "JJPS")
            tempFP = os.fdopen(tempFH, "wb")
            tempFP.write(text.encode("ascii", "ignore"))
            tempFP.close()

            # Create no spaces version of show name with trailing zeros
            titleNospaces = title.replace(" ", "").replace("'", "")
            

            # TODO
            # Need to figure out why I can't choose a particular voice
            self.logger.debug("TTS Chunks: Starting TTS and MP3 encoding processes for show %s" % (title))
            processTTS = subprocess.Popen([text2wavePath, tempFilename], shell=False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    
            processConversion = subprocess.Popen([ffmpegPath, "-y", "-ar", "44100", "-i", "-", tempfile.tempdir + "/%s.mp3" % titleNospaces], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    
            # Pass the TTS output to the communicate input
            processConversion.communicate(processTTS.communicate()[0])

            # Cleanup
            os.remove(tempFilename)

            mp3Filenames.append(tempfile.tempdir + "/%s.mp3" % titleNospaces)
        
        # Finish cleaning up the mp3 files
        if (len(mp3Filenames) != 1):
            # Wrap MP3 files
            self.logger.debug("TTS Chunks: Wrapping files")
            processCall = [mp3wrapPath, outputPath + "/%s.mp3" % titleNospaces]
            processCall.extend(mp3Filenames)
            
            # Use call so that we don't immediately go to move command below
            processMP3Wrap = subprocess.call(processCall, shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    
            # Unfortunately mp3wrap adds an annoying suffix to every file
            # We need to move the file to get rid of it
            shutil.move(outputPath + "/%s_MP3WRAP.mp3" % titleNospaces, outputPath + "/%s.mp3" % titleNospaces)
        else:
            shutil.copy(mp3Filenames[0], outputPath + "/%s.mp3" % titleNospaces)

        # Tag files
        self.logger.debug("TTS Chunks: Tagging file")
        processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % title, "--year=2010", "--comment='Visit http://journalofjournalperformancestudies.org for more information.'", outputPath + "/%s.mp3" % titleNospaces], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        # Cleaning up
        self.logger.debug("Cleaning up")
        for file in mp3Filenames:
            os.remove(file)

    def PhasorModFreq(self):
        """Nothing..."""

        tempDir = tempfile.mkdtemp()

        docID = random.choice(self.articleDocuments.docIDs)
        data = self.articleDocuments.get(docID)
        text = data["articleText"]
        tf_idf = data["tf_idf"]

        # Do all of our computations first
        sentences = nltk.sent_tokenize(text)

        tokens = []
        for sentence in sentences:
            tokens.append(self._makeTokens(sentence))
        
        allSyllables = []
        allWords = []
        allTFIDF = []
        from nltk_contrib.readability import syllables_en

        for tokenSet in tokens:
            syllablesSet = []
            wordsSet = []
            tfIdfs = []
            for word in tokenSet:
                numSyllables = syllables_en.count(word)
                
                try:
                    if (tf_idf[word] != 0.0):
                        tfIdfs.append(math.log(tf_idf[word]))
                except KeyError:
                    continue

                if (numSyllables != 0):
                    syllablesSet.append(numSyllables)
                    wordsSet.append(len(word))
            
            if (len(tfIdfs) == 0):
                allTFIDF.append(4)
            else:
                allTFIDF.append(-1 * min(tfIdfs))
            allSyllables.append(syllablesSet)
            allWords.append(wordsSet)
        
        # our instrument
        instrumentList = ["drumSimple.instr", "bassSimple.instr", "phaseModSimple.instr"]
        
        # All of our notes
        allNotes = []

        fTables = []
        fTables.append("f1 0 65537 10 1")
        fTables.append("f2  0 1024  7 1 1024 1")
        fTables.append("f   3       0           65536       13      1   1   0   3   0   2")
        fTables.append("f5 0 512 20 2 ; hanning window")

        notes = []
        
        timer = 0
        duration = 0.4

        fundamental = 200.0
        prior = 1.0
        sweepSets = [[5000, 8000, 5000], [100, 1000, 500], [250, 5500, 500], [250, 500, 300]]
        
        print len(allSyllables)
        chunkSize = 60
        numSyllableSets = len(allSyllables)
        numChunks = math.ceil(numSyllableSets/chunkSize)

        mp3Filenames = []
        for chunkNumber in xrange(numChunks):
            startSet = chunkNumber*chunkSize
            endSet= min((chunkNumber+ 1)*chunkSize - 1, numSyllableSets)

            currentSyllableSets = allSyllables[startSet:endSet]
            currentWordSets = allWords[startSet:endSet]

            for (syllableSet, wordsSet) in zip(currentSyllableSets, currentWordSets):
                numSyllables = len(syllableSet)
                if (numSyllables == 0):
                    continue
                
                counter = 0
                numBassBeats = 5
                if (numBassBeats > numSyllables):
                    numBassBeats = numSyllables
    
                bassBeatTimes = random.sample(xrange(numSyllables), numBassBeats)
                bassBeatTimes.sort()
                notesTimes = random.sample(xrange(numSyllables), numBassBeats)
    
                for (syllables, words) in zip(syllableSet, wordsSet):
                    sweepSet = random.choice(sweepSets)
                    noteDuration = float(duration / (syllables * 4))
                    
                    try:
                        bassBeatTimes.index(counter)
                        notes.append("i2 %f %f 5000" % (timer, 0.8))
                    except ValueError:
                        pass
                    
    
                    if ((counter % 8) == 0):
                        notes.append("i3 %f %f 4000 %f" % (timer, words, float((float(prior)/float(words))) * fundamental))
                        prior = float(words)
    
    
                    for x in xrange(syllables*4):
                        notes.append("i1 %f %f 2500 %d %d %d" % (timer, noteDuration, sweepSet[0], sweepSet[1], sweepSet[2]))
                        timer += noteDuration
                    
                    counter += 1
    
            # Give me the csd file, please
            csdMaker = CsoundProcessor(config = self.config)
            instruments = csdMaker.loadInstruments(instrumentList, instrumentPrefix = csdMaker.instrumentPrefix)
            csd = csdMaker.makeCSD(instruments, fTables, notes)

            self.logger.debug("PhasorModFreq: on chunk %d of %d" % (chunkNumber, numChunks))
            mp3File = self._makeCsoundChunks(csd, chunkNumber, tempDir = tempDir)
            mp3Filenames.append(mp3File)

        # Okay, got all of our mp3 files, let's finish wrapping them            
        self.logger.debug("PhasorModFreq: wrapping mp3")
        self._wrapMp3Files(mp3Filenames, "PhasorModFreq")

        # TODO
        # Only archiving one chunk of the grain csd now...
        self.archiveShow("PhasorModFreq", playlist = csd)

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

        docID = random.choice(self.articleDocuments.docIDs)

        data = self.articleDocuments.get(docID)
        pdfName = data["_attachments"].keys()[0]
        pdfFP = self.articleDocuments.db.get_attachment(data, pdfName)

        #pdfFP = open(os.path.join(pdfPath, "Land1993.pdf"), "r")

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
        self.archiveShow("Telegraph", playlist = csd)

        # Close our PDF file
        pdfFP.close()

    def GrainCombine(self):
        #docIDs = [item for item in self.db if item.find("_design") == -1]
        docIDs = self.articleDocuments.docIDs
        docID = random.choice(docIDs)
        data = self.articleDocuments.get(docID)

        self.logger.debug("Grain Combine: tokenizing words")

        # Tokenize our data into an ordered list of words
        text = data["articleText"]
        tokens = self._makeTokens(text)
        
        # Then, get a syllable mapping
        self.logger.debug("Grain Combine: counting syllables")
        from nltk_contrib.readability import syllables_en
        # TODO
        # Deal with when we don't have tf_idf...we (nearly) always should, but we should loop until we can get a working id
        words = data["tf_idf"].keys()
        syllables = {}
        for word in data["tf_idf"].keys():
            syllables[word] = syllables_en.count(word)

        # our instrument
        instrumentList = ["grainSimple.instr"]
        
        # All of our notes
        allNotes = []

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
                    notes.append("i1 %f %f 4500 %d 5 0.1 200 200 %f %f" % (time, 1 + syllableCount * 1, 1, 0.01, 0.01))
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

        # TODO
        # Only archiving one chunk of the grain csd now...
        self.archiveShow("GrainCombine", playlist = csd)

    def Feldman(self):
        """In the sparse style of Morton Feldman"""

        # Get random text from database
        #docIDs = [item for item in self.db if item.find("_design") == -1]
        docIDs = self.articleDocuments.docIDs
        docID = random.choice(docIDs)
        #data = self.db[docID]
        data = self.articleDocuments.get(docID)

        tokens = self._makeTokens(data["articleText"], clean = False)

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


    def _makeCsoundChunks(self, csd, chunkNumber, tempDir = None, useStdout = False, resample = False, bitrate = "128k"):
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
            if resample:
                processConversion = subprocess.call([ffmpegPath, "-y", "-ar", str(resample), "-ab", bitrate, "-i", outputPathWav, outputPathMp3], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            else:
                processConversion = subprocess.call([ffmpegPath, "-y", "-ab", bitrate, "-i", outputPathWav, outputPathMp3], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            
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
        processTag = subprocess.Popen([id3tagPath, "--artist='Journal of Journal Performance Studies'", "--album='Journal of Journal Performance Studies'", "--song='%s'" % title, "--year=2010", "--comment='Visit http://journalofjournalperformancestudies.org for more information.'", outputPath + "/%s.mp3" % titleNospaces], shell=False, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

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

    def archiveShow(self, programRef, playlist = None):
        """Archive the show materials for the given show.  The writing of the archive materials to the station XML file occurs when we switch programs.  We know that we can always copy the given programRef.mp3 file to the archive directory as we always overwrite it on each process run."""
        archivePath = self.config.get("Sound", "archivePath")
        programArchivePath = os.path.join(archivePath, programRef)
        outputPath = self.config.get("Sound", "outputPath")

        # Try to create the directory for the archived show
        try:
            os.mkdir(programArchivePath)
        except OSError:
            # Assume that if we get an error, the path already exists
            # TODO
            # bad assumption :-)
            pass

        # Copy the mp3 file to the archive directory
        shutil.copy2(os.path.join(outputPath, programRef + ".mp3"), os.path.join(programArchivePath, programRef + "Current.mp3"))

        if (playlist is not None):
            # Write the playlist to the archive directory
            fp = codecs.open(os.path.join(programArchivePath, programRef + "CurrentPlaylist.txt"), "w", "utf-8")
            fp.write(playlist)
            fp.close()



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

    def __init__(self, config = None, orcOptions = {'sr': 44100, 'kr': 4410, 'ksmps': 10, 'nchnls': 2}, commandOptions = "-d ; suppress displays"):
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
