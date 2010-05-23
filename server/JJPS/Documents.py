"""Dealing with documents in couchdb"""

import hashlib
from math import log
import os
import random
import subprocess

import couchdb
import BeautifulSoup
from pybtex.database.input import bibtex

# My libraries
import Log
import Text

class Documents(object):

    def __init__(self, config = None):
        self.config = config

        self.logger = Log.getLogger(config = self.config)

        self.dbServer = couchdb.Server(self.config.get("Database", "host"))
        self.db = self.dbServer[self.config.get("Database", "name")]

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
            dataDict["title"] = article.fields["title"]
            dataDict["journal"] = article.fields["journal"]
            dataDict["authors"] = self._getAuthorList(bib_data.entries[key].persons["author"])

            dataDict["articleText"] = self.getArticleText(os.path.join(pdfHome, dataDict["file"]))

            self.addDocument(dataDict)

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

    def addDocument(self, dataDict):
        """Add the document in dataDict to the database.  Create an ID based on the hash of the title and author values."""
        
        # Create an id based on the hash of the title and author

        id = hashlib.sha256(dataDict["title"].encode("ascii", "ignore") + dataDict["authors"].encode("ascii", "ignore")).hexdigest()

        dataDict["_id"] = id
        self.logger.debug("Adding document \"%s\" to the database" % dataDict["title"])
        try:
            id, rev = self.db.save(dataDict)
        except couchdb.http.ResourceConflict:
            document = self.db[id]
            rev = document["_rev"]
            dataDict["_rev"] = rev
            self.db.save(dataDict)


    def computeTF(self, recompute = True):
        """Compute the TF for every document in the database.  Optionally, don't recompute."""

        ifMap = """function(doc) { 
        if (!('tf' in doc)) 
            emit(doc._id, null); 
        }"""

        if recompute:
            results = self.db
        else:
            results = self.db.query(ifMap)

        self.logger.debug("Computing TF")
        #for result in db.query(ifMap):
        for result in results:
            if (result.find("_design") != -1):
                continue
            doc = self.db[result]
            self.logger.debug("Computing TF: Working on \"%s\"" % doc["title"])
            tokens = Text.tokenize(doc['articleText'])
            numTokens = len(tokens)
            doc['numTokens'] = numTokens
            doc['tf'] = Text.get_term_freq(tokens)
            self.addDocument(doc)


    def computeTFIDF(self):
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
            self.logger.debug("Computing TF-IDF: Working on \"%s\"" % doc["title"])
            tf = doc['tf']
            tf_idf = {}
            for k, v in tf.items(): # By construction, there should never be KeyError's here
                tf_idf[k] = v * df[k]
            doc['tf_idf'] = tf_idf
            self.addDocument(doc)
