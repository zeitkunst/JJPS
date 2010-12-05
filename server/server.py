#!/usr/bin/env python
# The code in JJPS is available under the GNU GPL V3 (http://www.gnu.org/copyleft/gpl.html) with the following modifications:

# The words "you", "licensee", and "recipient" are redefined to be as follows: "You", "licensee", and "recipient" is defined as anyone as long as s/he is not an EXCLUDED PERSON. An EXCLUDED PERSON is any individual, group, unit, component, synergistic amalgamation, cash-cow, chunk, CEO, CFO, worker, or organization of a corporation that is a member, as of the date of acquisition of this software, of the Fortune 1000 list of the world's largest businesses. (See http://money. cnn.com/magazines/fortune/global500/2008/full_list/ for an example of the top 500.) An EXCLUDED PERSON shall also include anyone working in a contractor, subcontractor, slave, or freelance capacity for any member of the Fortune 1000 list of the world's largest businesses.

# Please see http://.org/license.
# Just a test

import os
import random
from StringIO import StringIO
import sys
import urllib
import logging
import hashlib
import time


import simplejson as json
import web
from wsgilog import WsgiLog, LogIO
from webob.acceptparse import Accept
from lxml import etree
import textile
import PyRSS2Gen
import twitter

# My own library imports
from JJPS.Station import Station
from JJPS.Model import Model 
from JJPS.Documents import ArticleDocuments, VoteDocuments, PPCDocuments, AdsDocuments, JournalDocuments, UploadDocuments, PriceDocuments

import serverConfig

version = "0.01"

urls = (
    # Front-end URIs
    '/', 'index',
    '/license', 'license',
    '/license/', 'license',
    '/extension', 'extensionIndex',
    '/extension/', 'extensionIndex',
    '/extension/documentation', 'extensionDocumentation',
    '/extension/documentation/features', 'extensionFeatures',
    '/extension/documentation/factors', 'extensionFactors',
    '/extension/documentation/statement', 'extensionStatement',
    '/extension/documentation/screenshots', 'extensionScreenshots',
    '/extension/documentation/credits', 'extensionCredits',
    '/extension/download', 'extensionDownload',
    '/extension/FAQ', 'extensionFAQ',
    '/extension/developers', 'extensionDevelopers',
    '/radio', 'radioIndex',
    '/radio/', 'radioIndex',
    '/radio/schedule', 'schedule',
    '/radio/schedule/', 'schedule',
    '/radio/programs/(.*?)', 'ViewProgram',
    '/radio/programs', 'ViewProgramList',
    '/radio/technical', 'radioTechnical',
    '/radio/feed/podcast.xml', 'podcastFeed',
    # API URIs
    '/API', 'APIInfo',
    '/API/ownership/(.*?)', 'APIOwnership',
    '/API/journal/(.*?)', 'APIJournal',
    '/API/ads', 'APIAds',
    '/API/test/(.*?)', 'APITest',
    '/API/file/(.*?)', 'APIFile',
    '/API/vote', 'APIVote',
    '/API/price', 'APIPrice',
    '/API/programs', 'APIPrograms',
    # Feed URL
    '/feed/rss', 'PostsFeed', 
    '/feed/rss/', 'PostsFeed',
    # Admin URIs
    '/admin', 'adminIndex',
    '/admin/', 'adminIndex',
    '/admin/view', 'adminView',
    '/admin/viewComments', 'adminViewComments',
    '/post/(.*?)', 'viewPost',
    '/admin/edit/(.*?)', 'adminEdit',
    '/admin/editComment/(.*?)', 'adminEditComment',
    '/admin/index', 'adminIndex',
    '/admin/post', 'adminPost',
    '/admin/logout', 'adminLogout',
    '/admin/shows', 'adminShows'
)

app = web.application(urls, globals())
webDB = web.database(dbn='sqlite', db='data/JJPSSite.db')
if web.config.get('_session') is None:
    session = web.session.Session(app, web.session.DiskStore('sessions'),  initializer = {'loggedIn': False})
    web.config._session = session
else:
    session = web.config._session

render = web.template.render('templates/', base = 'layout', cache = serverConfig.cache)
renderAdmin = web.template.render('templates/', base = 'layoutAdmin', cache = serverConfig.cache)
renderExtension = web.template.render('templates/', base = 'layoutExtension', cache = serverConfig.cache)
renderRadio = web.template.render('templates/', base = 'layoutRadio', cache = serverConfig.cache)
#renderAdmin = web.template.render('templates/', base = 'layoutAdmin', cache = config.cache)

def notfound():
    return web.notfound(render.notfound())

app.notfound = notfound


class Log(WsgiLog):
    def __init__(self, application):
        WsgiLog.__init__(
            self,
            application,
            logformat = '%(message)s',
            tofile = True,
            file = serverConfig.log_file,
            interval = serverConfig.log_interval,
            backups = serverConfig.log_backups
        )
        sys.stdout = LogIO(self.logger, logging.INFO)
        sys.stderr = LogIO(self.logger, logging.ERROR)

class index:
    def GET(self):
        station = StationSingleton.getStation()

        # get identi.ca dents
        statusesString = station.mc.get("statuses")

        if statusesString:
            pass
        else:
            api = twitter.Api(base_url="http://identi.ca/api")
            statuses = api.GetUserTimeline("JJPS", count = 5)
            statusesE = etree.Element("div")
            statusesE.set("class", "span-6")
            headE = etree.Element("h2")
            headE.text = "JJPS Dents"
            statusesE.append(headE)
            for status in statuses:
                text = status.text
                created = status.created_at
                itemE = etree.Element("div")
                itemE.set("class", "status")
                itemSE = etree.Element("p")
                itemSE.text = text
                itemCE = etree.Element("p")
                itemCE.text = created
                itemE.append(itemSE)
                itemE.append(itemCE)
                statusesE.append(itemE)
            followE = etree.Element("h3")
            followAE = etree.Element("a")
            followAE.set("href", "http://identi.ca/JJPS")
            followAE.text = "Follow JJPS at identi.ca"
            followE.append(followAE)
            statusesE.append(followE)
            statusesString = etree.tostring(statusesE, pretty_print = True)
            station.mc.set("statuses", statusesString, time = 60)

        results = webDB.select("posts", limit=10, order="datetime DESC")
        posts = ""
        postsE = etree.Element("div")
        postsE.set("id", "posts")
        postsE.set("class", "span-18 last")
        h1E = etree.Element("h1")
        h1E.text = "Recent News"
        h1E.set("class", "span-18 last append-bottom")
        postsE.append(h1E)
        posts += "<div id='posts'>"
        for item in results:
            postID = item["pid"]
            datetime = item['datetime']
            timeTuple = time.localtime(datetime)
            timeFormatted = time.strftime("%a, %d %b %Y %H:%M:%S", timeTuple)
            postE = etree.Element("div")
            postE.set("id", "post" + str(postID))
            postE.set("class", "span-18 append-bottom last")
            pE = etree.Element("p")
            pE.set("class", "date span-4")
            pE.text = "Posted on " + timeFormatted
            postE.append(pE)

            actualPostE = etree.Element("div")
            actualPostE.set("class", "post prepend-1 span-10")
            h2E = etree.Element("h3")
            aPostLink = etree.Element("a")
            postLink = "/post/" + str(postID)
            aPostLink.set("href", postLink)
            aPostLink.text = item["title"]
            h2E.append(aPostLink)
            actualPostE.append(h2E)
            
            # TODO
            # this is really too much...
            contentE = etree.Element("div")
            content = textile.textile(item["content"]).replace("\n", "")
            parser = etree.HTMLParser()
            tree = etree.parse(StringIO(content), parser)
            for child in tree.getroot():
                children = child.getchildren()
                for item in children:
                    contentE.append(item)

            aE = etree.Element("a")
            aE.set("href", "/post/" + str(postID))
            aE.set("title", "Comment on post")
            aE.text = "Comments"
            pE = etree.Element("p")
            pE.append(aE)
            contentE.append(aE)
            actualPostE.append(contentE)
            postE.append(actualPostE)
            postsE.append(postE)

        posts += "</div>"
        
        etree.tostring(postsE)
        #return render.index(posts)
        return render.index(statusesString, etree.tostring(postsE, pretty_print = True, method="html"))

class license:
    def GET(self):
        return render.license()


class PostsFeed:
    def GET(self):
        title = "Journal of Journal Performance Studies"
        link = "http://journalofjournalperformancestudies.org/feed/rss"
        description = "RSS feed of posts for http://journalofjournalperformancestudies.org"
        
        results = webDB.select("posts", limit=10, order="datetime DESC")

        items = []
        for result in results:
            url = "http://journalofjournalperformancestudies.org/post/" + str(result["pid"])
            datetime = result['datetime']
            timeTuple = time.localtime(datetime)
            timeFormatted = time.strftime("%a, %d %b %Y %H:%M:%S", timeTuple)

            item = PyRSS2Gen.RSSItem(title = result["title"],
                link = url,
                description = textile.textile(result["content"]),
                guid = PyRSS2Gen.Guid(url),
                categories = ["journalofjournalperformancestudies.org"],
                author = "editor@journalofjournalperformancestudies.org",
                pubDate = timeFormatted)
            items.append(item)
        
        rss = PyRSS2Gen.RSS2(title = title,
            link = link,
            description = description,
            lastBuildDate = items[0].pubDate,
            items = items)

        return rss.to_xml()

class podcastFeed:
    def GET(self):
        station = StationSingleton.getStation()

        returnValue = station.mc.get("podcast")
        if returnValue:
            return returnValue
        title = "Journal of Journal Performance Studies Podcast"
        link = "http://journalofjournalperformancestudies.org/radio/feed/rss"
        description = "Podcast for JJPS Radio; http://journalofjournalperformancestudies.org/radio"
        
        items = []
        podcastItems = station.getPodcastItemsList()
        for podcastItem in podcastItems:
            url = "http://journalofjournalperformancestudies.org" + podcastItem["playlist"] 
            datetime = podcastItem['date']
            enclosure = PyRSS2Gen.Enclosure(url, podcastItem["size"], "audio/mpeg")
            item = PyRSS2Gen.RSSItem(title = podcastItem["title"],
                link = url,
                description = "<![CDATA[" + textile.textile(podcastItem["description"]) + "]]>",
                guid = PyRSS2Gen.Guid(url),
                enclosure = enclosure,
                categories = ["journalofjournalperformancestudies.org"],
                author = "editor@journalofjournalperformancestudies.org",
                pubDate = datetime)
            items.append(item)
        
        rss = PyRSS2Gen.RSS2(title = title,
            link = link,
            description = description,
            lastBuildDate = items[0].pubDate,
            items = items)
        
        podcastXML = rss.to_xml()
        station.mc.set("podcast", podcastXML, time = 60 * 24)
        return podcastXML

class extensionIndex:
    def GET(self):
        currentVersion = serverConfig.currentExtensionVersion
        currentPath = serverConfig.currentExtensionPath
        return renderExtension.extensionIndex(currentVersion, currentPath)

class extensionDocumentation:
    def GET(self):
        return renderExtension.extensionDocumentation()

class extensionFactors:
    def GET(self):
        return renderExtension.extensionFactors()

class extensionScreenshots:
    def GET(self):
        return renderExtension.extensionScreenshots()

class extensionStatement:
    def GET(self):
        return renderExtension.extensionStatement()

class extensionCredits:
    def GET(self):
        return renderExtension.extensionCredits()

class extensionDownload:
    def GET(self):
        currentVersion = serverConfig.currentExtensionVersion
        currentPath = serverConfig.currentExtensionPath

        return renderExtension.extensionDownload(currentVersion, currentPath)

class extensionFAQ:
    def GET(self):
        return renderExtension.extensionFAQ()

class extensionDevelopers:
    def GET(self):
        return renderExtension.extensionDevelopers()

class extensionFeatures:
    def GET(self):
        return renderExtension.extensionFeatures()

class radioIndex:
    def GET(self):
        station = StationSingleton.getStation()
        station.reloadXML()
        currentProgram, nextProgram = station.getCurrentAndNextProgram()

        currentProgramName = currentProgram["programName"]
        currentProgramRef = currentProgram["programRef"]

        nextProgramName = nextProgram["programName"]
        nextProgramRef = nextProgram["programRef"]
        
        current = """<h1>On Air</h1><p><a href="/radio/programs/%s">%s</a></p>""" % (currentProgramRef, currentProgramName)
        next  = """<h1>Next</h1><p><a href="/radio/programs/%s">%s</a></p>
        """ % (nextProgramRef, nextProgramName)

        return renderRadio.radioIndex(current, next)

class radioTechnical:
    def GET(self):
        station = StationSingleton.getStation()
        station.reloadXML()
        technicalInfo = station.getAllProgramsTechnicalHTML()
        return renderRadio.radioTechnical(technicalInfo)

class schedule:
    def GET(self):
        station = StationSingleton.getStation()
        station.reloadXML()
        scheduleHTML = station.getScheduleHTML()
        return renderRadio.schedule(scheduleHTML)


class viewPost:
    def GET(self, postID):
        dbVars = dict(postID = postID)
        results = webDB.select("posts", dbVars, where="pid = $postID", order="datetime DESC")
        post = ""
        for item in results:
            datetime = item['datetime']
            timeTuple = time.localtime(datetime)
            timeFormatted = time.strftime("%a, %d %b %Y %H:%M:%S", timeTuple)

            postTitle = item["title"]
            post += "<h2>" + item["title"] + "</h2>\n"
            post += "<div>" + textile.textile(item["content"]) + "</div>\n"
            post += "<p>Posted on " + str(timeFormatted) + "</p>\n"

        results = webDB.select("comments", dbVars, where="pid = $postID", order="datetime DESC")
        comments = []
        for item in results:
            comments.append(item)
        return render.post(postID, postTitle, post, comments)

    def POST(self, postID):
        form = web.input()

        if (form['human'].lower().find("jjps") == -1):
            return "NotHuman"

        if ((form['commentTitle'] != "") and (form['commentText'] != "") and (form['commentName'] != "")):
            sequenceID = webDB.insert("comments", title=form['commentTitle'], content=form['commentText'], handle=form['commentName'], pid=form['postID'], datetime=time.time())

        dbVars = dict(postID = postID)
        results = webDB.select("posts", dbVars, where="pid = $postID", order="datetime DESC")
        post = ""
        for item in results:
            postTitle = item["title"]
            post += "<h2>" + item["title"] + "</h2>\n"
            post += "<div>" + textile.textile(item["content"]) + "</div>\n"
            post += "<p>Posted on " + str(item["datetime"]) + "</p>\n"

        results = webDB.select("comments", dbVars, where="pid = $postID", order="datetime DESC")
        comments = []
        for item in results:
            comments.append(item)
        return render.post(postID, postTitle, post, comments)

# API Handlers
class APIInfo:
    def GET(self):
        return render.API()

class APIOwnership:
    def GET(self, arg):
        bestMimetype = checkMimetype(web.ctx.env.get("HTTP_ACCEPT", "application/xml"))
        station = StationSingleton.getStation()

        if ((bestMimetype == "application/xhtml+xml") or (bestMimetype == "application/xml") or (bestMimetype == "text/xml")):
            journalsXML = station.journalModel.getJournalsOwnedBy(arg)
            web.header("Content-Type", "text/xml; charset=utf-8")
            web.header('Content-Encoding', 'utf-8')
            return journalsXML
        elif ((bestMimetype == "application/rdf") or (bestMimetype == "application/rdf+xml")):
            journalsRDF = station.journalModel.getJournalsOwnedBy(arg, returnFormat="rdf")
            web.header("Content-Type", "application/rdf+xml; charset=utf-8")
            web.header('Content-Encoding', 'utf-8')
            return journalsRDF
        elif (bestMimetype == "application/json"):
            journalsJSON = station.journalModel.getJournalsOwnedBy(arg, returnFormat = "json")
            web.header("Content-Type", "application/json; charset=utf-8")
            web.header('Content-Encoding', 'utf-8')
            return journalsJSON
        else:
            return "Don't know how to respond to that mimetype, sorry."

class APIJournal:
    def GET(self, journalName):
        bestMimetype = checkMimetype(web.ctx.env.get("HTTP_ACCEPT", "application/xml"))
        station = StationSingleton.getStation()

        if ((bestMimetype == "application/xhtml+xml") or (bestMimetype == "application/xml") or (bestMimetype == "text/xml")):
            # Get XML representation of the journal
            journalsXML = station.journalModel.getJournalInfo(journalName)

            # Get the top trending words
            if (random.random() >= 0.5):
                words = station.ppcDocuments.getTrendingWordsByPrice()
            else:
                words = station.ppcDocuments.getTrendingWordsByVolume()
            journalsXML.append(words)
            
            web.header("Content-Type", "text/xml; charset=utf-8")
            web.header('Content-Encoding', 'utf-8')
            return etree.tostring(journalsXML)
        elif ((bestMimetype == "application/rdf") or (bestMimetype == "application/rdf+xml")):
            journalsRDF = station.journalModel.getJournalInfo(journalName, returnFormat="rdf")
            web.header("Content-Type", "application/rdf+xml; charset=utf-8")
            web.header('Content-Encoding', 'utf-8')
            return journalsRDF
        elif (bestMimetype == "application/json"):
            journalsJSON = station.journalModel.getJournalInfo(journalName, returnFormat = "json")
            web.header("Content-Type", "application/json; charset=utf-8")
            web.header('Content-Encoding', 'utf-8')
            return journalsJSON
        else:
            return "Don't know how to respond to that mimetype, sorry."


class APIAds:
    """Return some ad information for use in the extension."""

    def GET(self):
        station = StationSingleton.getStation()
        
        adsXML = station.adsDocuments.getAds()
        # TODO
        # This doesn't work as desired because of the code in getPPCData...need to rewrite there
        options = ["price", "click", "volume"]
        value = random.randint(0, len(options) - 1)
        adsXML.append(station.journalDocuments.getPPCData(sortBy = options[value]))

        # Return
        web.header("Content-Type", "application/xml; charset=utf-8")
        return etree.tostring(adsXML)

class APITest:
    def GET(self, arg):
        bestMimetype = checkMimetype(web.ctx.env.get("HTTP_ACCEPT", "application/xml"))
        return bestMimetype

class APIFile:
    def GET(self, arg):
        return arg

    def POST(self, arg):
        station = StationSingleton.getStation()

        # BEGIN HACK HACK HACK HACK HACK HACK HACK HACK HACK
        # I shouldn't have to do the following...but I do, for some reason, otherwise I get annoying timeout errors when posting from javascript.  See this thread for background info, even though it's a different use-case: http://groups.google.com/group/webpy/browse_thread/thread/b22d7dd17b1e477d/7f823b1aa133ac12?lnk=gst&q=timed+out#7f823b1aa133ac12.
        # This is needed even on files of only 30 bytes or so!
        tmpfile = os.tmpfile()
        contentLength = int(web.ctx.env['CONTENT_LENGTH'])
        if contentLength <= 0:
            raise AssertionError('invalid content length')

        wsgiInput = web.ctx.env['wsgi.input']

        while contentLength > 0:
            chunk = 1024
            if contentLength < chunk:
                chunk = contentLength
            contentLength -= chunk
            currentChunk = wsgiInput.read(chunk)
            #print currentChunk
            tmpfile.write(currentChunk)
        tmpfile.seek(0)

        web.ctx.env['wsgi.input'] = tmpfile 

        data = web.input(myfile = {})
        #data = web.input()
        tmpfile.close()
        # END HACK HACK HACK HACK HACK HACK HACK HACK HACK

        # Writing PDF files, if we get them            
        #file = data["myfile"].file.read()
        #fp = open("test.pdf", "wb")
        #fp.write(file)
        #fp.close()

        # For the moment, as we're testing, save the data to a dict, and then save to a pickled file
        authors = urllib.unquote(data["authors"])
        title = urllib.unquote(data["title"])
        articleText = urllib.unquote(data["articleText"])
        journalTitle = urllib.unquote(data["journalTitle"])

        dataDict = {}
        dataDict["authors"] = authors
        dataDict["title"] = title
        dataDict["articleText"] = articleText
        dataDict["journalTitle"] = journalTitle

        dataDict = station.uploadDocuments.preprocessWebData(dataDict)
        station.uploadDocuments.addDocument(dataDict)

        #pickleFP = open("dataDict.pickle", "wb")
        #cPickle.dump(dataDict, pickleFP)
        #pickleFP.close()
        return urllib.unquote(data["journalTitle"])

class APIVote:
    def POST(self):
        station = StationSingleton.getStation()

        # BEGIN HACK HACK HACK HACK HACK HACK HACK HACK HACK
        # I shouldn't have to do the following...but I do, for some reason, otherwise I get annoying timeout errors when posting from javascript.  See this thread for background info, even though it's a different use-case: http://groups.google.com/group/webpy/browse_thread/thread/b22d7dd17b1e477d/7f823b1aa133ac12?lnk=gst&q=timed+out#7f823b1aa133ac12.
        # This is needed even on files of only 30 bytes or so!
        tmpfile = os.tmpfile()
        contentLength = int(web.ctx.env['CONTENT_LENGTH'])
        if contentLength <= 0:
            raise AssertionError('invalid content length')

        wsgiInput = web.ctx.env['wsgi.input']

        while contentLength > 0:
            chunk = 1024
            if contentLength < chunk:
                chunk = contentLength
            contentLength -= chunk
            currentChunk = wsgiInput.read(chunk)
            #print currentChunk
            tmpfile.write(currentChunk)
        tmpfile.seek(0)

        web.ctx.env['wsgi.input'] = tmpfile 

        data = web.input(myfile = {})
        #data = web.input()
        tmpfile.close()
        # END HACK HACK HACK HACK HACK HACK HACK HACK HACK

        # Writing PDF files, if we get them            
        #file = data["myfile"].file.read()
        #fp = open("test.pdf", "wb")
        #fp.write(file)
        #fp.close()

        # For the moment, as we're testing, save the data to a dict, and then save to a pickled file
        dataDict = {}
        dataDict["articleTitle"] = urllib.unquote(data["articleTitle"])
        dataDict["journalName"] = urllib.unquote(data["journalName"])
        dataDict["currentArticleURL"] = urllib.unquote(data["currentArticleURL"])
        station.voteDocuments.addVote(dataDict["articleTitle"], dataDict)

        web.header("Content-Type", "application/xml; charset=utf-8")
        results = etree.Element("results")
        results.set("done", "true")
        return etree.tostring(results)

class APIPrice:
    def POST(self):
        station = StationSingleton.getStation()

        # BEGIN HACK HACK HACK HACK HACK HACK HACK HACK HACK
        # I shouldn't have to do the following...but I do, for some reason, otherwise I get annoying timeout errors when posting from javascript.  See this thread for background info, even though it's a different use-case: http://groups.google.com/group/webpy/browse_thread/thread/b22d7dd17b1e477d/7f823b1aa133ac12?lnk=gst&q=timed+out#7f823b1aa133ac12.
        # This is needed even on files of only 30 bytes or so!
        tmpfile = os.tmpfile()
        contentLength = int(web.ctx.env['CONTENT_LENGTH'])
        if contentLength <= 0:
            raise AssertionError('invalid content length')

        wsgiInput = web.ctx.env['wsgi.input']

        while contentLength > 0:
            chunk = 1024
            if contentLength < chunk:
                chunk = contentLength
            contentLength -= chunk
            currentChunk = wsgiInput.read(chunk)
            #print currentChunk
            tmpfile.write(currentChunk)
        tmpfile.seek(0)

        web.ctx.env['wsgi.input'] = tmpfile 

        data = web.input(myfile = {})
        #data = web.input()
        tmpfile.close()
        # END HACK HACK HACK HACK HACK HACK HACK HACK HACK

        # Writing PDF files, if we get them            
        #file = data["myfile"].file.read()
        #fp = open("test.pdf", "wb")
        #fp.write(file)
        #fp.close()

        # For the moment, as we're testing, save the data to a dict, and then save to a pickled file
        dataDict = {}
        dataDict["journalName"] = urllib.unquote(data["journalName"]).strip()
        dataDict["price"] = urllib.unquote(data["price"]).strip()
        print dataDict
        station.priceDocuments.addDocumentByName(dataDict["journalName"], dataDict)

        web.header("Content-Type", "application/xml; charset=utf-8")
        results = etree.Element("results")
        results.set("done", "true")
        return etree.tostring(results)


class APIPrograms:
    def GET(self):
        bestMimetype = checkMimetype(web.ctx.env.get("HTTP_ACCEPT", "application/xml"))
        
        station = StationSingleton.getStation()
        station.reloadXML()
        currentProgram, nextProgram = station.getCurrentAndNextProgram()

        currentProgramName = currentProgram["programName"]
        currentProgramRef = currentProgram["programRef"]

        nextProgramName = nextProgram["programName"]
        nextProgramRef = nextProgram["programRef"]
        
        if (bestMimetype == "application/json"):
            programs = {'currentProgram': currentProgramName, 'nextProgram': nextProgramName}
            return json.dumps(programs)
        elif ((bestMimetype == "application/xml") or (bestMimetype == "application/xhtml+xml")):
            responses = etree.Element("results")
            current = etree.Element("current")
            current.text = currentProgramName
            current.set("playing", "1")
            nextProgram = etree.Element("next")
            nextProgram.text = nextProgramName
            responses.append(current)
            responses.append(nextProgram)
            web.header("Content-Type", "application/xml; charset=utf-8")
            return etree.tostring(responses)
        else:
            return "Don't know how to handle that mimetype."

class ViewProgram:
    def GET(self, programRef):
        if (len(programRef) == 0):
            return web.redirect(serverConfig.baseURI + "radio/programs")

        # Get the flavor of a potential response
        HTTP_ACCEPT = web.ctx.env.get("HTTP_ACCEPT")

        station = StationSingleton.getStation()
        station.reloadXML()
        programTitle, programPersons, programDescription = station.getProgramInfoHTML(programRef)
        programArchives = station.getProgramArchivesHTML(programRef)
        if (programArchives is None):
            programArchives = ""
        return renderRadio.program(programTitle, programPersons, programDescription, programArchives)

class ViewProgramList:
    def GET(self):
        station = StationSingleton.getStation()
        station.reloadXML()
        programs = station.getAllProgramsHTML()
        return renderRadio.programs(programs)


# Our admin pages
class adminIndex:
    def GET(self):
        return render.adminIndex(session)

    def POST(self):
        form = web.input()
        results = webDB.query( "select * from users where username = '%s' and password = '%s'" % (form['username'], hashlib.sha256(form['password']).         hexdigest()))
        for result in results:
            # if we get a result, then we ought to be logged in
            session.loggedIn = True
            session.username = form['username']
        return renderAdmin.adminIndex(session)

class adminLogout:
    def GET(self):
        session.kill()
        web.redirect(serverConfig.baseURI + "admin")

class adminShows:
    def GET(self):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        station = StationSingleton.getStation()
        programList = station.getProgramIDsAndNames()
        menu = "<select id='viewShowInfo'>"
        for program in programList:
            menu += "<option value='%s'>%s</option>" % (program[0], program[1])
        menu += "</select>"
        return renderAdmin.adminShows(menu)

class adminPost:
    def GET(self):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        return renderAdmin.adminPost(session, False)

    def POST(self):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")

        form = web.input()
        sequenceID = webDB.insert("posts", title=form['title'], content=form['content'], datetime=time.time(), username=session.username)
        return renderAdmin.adminPost(session, True)

class adminView:
    def GET(self):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        results = webDB.select("posts", order="datetime DESC")
        items = []
        for result in results:
            item = []
            item.append(result['pid'])
            item.append(result['title'])
            item.append(result['content'])
            datetime = result['datetime']
            timeTuple = time.localtime(datetime)
            timeFormatted = time.strftime("%a, %d %b %Y %H:%M:%S", timeTuple)
            item.append(timeFormatted)
            items.append(item)
        return renderAdmin.adminView(items)

class adminViewComments:
    def GET(self):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        results = webDB.select("comments", order="datetime DESC")
        items = []
        for result in results:
            item = []
            item.append(result['cid'])
            item.append(result['title'])
            item.append(result['content'])
            item.append(result['datetime'])
            items.append(item)
        return renderAdmin.adminViewComments(items)

class adminEdit:

    def GET(self, postID):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        dbVars = dict(postID = postID)
        results = webDB.select("posts", dbVars, where="pid = $postID", order="datetime DESC")
        item = []
        for result in results:
            item.append(result['pid'])
            item.append(result['title'])
            item.append(result['content'])
            item.append(result['datetime'])

        return renderAdmin.adminEdit(item)

    def POST(self, postID):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        
        form = web.input()
        print form
        if form.has_key('submitButton'):
            numRows = webDB.update("posts", "pid = " + postID, title=form['title'], content=form['content'], datetime=time.time(), username=session.username)
        elif form.has_key('deleteButton'):
            numRows = webDB.delete("posts", where="pid = " + postID)
        web.redirect(serverConfig.baseURI + "admin/view")

class adminEditComment:

    def GET(self, commentID):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        dbVars = dict(commentID = commentID)
        results = webDB.select("comments", dbVars, where="cid = $commentID", order="datetime DESC")
        item = []
        for result in results:
            item.append(result['cid'])
            item.append(result['pid'])
            item.append(result['title'])
            item.append(result['content'])
            item.append(result['datetime'])

        dbVars = dict(postID = item[1])
        results = webDB.select("posts", dbVars, where="pid = $postID", order="datetime DESC")
        for result in results:
            item.append(result["title"])

        return renderAdmin.adminEditComment(item)

    def POST(self, commentID):
        if (session.loggedIn == False):
            web.redirect(serverConfig.baseURI + "admin")
        
        form = web.input()
        print form
        if form.has_key('submitButton'):
            numRows = webDB.update("comments", "cid = " + commentID, title=form['title'], content=form['content'], datetime=web.SQLLiteral("NOW()"))
        elif form.has_key('deleteButton'):
            numRows = webDB.delete("comments", where="cid = " + commentID)
        web.redirect(serverConfig.baseURI + "admin/viewComments")

# The singleton object for our station, so that we're not opening a million of them for each request
class StationSingleton(object):
    station = None

    def getStation():
        if StationSingleton.station == None:
            StationSingleton.station = Station(configFile = "JJPSConfig.ini")
            StationSingleton.station.journalModel = Model(config = StationSingleton.station.config)
            StationSingleton.station.articleDocuments = ArticleDocuments(config = StationSingleton.station.config)
            StationSingleton.station.priceDocuments = PriceDocuments(config = StationSingleton.station.config)
            StationSingleton.station.voteDocuments = VoteDocuments(config = StationSingleton.station.config, dbName = "jjps_votes")
            StationSingleton.station.uploadDocuments = UploadDocuments(config = StationSingleton.station.config)
            StationSingleton.station.ppcDocuments = PPCDocuments(config = StationSingleton.station.config)
            StationSingleton.station.adsDocuments = AdsDocuments(config = StationSingleton.station.config)
            StationSingleton.station.journalDocuments = JournalDocuments(config = StationSingleton.station.config)
        return StationSingleton.station
    getStation = staticmethod(getStation)

# A helper function that gives us a decent chance of guessing the correct mimetype
def checkMimetype(acceptHeader):
    accept = Accept('Accept', acceptHeader)
    best = accept.best_match(['application/rdf', 'application/rdf+xml', 'text/n3', 'application/xml', 'application/json', 'text/xml', 'application/xhtml+xml'])
    if best is None:
        best = "text/html"
    return best

# Finally, setup our web application
if (serverConfig.fastcgi):
    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)

if __name__ == "__main__":
    app.run(Log)
