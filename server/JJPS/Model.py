#!/usr/bin/env python
import cPickle
import csv
import glob
import os

from lxml import etree
import RDF
import simplejson as json
import networkx as nx
import matplotlib.pyplot as plt
from BeautifulSoup import BeautifulSoup

# Local imports
import Companies
import Documents
import Log

jjpsURI = u"http://journalofjournalperformancestudies.org/NS/JJPS.owl#"
jjpsNS = RDF.NS("http://journalofjournalperformancestudies.org/NS/JJPS.owl#")
rdfNS = RDF.NS("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
rdfsNS = RDF.NS("http://www.w3.org/2000/01/rdf-schema#") 

class Model(object):
    basicColorList = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']

    def __init__(self, config = None, ontologyPath= None):
        #RDF.Uri("file:///home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/info/JJPS.owl")
        self.config = config

        # Setup logging
        self.logger = Log.getLogger(config = self.config)

        if (ontologyPath is not None):
            self.ontologyPath = RDF.Uri(ontologyPath)
        else:
            self.ontologyPath = RDF.Uri(self.config.get("Model", "owlPath"))
        self.storagePath = self.config.get("Model", "storagePath")
        #self.storage = RDF.Storage(storage_name = "sqlite", name=self.storagePath, options_string="synchronous='normal'")
        self.storage = RDF.HashStorage(self.storagePath, options="hash-type='bdb'") 
        #self.storage = RDF.Storage(storage_name = "mysql", name = "JJPS", options_string = "host='localhost', database='JJPS', user='JJPS', password='jjps314'")
        self.model = RDF.Model(self.storage)
        self.parser = RDF.Parser()

        # setup link to PPC database
        # TODO
        # Make this configurable?
        self.d = Documents.PPCDocuments(config = self.config, dbName="jjps_ppc")
        
        # Setup link to company info
        self.companies = Companies.Companies(config = config)

    def getSubscriptionPrices(self):
        # TODO
        # More to get and process...
        prices = {}
        data = csv.reader(open("data/journalPrices/ElsevierPricelist2010USD.csv"))
        for item in data:
                prices[item[2]] = (item[8], item[9])
        
        data = csv.reader(open("data/journalPrices/TaylorAndFrancisPricelist2010.csv"))
        for item in data:
            if (item[7] == "USD"):
                prices[item[2]] = (item[8], '')
        data = csv.reader(open("data/journalPrices/SpringerJournals.csv"))
        for item in data:
            if (item[6] == ""):
                issn = item[7]
            else:
                issn = item[6]
            if (item[16] == ""):
                price = item[14]
            else:
                price = item[16]
            prices[issn] = (price, '')

        self.prices = prices

    def getFrobInfo(self, frobHTMLPath = "data/frob/"):
        """Read in all of our frob* info."""

        parsedData = []
        for file in glob.glob(frobHTMLPath + "*.html"):
            self.logger.debug("On file "+ file )
            fp = open(file)
            data = fp.read()
            fp.close()
            soup = BeautifulSoup(data)
            tables = soup.findAll("table")
            len(tables)
            frobTable = tables[8]
            trs = frobTable.findAll("tr")
            dataTrs = trs[2:]
            
            for dataTr in dataTrs:
                dataTds = dataTr.findAll("td")[2:]
                parsedData.append([dataTd.getText() for dataTd in dataTds])

        return parsedData
   
    def getSJRData(self):
        """Read the SJR data from our file."""
        lines = csv.reader(open("data/sjr.csv"))
        
        dataDict = {}
        for line in lines:
            issn = line[2]
            if (len(issn) != 8):
                continue
            issn = issn[0:4] + "-" + issn[4:]
            dataDict[issn] = {"sjr": line[3], "hIndex": line[4]}
        
        return dataDict

    def getISSNJournalMapping(self):
        """Return a mapping from ISSN to journalURI."""

        self.logger.debug("Getting ISSN/Journal mapping")
        # Get the URIs and associated ISSNs so that we can make a dictionary
        issnQuery = """PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?issn, ?journalURI
            WHERE {
            ?journalURI jjps:hasISSN ?issn .
            } """ % (jjpsURI)
        issn = RDF.Query(issnQuery.encode("ascii"), query_language="sparql")

        results = issn.execute(self.model)

        issnDict = {}

        for result in results:
            issnValue = result["issn"].literal_value["string"]
            journalURI = str(result["journalURI"].uri)
            issnDict[issnValue] = journalURI
        
        return issnDict

    def addSJRInfoToModel(self, sjrInfo):
        """Add the SJR info to the model indexed on ISSN."""

        issnDict = self.getISSNJournalMapping()
        
        sjrISSNs = sjrInfo.keys()

        for issn in sjrISSNs:
            try:
                journalURI = issnDict[issn]
                self.logger.debug("Working on " + journalURI)
            except KeyError:
                self.logger.debug("Problem with ISSN " + issn)
                continue
            
            sjr = sjrInfo[issn]["sjr"]
            hIndex = sjrInfo[issn]["hIndex"]

            # Add statements to model
            sjrStatement = RDF.Statement(RDF.Uri(journalURI), jjpsNS["hasSJR"], str(sjr))
            self.model.append(sjrStatement)

            hIndexStatement = RDF.Statement(RDF.Uri(journalURI), jjpsNS["hasHIndex"], str(hIndex))
            self.model.append(hIndexStatement)

    def addFrobInfoToModel(self, frobInfo):
        """Frobinate the info and add it to the model."""
        
        self.logger.debug("Getting ISSN/Journal mapping")
        # Get the URIs and associated ISSNs so that we can make a dictionary
        issnQuery = """PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?issn, ?journalURI
            WHERE {
            ?journalURI jjps:hasISSN ?issn .
            } """ % (jjpsURI)
        issn = RDF.Query(issnQuery.encode("ascii"), query_language="sparql")

        results = issn.execute(self.model)

        issnDict = {}

        for result in results:
            issnValue = result["issn"].literal_value["string"]
            journalURI = str(result["journalURI"].uri)
            issnDict[issnValue] = journalURI
        
        # Adding frobinated values to the model
        for frob in frobInfo:
            issn = frob[1]

            # Get URI for this issn
            try:
                journalURI = issnDict[issn]
                self.logger.debug("Working on " + journalURI)
            except KeyError:
                self.logger.debug("Problem with ISSN " + issn)
                continue

            if ((frob[3] != '') and (frob[3] != "&nbsp;")):
                frobpactFactor = int(float(frob[3]) * 1000) ^ 42
            else:
                frobpactFactor = ''

            if ((frob[8] != '') and (frob[8] != "&nbsp;")):
                eigenfrobFactor = int(float(frob[8]) * 100000) ^ 42
            else:
                eigenfrobFactor = ''

            if ((frob[9] != '') and (frob[9] != "&nbsp;")):
                frobfluenceFactor = int(float(frob[9]) * 1000) ^ 42
            else:
                frobfluenceFactor = ''
            

            # Add frobinated statements to model
            frobStatement = RDF.Statement(RDF.Uri(journalURI), jjpsNS["hasFrobpactFactor"], str(frobpactFactor))
            self.model.append(frobStatement)

            frobStatement = RDF.Statement(RDF.Uri(journalURI), jjpsNS["hasEigenfrobFactor"], str(eigenfrobFactor))
            self.model.append(frobStatement)

            frobStatement = RDF.Statement(RDF.Uri(journalURI), jjpsNS["hasFrobfluence"], str(frobfluenceFactor))
            self.model.append(frobStatement)

    def getOwnerNames(self):
        """Return all of the owners in the database."""
        ownerQuery = """PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?ownerName
            WHERE {
            ?ownerURI jjps:hasOrganizationName ?ownerName .
            } """ % (jjpsURI)
        owner = RDF.Query(ownerQuery.encode("ascii"), query_language="sparql")

        results = owner.execute(self.model)

        ownerList = []
        for result in results:
            ownerList.append(result["ownerName"].literal_value["string"])

        return ownerList

    def getJournalInfo(self, journalName, returnFormat = "xml"):
        """Return the information about a particular journal."""

        # Format the journal name so that we can find it in our model
        journalNameFormatted = journalName.lower().replace("&amp;", "and").replace(" ", "_")

        if (returnFormat == "xml"):
            # First, get the owner and, potentially, the price of the journal
            queryString = """
            PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?price, ?ownerURI, ?ownerName, ?frobpactFactor, ?eigenfrobFactor, ?frobfluence, ?sjr, ?hIndex
            WHERE {
                jjps:%s jjps:isOwnedBy ?ownerURI .
                ?ownerURI jjps:hasOrganizationName ?ownerName .
                OPTIONAL {
                    jjps:%s jjps:hasSubscriptionPrice ?price .
                } .
                OPTIONAL {
                    jjps:%s jjps:hasFrobpactFactor ?frobpactFactor .
                } .
                OPTIONAL {
                    jjps:%s jjps:hasEigenfrobFactor ?eigenfrobFactor .
                } .
                OPTIONAL {
                    jjps:%s jjps:hasFrobfluence ?frobfluence .
                } .
                OPTIONAL {
                    jjps:%s jjps:hasSJR ?sjr .
                } .
                OPTIONAL {
                    jjps:%s jjps:hasHIndex ?hIndex .
                } .

            } 
            """ % (jjpsURI, journalNameFormatted, journalNameFormatted, journalNameFormatted, journalNameFormatted, journalNameFormatted, journalNameFormatted, journalNameFormatted)

            """                """


            self.logger.debug("Looking up %s" % journalName)
            queryString = unicode(queryString)
            ownerQuery = RDF.Query(queryString.encode("ascii"), query_language="sparql")
            results = ownerQuery.execute(self.model)

            resultsXML = etree.Element("results")
            resultsXML.set("type", "journalInfo")
            resultsXML.set("journalName", journalName)
            for result in results:
                resultXML = etree.Element("result")
                if (result["price"] is not None):
                    price = result["price"].literal_value["string"]
                else:
                    price = ""

                if (result["frobpactFactor"] is not None):
                    frobpactFactor = result["frobpactFactor"].literal_value["string"]
                else:
                    frobpactFactor = ""

                if (result["eigenfrobFactor"] is not None):
                    eigenfrobFactor = result["eigenfrobFactor"].literal_value["string"]
                else:
                    eigenfrobFactor = ""

                if (result["frobfluence"] is not None):
                    frobfluence = result["frobfluence"].literal_value["string"]
                else:
                    frobfluence = ""

                if (result["sjr"] is not None):
                    sjr = result["sjr"].literal_value["string"]
                else:
                    sjr = ""

                if (result["hIndex"] is not None):
                    hIndex = result["hIndex"].literal_value["string"]
                else:
                    hIndex = ""


                ownerURI = str(result["ownerURI"].uri)
                ownerName = result["ownerName"].literal_value["string"]
                resultXML.set("ownerURI", ownerURI)
                resultXML.set("ownerName", ownerName)
                resultXML.set("price", price)
                resultXML.set("frobpactFactor", frobpactFactor)
                resultXML.set("frobfluence", frobfluence)
                resultXML.set("eigenfrobFactor", eigenfrobFactor)
                resultXML.set("sjr", sjr)
                resultXML.set("hIndex", hIndex)
                resultsXML.append(resultXML)

            # Next, try and get its parent owner
            queryString = """
            PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?parentURI, ?parentName 
            WHERE {
                <%s> rdfs:subClassOf ?parentURI .
                ?parentURI jjps:hasOrganizationName ?parentName .
            } 
            """ % (jjpsURI, ownerURI)
            parentQuery = RDF.Query(queryString.encode("ascii"), query_language="sparql")
            results = parentQuery.execute(self.model)

            for result in results:
                parentURI = str(result["parentURI"].uri)
                parentName = result["parentName"].literal_value["string"]
                resultXML.set("parentURI", parentURI)
                resultXML.set("parentName", parentName)
            
            # Figure out what to add wrt the stock quotes and headlines
            # Try and use the parent name
            companyName = resultXML.get("parentName")
            if (companyName is None):
                # If it doesn't exist, use the owner name
                companyName = resultXML.get("ownerName")

            results = self.companies.getCompanyInfo(companyName)
            headlines = etree.Element("headlines")
            for headline in results["headlines"]:
                headlineE = etree.Element("headline")
                headlineE.set("value", headline)
                headlines.append(headlineE)
            resultsXML.append(headlines)

            # Add stock quotes if they exist
            try:
                stocks = results["stocks"]
                stocksE = etree.Element("stocks")

                for stock in stocks:
                    stockE = etree.Element("stock")
                    stockE.set("name", stock[0])
                    stockE.set("symbol", stock[1])
                    stockE.set("price", stock[2])
                    stockE.set("change", stock[3])
                    stockE.set("date", stock[4])
                    stockE.set("time", stock[5])
                    stockE.set("volume", stock[6])
                    stocksE.append(stockE)

                resultsXML.append(stocksE)
            except KeyError:
                pass

            # Get click value
            clickValue = self.d.getClickValue(journalName)
            resultXML.set("clickValue", unicode(round(clickValue)))

            return etree.tostring(resultsXML)
        elif (returnFormat == "json"):
            pass
        elif (returnFormat == "rdf"):
            pass

    def getJournalsOwnedBy(self, owner, returnFormat = "xml"):
        """Return the list of journals owned by a top-level owner, such as Elsevier.  `returnFormat` can be any of xml, rdf, or json."""
        # TODO
        # OPTIMIZE!!!  It's way too slow right now, at least for XML on the big publishers

        if (returnFormat == "xml"):
            queryString = """
            PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?parent, ?journal
            WHERE {
                ?parentURI rdfs:subClassOf jjps:%s ;
                            jjps:hasOrganizationName ?parent .
                ?journalURI jjps:isOwnedBy ?parentURI ;
                            jjps:hasJournalName ?journal .
            } 
            ORDER BY ?parent""" % (jjpsURI, owner)
            queryString = unicode(queryString)
            parentQuery = RDF.Query(queryString.encode("ascii"), query_language="sparql")
            results = parentQuery.execute(self.model)

            resultsXML = etree.Element("results")
            resultsXML.set("type", "journalOwners")
            for result in results:
                resultXML = etree.Element("result")
                parent = result["parent"].literal_value["string"]
                journal = result["journal"].literal_value["string"]
                resultXML.set("parent", parent)
                resultXML.set("journal", journal)
                resultsXML.append(resultXML)
            return etree.tostring(resultsXML)
        elif (returnFormat == "json"):
            dataDict = {}
            for result in results:
                parent = result["parent"].literal_value["string"]
                journal = result["journal"].literal_value["string"]
                if (dataDict.has_key(parent)):
                    dataDict[parent].append(journal)
                else:
                    dataDict[parent] = []
                    dataDict[parent].append(journal)
            return json.dumps(dataDict)
        elif (returnFormat == "rdf"):
            queryString = """
            PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            CONSTRUCT { 
                ?parent rdfs:subClassOf jjps:%s . 
                ?journal jjps:isOwnedBy ?parent .
            } 
            WHERE {
                ?parent rdfs:subClassOf jjps:%s .
                ?journal jjps:isOwnedBy ?parent .
            }""" % (jjpsURI, owner, owner)
            parentQuery = RDF.Query(queryString.encode('ascii'), query_language="sparql")
            results = parentQuery.execute(self.model)
            return results.to_string()

    def getJournalNames(self):
        """Get a list of names from the query."""
        getNamesQuery = """PREFIX jjps: <%s>
SELECT ?journalName, ?ownerName
WHERE {
    ?journal jjps:hasJournalName ?journalName .
    ?journal jjps:isOwnedBy ?ownerURI .
    ?ownerURI jjps:hasOrganizationName ?ownerName .
}""" % (jjpsURI)
        getNames = RDF.Query(getNamesQuery.encode("ascii"), query_language = "sparql")
        getNamesResults = getNames.execute(self.model)
        
        journalNames = []
        for result in getNamesResults:
            journalNames.append((result["ownerName"].literal_value["string"], result["journalName"].literal_value["string"]))
        return journalNames

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

    def getOwnerCounts(self):
        """Go through each owner (as object of "isOwnedBy"), and count up how many journals they have."""
        getOwnersQuery =  """PREFIX jjps: <%s> 
SELECT DISTINCT ?ownerURI 
WHERE {
    ?x jjps:isOwnedBy ?ownerURI . 
}""" % (jjpsURI)
        print getOwnersQuery
        print "Model: Getting all owners"
        getOwners = RDF.Query(getOwnersQuery.encode("ascii"), query_language="sparql")
        ownerURIs = []
        results = getOwners.execute(self.model)
        for result in results:
            ownerURI = str(result["ownerURI"])
            ownerURI = ownerURI[1:len(ownerURI) - 1]

            # Now, get all the journals owned by this owner
            # We can't use ARQ extensions like COUNT, unfortunately
            getOwnedQuery = """PREFIX jjps: <%s>
SELECT ?journal
WHERE {
    ?journal jjps:isOwnedBy <%s> .
}""" % (jjpsURI, ownerURI)
            getOwned = RDF.Query(getOwnedQuery.encode("ascii"), query_language = "sparql")
            getOwnedResults = getOwned.execute(self.model)
            
            count = 0
            for getOwnedResult in getOwnedResults:
                count += 1
            ownerURIs.append((ownerURI, count))

        return ownerURIs

    def addJournalOwnershipToModel(self, companyName, journalName, frequency, ISSN):
        """Add the journal ownership information (at the moment: journal name, owner, frequency, and ISSN) to the local triple store.

        TODO: add in citation index info from Thompson/Reuters."""

        companyNameLower = companyName.lower()
        
        journalNameUnderscores = journalName.lower().replace("&amp;", "and").replace(" ", "_")
        companyNameUnderscores = companyName.lower().replace("&amp;", "and").replace(" ", "_")

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
        # . journal price (if we have it...)
        try:
            price = self.prices[str(ISSN)]
            journalStatement = RDF.Statement(jjpsNS[str(journalNameUnderscores)], jjpsNS["hasSubscriptionPrice"], str(price[0]))
            self.model.append(journalStatement)
        except KeyError:
            pass

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
        elif (companyNameLower.find("taylor") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["TaylorAndFrancis"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("routledge") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["TaylorAndFrancis"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("cambridge univ") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["CambridgeUniversityPress"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("oxford univ") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["OxfordUniversityPress"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("ieee") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["IEEE"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("biomed central") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["Springer"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("karger") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["Karger"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("nature publishing") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["NaturePublishingGroup"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("world scientific") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["WorldScientificPublishing"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("bentham science") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["BenthamSciencePublishers"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("mary ann liebert") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["MaryAnnLiebert"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("univ chicago") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["UniversityOfChicagoPress"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("emerald group") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["EmeraldGroupPublishing"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("iop publishing") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["IOPPublishing"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("informa healthcare") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["Informa"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("science china") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["ScienceChinaPress"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("johns hopkins") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["JohnsHopkinsUniversityPress"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("amer chemical") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["AmericanChemicalSociety"])
            self.model.append(ownedStatement)
        elif (companyNameLower.find("maney publishing") != -1):
            ownedStatement = RDF.Statement(jjpsNS[str(companyNameUnderscores)], rdfsNS["subClassOf"], jjpsNS["ManeyPublishing"])
            self.model.append(ownedStatement)
        else:
            pass

    def rebuildModel(self):
        """Rebuild the model.  Best to delete the original bdb files beforehand.  Run this from top-level directory of server (otherwise you have to change the path below to the master journal list pickled file)."""
        self.createBaseModel()
    
        # Read in pickle file with journal information
        print "Reading in journalList pickle file"
        fp = open("data/journalList/masterJournalList.pickle", "r")
        masterJournalList = cPickle.load(fp)
        fp.close()
    
        self.getSubscriptionPrices()
        self.addJournalsToModel(masterJournalList)
    
        self.writeModel()

    def createGraphForTopLevelOwner(self, topLevelOwner):
        """Create a dot format network file for the given owner.  At the moment this only works for top-level owners already instantiated in our ontology file."""

        graph = nx.DiGraph()
        #dotNetwork = "digraph {\n"
        subClassQuery = """PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?subsidiary, ?subsidiaryName, ?ownerName
            WHERE {
            ?subsidiary rdfs:subClassOf jjps:%s .
                ?subsidiary jjps:hasOrganizationName ?subsidiaryName .
                jjps:%s jjps:hasOrganizationName ?ownerName .
            } """ % (jjpsURI, topLevelOwner, topLevelOwner)
        subClass = RDF.Query(subClassQuery.encode("ascii"), query_language="sparql")

        results = subClass.execute(self.model)
        subsidiaries = []

        # Generate color lists
        colorMapping = {}

        count = 0
        for result in results:
            topLevelOwnerName = result["ownerName"].literal_value["string"]
            subsidiaryURI = str(result["subsidiary"])
            subsidiaryName = result["subsidiaryName"].literal_value["string"]
            subsidiaries.append((subsidiaryURI[1:len(subsidiaryURI) - 1], subsidiaryName))

            # TODO
            # Fix for when we have too many colors
            try:
                colorMapping[subsidiaryName] = self.basicColorList[count]
            except IndexError:
                count = 0
                colorMapping[subsidiaryName] = self.basicColorList[count]

            graph.add_edge(subsidiaryName, topLevelOwnerName, color=colorMapping[subsidiaryName])

            #dotNetwork += "\"%s\" -> \"%s\";\n" % (subsidiaryName, topLevelOwnerName)
            count += 1

        # Now, go through each subsidiary URI and pull out each of the journals attached to it
        for subsidiary in subsidiaries:
            subsidiaryQuery = """PREFIX jjps: <%s> 
            SELECT ?journalURI, ?journalName
            WHERE {
                ?journalURI jjps:isOwnedBy <%s> .
                ?journalURI jjps:hasJournalName ?journalName .
            } """ % (jjpsURI, subsidiary[0])

            subsidiaryInfo = RDF.Query(subsidiaryQuery.encode("ascii"), query_language="sparql")

            results = subsidiaryInfo.execute(self.model)

            for result in results:
                journalName = result["journalName"].literal_value["string"]
                graph.add_edge(journalName, subsidiary[1], color = colorMapping[subsidiary[1]])
                #dotNetwork += "\"%s\" -> \"%s\";\n" % (journalName, subsidiary[1])

        #dotNetwork += "}"

        return graph

    def createGraphForOwner(self, ownerName):
        """Create a dot format network file for the given owner.  At the moment this only works for top-level owners already instantiated in our ontology file."""

        graph = nx.DiGraph()
        #dotNetwork = "digraph {\n"
        ownerQuery = """PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?journalName 
            WHERE {
            ?ownerURI jjps:hasOrganizationName "%s" .
                ?journalURI jjps:isOwnedBy ?ownerURI .
                ?journalURI jjps:hasJournalName ?journalName .
            } """ % (jjpsURI, ownerName)
        owner = RDF.Query(ownerQuery.encode("ascii"), query_language="sparql")

        results = owner.execute(self.model)
        journals = []

        # Generate color lists
        colorMapping = {}

        count = 0
        for result in results:
            journalName = result["journalName"].literal_value["string"]

            graph.add_edge(journalName, ownerName)

            count += 1

        return graph

    def createImageOfGraph(self, g, iterations = 5, filename = None, figsize = (7, 3), graphParams = {"node_size": 0, "alpha": 0.4, "edge_color": 'r', "font_size": 10}):
        """Create an image of the graph g with the given parameters.  Save it in the designated directory."""
        try:
            pos = nx.spring_layout(g, iterations = iterations)
        except ZeroDivisionError:
            # nothing is in the graph, so return
            return False

        plt.figure(figsize = figsize)
        try:
            nx.draw(g, pos, node_size = graphParams["node_size"], alpha = graphParams["alpha"], edge_color = graphParams["edge_color"], font_size = graphParams["font_size"])
        except ValueError:
            # Strangely, some graphs aren't able to be drawn as they give a "zero-size array to ufunc.reduce without identity" error
            return False

        if (filename is None):
            filename = "foo.png"

        plt.savefig(filename)
        plt.close()

        return True

    def createAllOwnerImages(self, redo = False):
        stem = "static/images/graphs/"

        ownerList = self.getOwnerNames()

        for owner in ownerList:
            ownerUnderscores = owner.replace(" ", "_").replace("&amp;", "_").replace("&Amp;", "_").replace(".", "_").replace("/", "_") + ".png"

            filename = os.path.join(stem, ownerUnderscores)
            
            # TODO
            # There's got to be a better way of doing this...
            if (redo == False):
                # Check to see if we already have an image created
                try:
                    # If the stat call retuns properly, the file "exists"
                    os.stat(filename)
                    continue
                except OSError:
                    pass
            

            g = self.createGraphForOwner(owner)

            self.logger.debug("Creating graph for %s" % owner)
            

            self.createImageOfGraph(g, filename = os.path.join(stem, ownerUnderscores))

"""Getting price information
prices = {}
data = csv.reader(open("ElsevierPricelist2010USD.csv"))
for item in data:
        prices[item[2]] = (item[8], item[9])

data = csv.reader(open("TaylorAndFrancisPricelist2010.csv"))
for item in data:
    if (item[7] == "USD"):
        prices[item[2]] = (item[8], '')
data = csv.reader(open("SpringerJournals.csv"))
for item in data:
    if (item[6] == ""):
        issn = item[7]
    else:
        issn = item[6]
    if (item[16] == ""):
        price = item[14]
    else:
        price = item[16]
    prices[issn] = (price, '')
# Total price
jjpsNS = "http://journalofjournalperformancestudies.org/NS/JJPS.owl#"
query = "PREFIX jjps: <%s> SELECT ?price WHERE { ?x jjps:hasSubscriptionPrice ?price } ORDER BY ?x" % jjpsNS
priceQuery = RDF.Query(query, query_language="sparql")
results = priceQuery.execute(model)
total = 0
for result in results:
    price = result["price"].literal_value["string"]
    price = price.replace(",", "")
    if (price != ""):
        total += float(price)
# Making images of ownership graphs, basic version
from networkx import *
import matplotlib.pyplot as plt
G = m.createGraphForOwner("JohnWileyAndSons")
pos = nx.spring_layout(G, iterations = 10)
plt.figure(figsize = (50, 50))
edgeColors = [edgeInfo[2]["color"] for edgeInfo in G.edges(data = True)]
nx.draw(G, pos, node_size = 0, alpha = 0.4, edge_color = edgeColors, font_size = 10)
plt.savefig("foo.png")
"""
if __name__ == "__main__":
    journalModel = Model()
    journalModel.createBaseModel()

    # Read in pickle file with journal information
    print "Reading in journalList pickle file"
    fp = open("journalList/masterJournalList.pickle", "r")
    masterJournalList = cPickle.load(fp)
    fp.close()

    journalModel.getSubscriptionPrices()
    journalModel.addJournalsToModel(masterJournalList)

    journalModel.writeModel()
