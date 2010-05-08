#!/usr/bin/env python
import glob
import cPickle
import re

from BeautifulSoup import BeautifulSoup

from titlecase import titlecase

getName = re.compile("(\d+\.)(.*)")

def parseJournalListFile(filename):
    fp = open(filename, "r")
    doc = fp.read()
    fp.close()

    soup = BeautifulSoup(doc)
    dts = soup.findAll("dt")

    journalList = {}

    for dt in dts:
        # Get the name minus the number
        fullName = getName.match(dt.text).groups()[1].strip()
        fullName = fullName.lower()
        fullName = titlecase(fullName)

        journalList[fullName] = {}

        # Get the following definition data elements, which include:
        # . frequency of publication
        # . ISSN
        # . address + indicies
        dds = dt.fetchNextSiblings("dd", limit=3)

        # We need to check if the ISSN is in the second dd;
        # if not, then we assume that there was no frequency given,
        # and we need to take only two dds instead

        if (dds[1].text.find("ISSN") == -1):
            dds = dt.fetchNextSiblings("dd", limit=2)
            journalList[fullName]["frequency"] = "none"
            journalList[fullName]["ISSN"] = dds[0].text[6:]
            address = dds[1].contents[0].lower()
            journalList[fullName]["address"] = titlecase(address)
            citationIndicies = dds[1].contents[1]
            links = citationIndicies.findAll("a")
    
            linkList = []
    
            for link in links:
                linkList.append((link["href"], link.text))
    
            journalList[fullName]["citationIndicies"] = linkList

        else:
            journalList[fullName]["frequency"] = dds[0].text.strip()
            journalList[fullName]["ISSN"] = dds[1].text[6:]
            address = dds[2].contents[0].lower()
            journalList[fullName]["address"] = titlecase(address)
            citationIndicies = dds[2].contents[1]
            links = citationIndicies.findAll("a")
    
            linkList = []
    
            for link in links:
                linkList.append((link["href"], link.text))
    
            journalList[fullName]["citationIndicies"] = linkList
    return journalList

if __name__ == "__main__":
    masterJournalList = {}

    filenames = glob.glob("*.html")
    filenames.sort()
    for file in filenames:
        print "Working on", file
        journalList = parseJournalListFile(file)
        masterJournalList.update(journalList)

    fp = open("masterJournalList.pickle", "wb")
    cPickle.dump(masterJournalList, fp)
    fp.close()

