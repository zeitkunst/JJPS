# Dealing with documents in couchdb
import hashlib

import couchdb
import BeautifulSoup

class Documents(object):

    def __init__(self, config = None):
        self.config = config

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

        return newDataDict

    def addDocument(self, dataDict):
        """Add the document in dataDict to the database.  Create an ID based on the hash of the title and author values."""
        
        # Create an id based on the hash of the title and author

        id = hashlib.sha256(dataDict["title"].encode("ascii", "ignore") + dataDict["authors"].encode("ascii", "ignore")).hexdigest()
        print id
        dataDict["_id"] = id
        try:
            id, rev = self.db.save(dataDict)
        except couchdb.http.ResourceConflict:
            document = self.db[id]
            rev = document["_rev"]
            dataDict["_rev"] = rev
            self.db.save(dataDict)
