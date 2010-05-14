#!/usr/bin/env python
import cPickle
import csv

from lxml import etree
import RDF
import simplejson as json

jjpsURI = u"http://journalofjournalperformancestudies.org/NS/JJPS.owl#"
jjpsNS = RDF.NS("http://journalofjournalperformancestudies.org/NS/JJPS.owl#")
rdfNS = RDF.NS("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
rdfsNS = RDF.NS("http://www.w3.org/2000/01/rdf-schema#") 

class Model(object):

    def __init__(self, config = None, ontologyPath= None):
        #RDF.Uri("file:///home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/info/JJPS.owl")
        self.config = config
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

    def getJournalsOwnedBy(self, owner, returnFormat = "xml"):
        """Return the list of journals owned by a top-level owner, such as Elsevier.  `returnFormat` can be any of xml, rdf, or json."""
        # TODO
        # OPTIMIZE!!!  It's way too slow right now


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

    def addJournalOwnershipToModel(self, companyName, journalName, frequency, ISSN):
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
        else:
            pass

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
# Constructing graphs of ownership
queryString = 'PREFIX jjps: <http://journalofjournalperformancestudies.org/NS/JJPS.owl#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> CONSTRUCT{?parent rdfs:subClassOf jjps:Elsevier . ?journal jjps:isOwnedBy ?parent .} WHERE { ?parent rdfs:subClassOf jjps:Elsevier . ?journal jjps:isOwnedBy ?parent .} ORDER BY ?parent'
parentQuery = RDF.Query(queryString, query_language="sparql")
results = parentQuery.execute(model)
fp = open("elsevierModel.rdf", "w")
fp.write(results.to_string())
fp.close()
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