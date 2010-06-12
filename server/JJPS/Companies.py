#!/usr/bin/env python
import csv
import time
import urllib

import feedparser
import memcache

import Log

class Companies(object):
    # TODO
    # Better way of storing this information, a la, in a configuration file somewhere?
    companyDict = {
        "John Wiley and Sons": ["JW-A"],
        "Brill Academic Publishers": ["BRILL.AS"],
        "Elsevier": ["RUK", "ENL"]
    }
    
    companyNews = {}

    def __init__(self, config = None):
        #RDF.Uri("file:///home/nknouf/Documents/Personal/Projects/FirefoxExtensions/JJPS/trunk/info/JJPS.owl")
        self.config = config

        # Setup logging
        self.logger = Log.getLogger(config = self.config)

        # Setup memcache
        self.mc = memcache.Client([self.config.get("memcache", "server")], debug = int(self.config.get("memcache", "debug")))

    def getCompanyInfo(self, companyName, numEntries = 10):
        try:
            symbols = self.companyDict[companyName]
        except KeyError:
            # Try just getting news information from Yahoo News
            return self.getCompanyNews(companyName)
       
        # Get the stock prices
        symbolString = ""
        for symbol in symbols:
            symbolString += symbol + "+"
        
        # Cut off ending "+"
        symbolString = symbolString[:-1]

        quotesURL = "http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=snl1d1t1c1ohgv&e=.csv" % symbolString

        quotesCSV = urllib.urlopen(quotesURL)
        
        reader = csv.reader(quotesCSV)
        
        currentTime = time.strftime("%A, %d %B, %Y")
        
        stocksData = []
        for row in reader:
            code = row[0]
            name = row[1]
            price = row[2]
            date = row[3]
            timeTraded = row[4]
            change = row[5]
            volume = row[9]
            stockData = [name, code, price, change, date, timeTraded, volume]
            stocksData.append(stockData)
        
        # Get the 5 latest financial news headlines
        # Take first symbol
        url = "http://finance.yahoo.com/rss/headline?s=" + symbols[0]
        response = urllib.urlopen(url)
        data = response.read()
        response.close()

        feed = feedparser.parse(data)
        headlines = []
        headlines = [entry["title"] for entry in feed.entries[0:numEntries]]
        summaries = [entry["summary"] for entry in feed.entries[0:numEntries]]

        return {"stocks": stocksData, "headlines": headlines, "summaries": summaries}

    def getCompanyNews(self, companyName, numEntries = 10):
        """Search for company information at yahoo news; the data here is easier to parse than google's rss (at least if I remember correctly...)"""
        
        companyNameKey = companyName.replace(" ", "_").replace("&", "_").replace(".", "_")

        dataDict = self.mc.get(companyNameKey.encode("ascii"))
        if dataDict:
            return dataDict
        else:
            url = "http://news.search.yahoo.com/rss?ei=UTF-8&p=%22" + urllib.quote(companyName) + "%22&fr=news-us-ss"
            response = urllib.urlopen(url)
            data = response.read()
            response.close()
    
            feed = feedparser.parse(data)
            headlines = []
            headlines = [entry["title"] for entry in feed.entries[0:numEntries]]
            summaries = [entry["summary"] for entry in feed.entries[0:numEntries]]
            
            dataDict = {"headlines": headlines, "summaries": summaries}
            self.companyNews[companyName] = dataDict

            self.mc.set(companyNameKey.encode("ascii"), dataDict, time = int(self.config.get("memcache", "time")))

            return dataDict
