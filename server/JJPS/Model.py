#!/usr/bin/env python
import cPickle
import csv

from lxml import etree
import RDF
import simplejson as json
import networkx as nx

# Local imports
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

    def getJournalInfo(self, journalName, returnFormat = "xml"):
        """Return the information about a particular journal."""

        # Format the journal name so that we can find it in our model
        journalNameFormatted = journalName.lower().replace("&amp;", "and").replace(" ", "_")

        if (returnFormat == "xml"):
            # First, get the owner and, potentially, the price of the journal
            queryString = """
            PREFIX jjps: <%s> 
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT ?price, ?ownerURI, ?ownerName
            WHERE {
                jjps:%s jjps:isOwnedBy ?ownerURI .
                ?ownerURI jjps:hasOrganizationName ?ownerName .
                OPTIONAL {
                    jjps:%s jjps:hasSubscriptionPrice ?price .
                } .
            } 
            """ % (jjpsURI, journalNameFormatted, journalNameFormatted)

            """                """


            self.logger.debug("Looking up %s" % journalName)
            queryString = unicode(queryString)
            ownerQuery = RDF.Query(queryString.encode("ascii"), query_language="sparql")
            results = ownerQuery.execute(self.model)

            resultsXML = etree.Element("results")
            resultsXML.set("type", "journalInfo")
            for result in results:
                resultXML = etree.Element("result")
                if (result["price"] is not None):
                    price = result["price"].literal_value["string"]
                else:
                    price = ""
                ownerURI = str(result["ownerURI"].uri)
                ownerName = result["ownerName"].literal_value["string"]
                resultXML.set("price", price)
                resultXML.set("ownerURI", ownerURI)
                resultXML.set("ownerName", ownerName)
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

    def createGraphForOwner(self, topLevelOwner):
        """Create a dot format network file for the given owner.  At the moment this only works for top-level owners already instantiated in our ontology file.
        
        TODO: instead of writing out a dot file, make a graph using networkx."""

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
