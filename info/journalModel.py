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
        self.hashStorage = RDF.HashStorage("JournalStorage.bdb", options="hash-type='bdb'") 
        self.model = RDF.Model(self.hashStorage)
        self.parser = RDF.Parser()

    def createBaseModel(self):
        self.parser.parse_into_model(self.model, self.ontologyPath, base_uri="http://journalofjournalperformancestudies.org/NS/JJPS.owl")

    def writeModel(self):
        fp = open("output.rdf", "w")
        fp.write(self.model.to_string())
        fp.close()

    def addJournalsToModel(self, journalList):
        counter = 0
        keys = journalList.keys()
        #keys = keys[0:5000]
        for key in keys:
            # Get the first big before the comma
            journalAddress = journalList[key]["address"].split(",")[0]
            journalISSN = journalList[key]["ISSN"]
            journalFrequency = journalList[key]["frequency"]
            
            self.addJournalOwnershipToModel(journalAddress, key, journalFrequency, journalISSN)

            counter +=1

            if ((counter % 100) == 0):
                print "On journal %d" % counter

    def addJournalOwnershipToModel(self, companyName, journalName, frequency, ISSN):
        companyNameLower = companyName.lower()
        
        journalNameUnderscores = journalName.lower().replace(" ", "_")
        companyNameUnderscores = companyName.lower().replace(" ", "_")

        # . Name of Journal
        journalStatement = RDF.Statement(jjpsNS[str(journalNameUnderscores)], jjpsNS["hasJournalName"], str(journalName))
        self.model.append(journalStatement)
        # . ISSN
        journalStatement = RDF.Statement(jjpsNS[str(journalNameUnderscores)], jjpsNS["hasISSN"], str(ISSN))
        self.model.append(journalStatement)
        # . frequency
        journalStatement = RDF.Statement(jjpsNS[str(journalNameUnderscores)], jjpsNS["hasIssueFrequency"], str(frequency))
        self.model.append(journalStatement)

        # . isa journal
        journalStatement = RDF.Statement(jjpsNS[str(journalNameUnderscores)], rdfNS["type"], jjpsNS["Journal"])
        self.model.append(journalStatement)
        # . isOwnedBy
        journalStatement = RDF.Statement(jjpsNS[str(journalNameUnderscores)], jjpsNS["isOwnedBy"], jjpsNS[str(companyNameUnderscores)])
        self.model.append(journalStatement)
         # . company name
        journalStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], jjpsNS["hasOrganizationName"], str(companyName))
        self.model.append(journalStatement)
   

        if (companyNameLower.find("wiley") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["JohnWileyAndSons"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("elsevier") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["Elsevier"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("sage") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["SagePublications"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("springer") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["Springer"])
            self.model.append(ownedStatement)
        else:
            pass

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
