import csv
import urllib

from BeautifulSoup import BeautifulSoup
import feedparser

quotesURL = "http://download.finance.yahoo.com/d/quotes.csv?s=ENL+RUK&f=snl1d1t1c1ohgv&e=.csv"
quotesCSV = urllib.urlopen(quotesURL)

reader = csv.reader(quotesCSV)

stockString = "And now, for the markets.\n\n"

for row in reader:
    code = row[0]
    name = row[1]
    price = row[2]
    date = row[3]
    time = row[4]
    change = row[5]
    volume = row[9]
    stockString += "%s, with stock code %s, had a price of %s at %s on a change of %s and volume of %s" % (name, code, str(price), time, str(change), str(volume))
    stockString += "\n\n"

stockString += "And now, for the news.\n\n"

#d = feedparser.parse("http://news.google.com/news?pz=1&cf=all&ned=us&hl=en&q=reed+elsevier&cf=all&output=rss") 
d = feedparser.parse("http://finance.yahoo.com/rss/headline?s=ENL") 
entries = d['entries'][0:9]

for entry in d['entries']:
    title = entry['title']
    stockString += "%s\n\n" % title
    soup = BeautifulSoup(entry['summary'])
    summary = soup.getText()
    stockString += "%s\n\n" % summary

stockString = stockString.encode("utf-8")
fp = open("output.txt", 'w')
fp.write(stockString)
fp.close()
