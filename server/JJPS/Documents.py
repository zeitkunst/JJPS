"""Dealing with documents in couchdb"""

import codecs
import csv
import hashlib
from math import log
import operator
import os
import random
import subprocess

import couchdb
import BeautifulSoup
from lxml import etree
from pybtex.database.input import bibtex

# My libraries
import Log
import Text
import Model

class DocumentBase(object):

    all_docs_count = {"map": """function(doc) {
    if ("tf" in doc) {
        emit(null, 1);
    }
}""",
        "reduce": """function(keys, values) {
    return sum(values);
}"""}
    
    docfreq = {"map": """function(doc) {
    if ("tf" in doc) {
        for (term in doc.tf) {
            emit(term, 1);
        }
    }
}""",
        "reduce": """function(keys, values) {
    return sum(values);
}"""}

    def __init__(self, config = None, hashKeys = ["title", "authors"]):
        """Initialize the document processing code.

        The id in couchdb is computed from a sha256 hash of two keys in the dataDict.  You can set those keys by passing a "hashKeys" parameters.  Even if you only have one key in your database, you have to pass two hashKeys...so just pass the same key twice :-)  
        IMPORTANT!  You need to keep the order of the keys in the "hashKeys" list consistent, otherwise you'll get new IDs when you had thought you were working with the same data ;-)"""

        self.config = config

        self.logger = Log.getLogger(config = self.config)
        self.hashKeys = hashKeys

    def clearDatabase(self, really = False):
        """Delete all documents in the database.  Pass really=True to actually do it."""
        # WARNING: THIS WILL REMOVE ALL DOCUMENTS IN THE DATABASE!
        # IT WILL ONLY KEEP BEHIND THE DESIGN DOCUMENTS!
        if really:
            self.logger.warn("Deleting all documents in the database!")
            for result in self.db:
                if (result.find("_design") == -1):
                    doc = self.db[result]
                    self.db.delete(doc)

    def get(self, docID):
        """Return a document with the given ID."""

        return self.db[docID]

    def addDocument(self, dataDict, showName = False, fp = None):
        """Add the document in dataDict to the database.  Create an ID based on the hash of the title and author values."""
        
        # Create an id based on the hash of the title and author
        key1 = self.hashKeys[0]
        key2 = self.hashKeys[1]
        id = hashlib.sha256(dataDict[key1].encode("ascii", "ignore") + dataDict[key2].encode("ascii", "ignore")).hexdigest()

        dataDict["_id"] = id
        if (showName):
            self.logger.debug("Adding document \"%s\" to the database" % dataDict[key1])

        try:
            id, rev = self.db.save(dataDict)
        except couchdb.http.ResourceConflict:
            document = self.db[id]
            rev = document["_rev"]
            dataDict["_rev"] = rev
            self.db.save(dataDict)
        
        # Try and add the attachment, if given
        if (fp is not None):
            doc = self.db[id]
            self.db.put_attachment(doc, fp)

    def addDocumentByName(self, name, dataDict):
        """Add the document in dataDict to the database.  Name of document is given by method argument."""
        
        id = name

        dataDict["_id"] = id
        self.logger.debug("Adding document \"%s\" to the database" % name)
        try:
            id, rev = self.db.save(dataDict)
        except couchdb.http.ResourceConflict:
            document = self.db[id]
            rev = document["_rev"]
            dataDict["_rev"] = rev
            self.db.save(dataDict)

    def computeTF(self, recompute = True, keysToTokenize = ["articleText"], keyToDisplay = "title"):
        """Compute the TF for every document in the database.  Keys to draw text from to tokenize are given in "keysToTokenize".  Optionally, don't recompute."""

        ifMap = """function(doc) { 
        if (!('tf' in doc)) 
            emit(doc._id, null); 
        }"""

        if recompute:
            results = self.db
        else:
            results = self.db.query(ifMap)

        self.logger.debug("Computing TF")
        for result in results:
            try:
                # if we're recomputing...
                if (result.find("_design") != -1):
                    continue
                doc = self.db[result]
            except AttributeError:
                # otherwise, just get the key
                doc = self.db[result["key"]]

            self.logger.debug("Computing TF: Working on \"%s\"" % doc[keyToDisplay])
            # Get the text to use
            textToTokenize = ""
            for key in keysToTokenize:
                textToTokenize += doc[key] + "\n"
            tokens = Text.tokenize(textToTokenize)
            numTokens = len(tokens)
            doc['numTokens'] = numTokens
            doc['tf'] = Text.get_term_freq(tokens)
            self.addDocument(doc)


    def computeTFIDF(self, keyToDisplay = "title"):
        """Run the TF-IDF computation."""

        self.logger.debug("Computing IDF")
        # The number of documents in the database (exclude design docs).
        for result in self.db.view('_design/test/_view/all_docs_count'):
            num_docs = result.value
        
        # Document frequency.  Number of documents a term appears in.
        self.logger.debug("Computing document frequency")
        df = {}
        for result in self.db.view('_design/test/_view/docfreq', group=True):
            df[result.key] = log(float(num_docs)/float(result.value))    

        self.logger.debug("Computing TF-IDF")
        # Compute tf-idf for each document.
        for result in self.db.query('''function(doc) { if (!('tf_idf' in doc)) emit(doc._id, null); }'''):
            doc = self.db[result.key]
            self.logger.debug("Computing TF-IDF: Working on \"%s\"" % doc[keyToDisplay])
            tf = doc['tf']
            tf_idf = {}
            for k, v in tf.items(): # By construction, there should never be KeyError's here...except there are :-(
                try:
                    tf_idf[k] = v * df[k]
                except KeyError:
                    continue
            doc['tf_idf'] = tf_idf
            self.addDocument(doc)

    def getWordFrequency(self):
        """Return an ordered set of word frequency."""
        self.logger.debug("Getting sorted word frequency from database")
        wordFreq = {}
        for result in self.db.view('_design/test/_view/docfreq', group=True):
            wordFreq[result.key] = result.value
        
        wordFreq = sorted(wordFreq.iteritems(), key = operator.itemgetter(1))
        wordFreq.reverse()

        return wordFreq

    def preprocessWebData(self, dataDict):
        """Preprocess the web-based data in dataDict."""
        newDataDict = {}
        
        # Article text
        soup = BeautifulSoup.BeautifulSoup(dataDict["articleText"])
        # Go two levels down
        articleText = u""
        for element in soup.contents:
            try:
                for element2 in element.contents:
                    try:
                        articleText += unicode(element2.text).strip() + "\n"
                    except AttributeError:
                        articleText += unicode(element2).strip() + "\n"
            except AttributeError:
                articleText += unicode(element).strip() + "\n"
        newDataDict["articleText"] = articleText        

        # Title
        soup = BeautifulSoup.BeautifulSoup(dataDict["title"])
        newDataDict["title"] = soup.text

        # Authors
        soup = BeautifulSoup.BeautifulSoup(dataDict["authors"])
        
        # Go two levels deep, only get strings
        authors = ""
        for element in soup.contents:
            try:
                for element2 in element.contents:
                    if (type(element2) == BeautifulSoup.NavigableString):
                        if (element2 is not None):
                            authors += element2
            except AttributeError:
                pass
        newDataDict["authors"] = authors

        # Nothing to do with the journal title
        newDataDict["journalTitle"] = dataDict["journalTitle"]

        return newDataDict

    def preprocessPDFData(self, text):
        """Preprocess the pdftotext data before we add it to the database."""

        newlines = []
        for line in text:
            if (line[0] == "\x0C"):
                if (len(line) >= 150):
                    newlines.append(line)
            else:
                newlines.append(line)
        
        textNew = "".join(newlines)
        textNew = textNew.replace(".", ". ")
        textNew = textNew.replace(",", ", ")
        return textNew.decode("utf-8")

    def initViews(self):
        """Initialize with the standard views."""

        view = couchdb.design.ViewDefinition("test", "all_docs_count", self.all_docs_count["map"], reduce_fun = self.all_docs_count["reduce"])
        view.get_doc(self.db)
        view.sync(self.db)

        view = couchdb.design.ViewDefinition("test", "docfreq", self.docfreq["map"], reduce_fun = self.docfreq["reduce"])
        view.get_doc(self.db)
        view.sync(self.db)


    def addBibtexArticles(self, bibtexPath = None, desiredArticles = [], numArticles = 20, pdfHome = "/home/nknouf/Papers/Database"):
        """Add a random subset of bibtex articles to the database, in addition to the desired articles given in the list."""
        
        if (bibtexPath is None):
            return

        parser = bibtex.Parser()
        self.logger.debug("Reading in bibtex file %s" % bibtexPath)
        bib_data = parser.parse_file(bibtexPath)
        entryKeys = bib_data.entries.keys()
        
        articleKeys = []
        for key in entryKeys:
            if (bib_data.entries[key].type == "article"):
                articleKeys.append(key)
                pass

        if (numArticles > len(articleKeys)):
            numArticles = len(articleKeys)
        articleKeys = random.sample(articleKeys, numArticles)
        articleKeys.extend(desiredArticles)

        for key in articleKeys:
            dataDict = {}
            article = bib_data.entries[key]
            try:
                file = article.fields["file"]
            except KeyError:
                # If no file, continue
                continue
            
            # For the moment, assume all files are PDF (don't try and parse more of the file field)
            dataDict["file"] = file.split(":")[1]

            # Add other infos to the dataDict
            try:
                dataDict["title"] = article.fields["title"]
                dataDict["journal"] = article.fields["journal"]
                dataDict["authors"] = self._getAuthorList(bib_data.entries[key].persons["author"])
            except KeyError:
                continue
            
            pdfFile = os.path.join(pdfHome, dataDict["file"])
            dataDict["articleText"] = self.getArticleText(pdfFile)
            
            try:
                fp = open(pdfFile, "rb")
                self.addDocument(dataDict, fp = fp)
                fp.close()
            except IOError:
                continue

    def getArticleText(self, pdfFile):
        self.logger.debug("Converting %s to text" % pdfFile)
        processPDF = subprocess.Popen([self.config.get("Documents", "pdfToTextPath"), "-layout", pdfFile, "-"], shell=False, stdout = subprocess.PIPE)
        text = processPDF.communicate()[0]
        
        return self.preprocessPDFData(text)

    def _getAuthorList(self, authorList):
        """Return a formatted list of authors based on the info in the bibtex entry."""
        authorListStr = ""
        for author in authorList:
            authorListStr += " ".join(author.first()) + " " + " ".join(author.middle()) + " " + " ".join(author.last()) + ", "
        
        # Remove final comma
        return authorListStr[0: len(authorListStr) - 2]

class JournalDocuments(DocumentBase):
    """Methods for processing the journal documents database."""

    ppcData = None
    ppcXML = None

    def __init__(self, config = None, dbName = "jjps_journals", hashKeys = ["journalName", "ownerName"]):
        super(JournalDocuments, self).__init__(config = config, hashKeys = hashKeys)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")
        
        # Setup the model
        self.model = Model.Model(config = self.config)

    def initDatabase(self):
        """Initialize the database with the journal and owner names from our model.
        THIS DESTROYS EVERYTHING IN THE DATABASE!!!"""

        self.clearDatabase(really = True)
        
        self.logger.debug("Getting journal names from model")
        self.journalNames = self.model.getJournalNames()
        
        count = 0
        self.logger.debug("Adding journal info to db")
        for journal in self.journalNames:
            dataDict = {}
            dataDict["ownerName"] = journal[0]
            dataDict["journalName"] = journal[1]
            self.addDocument(dataDict)
            count += 1
            if ((count % 100) == 0):
                self.logger.debug("On journal %d" % count)

    def writeWordLists(self):
        """Write a file with possible word lists for Google use."""
        self.logger.debug("Writing word list files")
        wordFreq = self.getWordFrequency()

        wordsList1 = wordFreq[0:500]
        wordsList2 = wordFreq[500:1000]

        fp = open(os.path.join("data", "wordsList1.txt"), "w")
        fp.write("\n".join([item[0] for item in wordsList1]))
        fp.close()
                           
        fp = open(os.path.join("data", "wordsList2.txt"), "w")
        fp.write("\n".join([item[0] for item in wordsList2]))
        fp.close()
    
    def updatePPCInfo(self):
        """Update the PPC info for the journals database from the PPC database."""
        
        self.logger.debug("Updating PPC info")
        ppcDocuments = PPCDocuments(config = self.config)
        ids = [id for id in self.db]
        
        count = 0
        for id in ids:
            if ((count % 100) == 0):
                self.logger.debug("Working on journal %d" % count)

            if (id.find("_design") != -1):
                continue
            
            data = self.db[id]
            # Try and get the current values
            try:
                currentClick = data["click"]
            except KeyError:
                currentClick = 0

            try:
                currentVolume = data["volume"]
            except KeyError:
                currentVolume = 0

            try:
                currentPPC = data["ppc"]
            except KeyError:
                currentPPC = 0

            text = data["ownerName"] + data["journalName"]
            ppcDataDict = ppcDocuments.makeClickInfo(text)
            data["deltaClick"] = ppcDataDict["click"] - float(currentClick) 
            data["deltaVolume"] = ppcDataDict["volume"] - float(currentVolume) 
            data["deltaPPC"] = ppcDataDict["ppc"] - float(currentPPC) 
            data.update(ppcDataDict)
            self.addDocument(data)

            count += 1

    def getPPCData(self, sortBy = "price", numItems = 10):
        """Get a set of PPC data for use in the ads.  Run only once per object initialization."""

        if (self.ppcXML is None):
            self.ppcData = []

            for result in self.db.view("_design/ppc/_view/ppcData"):
                self.ppcData.append(result["value"])
            
            if (sortBy == "price"):
                self.ppcData = sorted(self.ppcData, key = operator.itemgetter(3), reverse = True)
            elif (sortBy == "click"):
                self.ppcData = sorted(self.ppcData, key = operator.itemgetter(2), reverse = True)
            elif (sortBy == "volume"):
                self.ppcData = sorted(self.ppcData, key = operator.itemgetter(4), reverse = True)
            else:
                self.ppcData = sorted(self.ppcData, key = operator.itemgetter(3,2), reverse = True)

            self.ppcData = self.ppcData[0:numItems]

            journals = etree.Element("journals")
            journals.set("type", sortBy)

            for item in self.ppcData:
                journal = etree.Element("journal")
                journal.set("journalName", item[0])
                journal.set("ownerName", item[1])
                journal.set("click", str(item[2]))
                journal.set("price", str(item[3]))
                journal.set("volume", str(item[4]))
                journals.append(journal)

            self.ppcXML = journals

        return self.ppcXML

class PPCDocuments(DocumentBase):
    """Methods for processing ppc database."""

    def __init__(self, config = None, dbName = "jjps_ppc"):
        super(PPCDocuments, self).__init__(config = config)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")

    def addPPCInfo(self):
        """Add the PPC info to the database."""
        
        # TODO
        # Make this configurable?
        ppcFiles = ["data/ppc1.csv", "data/ppc2.csv"]

        # TODO
        # File has null bytes
        # Solution taken from: http://stackoverflow.com/questions/2243655/reading-csv-file-without-for
        def nonull(stream):
            for line in stream:
                yield line.replace('\x00', '')

        for file in ppcFiles:
            f = open(file, "rb")
            lines = csv.reader(nonull(f), delimiter="\t")

            data = [line for line in lines]
            # Drop the first line
            data = data[2:len(data) - 2]
            for item in data:
                word = item[0]
                dataDict = {}
                dataDict["lowPPC"] = item[3]
                dataDict["highPPC"] = item[4]
                dataDict["lowClick"] = item[7]
                dataDict["highClick"] = item[8]
                dataDict["volume"] = item[2]
                self.addDocumentByName(word, dataDict)
    
    def getPPCInfo(self, text):
        """Get PPC info from our database from the string given."""

        tokens = Text.tokenize(text)
        
        documents = []
        for token in tokens:
            try:
                documents.append(self.db[token])
            except couchdb.client.ResourceNotFound:
                continue

        return documents            

    def makeClickInfo(self, text):
        """Make a dictionary of click info for the given text.  Useful for updating entries in jjps_journals."""

        ppcInfo = self.getPPCInfo(text)
        count = float(len(ppcInfo))

        if (count == 0):
            dataDict = {}
            dataDict["click"] = 0
            dataDict["volume"] = 0
            dataDict["ppc"] = 0
            return dataDict

        dataDict = {}

        totalClick = 0
        totalVolume = 0
        totalPPC = 0

        for info in ppcInfo:
            if (info["highClick"] != "no data"):
                totalClick += float(info["highClick"].replace(",", ""))
            if (info["volume"] != "no data"):
                totalVolume += float(info["volume"])
            if (info["highPPC"] != "no data"):
                totalPPC += float(info["highPPC"][1:])

        dataDict["click"] = totalClick / count
        dataDict["volume"] = totalVolume / count
        dataDict["ppc"] = totalPPC / count

        return dataDict

    def getClickValue(self, text):
        """Return the click value for the given text.

        Click value is defined as the \sum_{i=0}^{n} \bar{\text{count}} \times \bar{\text{price}}, where the first term is the mean of the click values and the second term is the mean of the prices and the limit is the number of words in the text."""
        
        ppcInfo = self.getPPCInfo(text)

        total = 0

        for info in ppcInfo:
            click = (float(info["highClick"].replace(",", "")) + float(info["lowClick"].replace(",", "")))/2
            ppc = (float(info["highPPC"].replace("$", "")) + float(info["lowPPC"].replace("$", "")))/2
            total += click * ppc
        
        return total
    
    def getTrendingWordsByPrice(self, num = 40):
        """Get a list of the top trending words, sorted by price."""
        results = []

        for result in self.db.view("_design/ppc/_view/ppcVolume"):
            results.append(result["value"])

        results = sorted(results, key = operator.itemgetter(2))
        results.reverse()

        count = 0
        
        words = etree.Element("words")
        words.set("type", "price")
        for result in results:
            if (result[2] == "no data"):
                continue
            
            word = etree.Element("word")
            word.set("name", result[0])
            word.set("price", result[2])
            words.append(word)

            count += 1

            if (count == num):
                break

        return words

    def getTrendingWordsByVolume(self, num = 40):
        """Get a list of the top trending words, sorted by volume."""
        results = []

        for result in self.db.view("_design/ppc/_view/ppcVolume"):
            results.append(result["value"])

        results = sorted(results, key = operator.itemgetter(1))
        results.reverse()

        count = 0
        
        words = etree.Element("words")
        words.set("type", "volume")
        for result in results:
            if (result[1] == "no data"):
                continue

            word = etree.Element("word")
            word.set("name", result[0])
            word.set("price", result[2])
            words.append(word)

            count += 1

            if (count == num):
                break

        return words

class VoteDocuments(DocumentBase):
    """Methods for processing ppc database."""

    def __init__(self, config = None, dbName = None):
        super(VoteDocuments, self).__init__(config = config)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")

    def addVote(self, name, dataDict):
        """Add the document in dataDict to the database.  Name of document is given by method argument."""
        
        id = name.strip()

        # Try and get the data by the given id
        # If it doesn't exist, add the votes value to the dictionary
        try:
            data = self.db[id]
            dataDict["votes"] = int(data["votes"]) + 1
        except couchdb.client.ResourceNotFound:
            dataDict["votes"] = 1

        dataDict["_id"] = id
        self.logger.debug("Adding document \"%s\" to the database" % name)
        try:
            id, rev = self.db.save(dataDict)
        except couchdb.http.ResourceConflict:
            document = self.db[id]
            rev = document["_rev"]
            votes = int(document["votes"])
            dataDict["_rev"] = rev
            dataDict["votes"] = votes + 1
            self.db.save(dataDict)

class PriceDocuments(DocumentBase):
    """Methods for processing price database."""

    def __init__(self, config = None, dbName = "jjps_article_prices"):
        super(PriceDocuments, self).__init__(config = config)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")



class AdsDocuments(DocumentBase):
    """Methods for processing ppc database."""
    
    # Initial ad list
    initialAds = [ {"title": "Better your ASEO!", 
                    "content": "Improve your academic search engine optimization!",
                    "href": "http://journalofjournalperformancestudies.org/journal/index.php/jjps/article/view/6/6"},
                  {"title": "Measure author performance!",
                   "content": "Ensure your authors are writing optimally!",
                   "href": "http://journalofjournalperformancestudies.org/journal/index.php/jjps/article/view/6/6"},
                  {"title": "Googlable titles?",
                   "content": "Can your title be found via Google?  Take this test to find out!",
                   "href": "http://journalofjournalperformancestudies.org/journal/index.php/jjps/article/view/6/6"},
                  {"title": "Discover the hottest trends!",
                   "content": "Want to know what research is hot?  Check it out here!",
                   "href": "http://journalofjournalperformancestudies.org/journal/index.php/jjps/article/view/6/6"}]

    def __init__(self, config = None, dbName = "jjps_ads", hashKeys = ["title", "href"]):
        super(AdsDocuments, self).__init__(config = config, hashKeys = hashKeys)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")

    def initDatabase(self):
        """Initialize the ads database with our own subset.  Useful during our testing phases :-)"""

        self.clearDatabase(really = True)
        
        for ad in self.initialAds:
            self.addDocument(ad)

    def getAds(self):
        """Return a list of ads in XML format."""
        
        ids = [id for id in self.db]
        
        results = etree.Element("results")
        for id in ids:
            if (id.find("_design") != -1):
                continue
            
            result = etree.Element("result")
            data = self.db[id]
            result.set("title", data["title"])
            result.set("content", data["content"])
            result.set("href", data["href"])
            results.append(result)

        return results

class CopyrightDocuments(DocumentBase):
    
    docs = {"Elsevier": "ElsevierCopyright.txt",
                 "Taylor and Francis": "TaylorAndFrancisCopyright.txt",
                "MIT Press Institutional License": "MITPressInstitutionalLicense.txt",
                 "University of California Press Fair Use Guidelines":"UCPFairUseGuidelines.txt",
                 "MIT Press Journal Copyright Form": "MITPressJournalCopyrightForm.txt",
                 "Wiley-Blackwell Copyright Form": "WileyBlackwellCopyright.txt",
                 "Springer Copyright Agreement": "SpringerCopyright.txt",
            "Creative Commons Attribution Non-Commercial Share Alike": "CC-Attribution-NonCommercial-ShareAlike.txt",
            "Creative Commons Attribution Non-Commercial": "CC-Attribution-NonCommercial.txt"
    }

    def __init__(self, config = None, dbName = "jjps_copyright"):
        super(CopyrightDocuments, self).__init__(config = config, hashKeys = ["title", "title"])

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")
       
        # Get a list of IDs
        self.docIDs = [item for item in self.db if item.find("_design") == -1]

    def initDatabase(self):
        """Initialize the copyright database."""

        self.clearDatabase(really = True)
        
        dataPath = self.config.get("Model", "dataPath")
        copyrightFilesPath = os.path.join(dataPath, "journalCopyright")

        for title, filename in self.docs.items():
            dataDict = {}
            dataDict["title"] = title

            fp = codecs.open(os.path.join(copyrightFilesPath, filename), "r", "utf-8")
            dataDict["articleText"] = fp.read()
            fp.close()

            self.addDocument(dataDict)

class UploadDocuments(DocumentBase):
    """For documents that users upload."""

    def __init__(self, config = None, dbName = "jjps_upload"):
        super(UploadDocuments, self).__init__(config = config)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")
       
        # Get a list of IDs
        self.docIDs = [item for item in self.db if item.find("_design") == -1]


class ArticleDocuments(DocumentBase):

    def __init__(self, config = None, dbName = "jjps_articles"):
        super(ArticleDocuments, self).__init__(config = config)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")
       
        # Get a list of IDs
        self.docIDs = [item for item in self.db if item.find("_design") == -1]




    def clearDatabase(self, really = False):
        """Delete all documents in the database.  Pass really=True to actually do it."""
        # WARNING: THIS WILL REMOVE ALL DOCUMENTS IN THE DATABASE!
        # IT WILL ONLY KEEP BEHIND THE DESIGN DOCUMENTS!
        if really:
            self.logger.warn("Deleting all documents in the database!")
            for result in self.db:
                if (result.find("_design") == -1):
                    doc = self.db[result]
                    self.db.delete(doc)

class OpenAccessDocuments(DocumentBase):

    def __init__(self, config = None, dbName = "jjps_open"):
        super(OpenAccessDocuments, self).__init__(config = config)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        
        # Setup the db
        if (dbName is not None):
            self.db = self.dbServer[dbName]
        else:
            raise Exception("Need to provide db name")
       
        # Get a list of IDs
        self.docIDs = [item for item in self.db if item.find("_design") == -1]

