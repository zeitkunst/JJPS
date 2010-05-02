import csv
import urllib

from BeautifulSoup import BeautifulSoup
import feedparser

# The mapping from program IDs to processing code
# TODO
# make processing code inherit from some sort of base
soundMapping = {"NewsProgram": NewsProgram}

def Default():
    return None

def NewsProgram():
    quotesURL = "http://download.finance.yahoo.com/d/quotes.csv?s=ENL+RUK&f=snl1d1t1c1ohgv&e=.csv"
    quotesCSV = urllib.urlopen(quotesURL)
    
    reader = csv.reader(quotesCSV)
    
    newsString = "And now, for the markets.\n\n"
    
    for row in reader:
        code = row[0]
        name = row[1]
        price = row[2]
        date = row[3]
        time = row[4]
        change = row[5]
        volume = row[9]
        newsString += "%s, with stock code %s, had a price of %s at %s on a change of %s and volume of %s" % (name, code, str(price), time, str(change), str(volume))
        newsString += "\n\n"
    
    newsString += "And now, for the news.\n\n"
    
    #d = feedparser.parse("http://news.google.com/news?pz=1&cf=all&ned=us&hl=en&q=reed+elsevier&cf=all&output=rss") 
    d = feedparser.parse("http://finance.yahoo.com/rss/headline?s=ENL") 
    entries = d['entries'][0:9]
    
    for entry in d['entries']:
        title = entry['title']
        newsString += "%s\n\n" % title
        summary = entry['summary']
        #soup = BeautifulSoup(entry['summary'])
        #print soup.contents[0]
        #summary = soup.getText()
        newsString += "%s\n\n" % summary
   
    return newsString
