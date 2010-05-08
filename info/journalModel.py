#!/usr/bin/env python
import cPickle

import RDF

jjpsNS = RDF.NS("http://journalofjournalperformancestudies.org/NS/JJPS.owl#")
rdfNS = RDF.NS("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
rdfsNS = RDF.NS("http://www.w3.org/2000/01/rdf-schema#") 

class JournalModel(object):

    def __init__(self, pathToOntology = RDF.Uri("file:///home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/info/JJPS.owl")):
        self.ontologyPath = pathToOntology
        self.memoryStorage = RDF.MemoryStorage()
        self.model = RDF.Model(self.memoryStorage)
        self.parser = RDF.Parser()

    def createBaseModel(self):
        self.parser.parse_into_model(self.model, self.ontologyPath, base_uri="http://journalofjournalperformancestudies.org/NS/JJPS.owl")

    def writeModel(self):
        fp = open("output.rdf", "w")
        fp.write(self.model.to_string())
        fp.close()

    def addJournalsToModel(self, journalList):
        counter = 0
        for key in journalList.keys():
            address = journalList[key]["address"].lower()

            # Do wiley
            if (address.find("wiley") != -1):
                # Parse owner info
                addressSplit = journalList[key]["address"].split(",")
                addressSpaces = addressSplit[0]
                addressUnderscores = addressSpaces.replace(" ", "_")

                # Add in journal statements
                keyUnderscores = key.replace(" ", "_")
                keyUnderscores = keyUnderscores.decode("ascii", "ignore")

                # . Name of Journal
                journalStatement = RDF.Statement(jjpsNS[keyUnderscores], jjpsNS["hasJournalName"], key)
                self.model.append(journalStatement)
                # . isa journal
                journalStatement = RDF.Statement(jjpsNS[keyUnderscores], rdfNS["type"], jjpsNS["Journal"])
                self.model.append(journalStatement)
                # . isOwnedBy
                journalStatement = RDF.Statement(jjpsNS[keyUnderscores], jjpsNS["isOwnedBy"], jjpsNS[addressUnderscores])
                self.model.append(journalStatement)

                # . Who it is owned by
                ownedStatement = RDF.Statement(jjpsNS[addressUnderscores], rdfsNS["subClassOf"], jjpsNS["JohnWileyAndSons"])
                self.model.append(ownedStatement)
            counter +=1

            if ((counter % 100) == 0):
                print "On journal %d" % counter

if __name__ == "__main__":
    journalModel = JournalModel()
    journalModel.createBaseModel()

    # Read in pickle file with journal information
    print "Reading in journalList pickle file"
    fp = open("journalList/masterJournalList.pickle", "r")
    masterJournalList = cPickle.load(fp)
    fp.close()

    journalModel.addJournalsToModel(masterJournalList)

    journalModel.writeModel()
