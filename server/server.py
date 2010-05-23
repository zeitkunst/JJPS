#!/usr/bin/env python
# The code in JJPS is available under the GNU GPL V3 (http://www.gnu.org/copyleft/gpl.html) with the following modifications:

# The words "you", "licensee", and "recipient" are redefined to be as follows: "You", "licensee", and "recipient" is defined as anyone as long as s/he is not an EXCLUDED PERSON. An EXCLUDED PERSON is any individual, group, unit, component, synergistic amalgamation, cash-cow, chunk, CEO, CFO, worker, or organization of a corporation that is a member, as of the date of acquisition of this software, of the Fortune 1000 list of the world's largest businesses. (See http://money. cnn.com/magazines/fortune/global500/2008/full_list/ for an example of the top 500.) An EXCLUDED PERSON shall also include anyone working in a contractor, subcontractor, slave, or freelance capacity for any member of the Fortune 1000 list of the world's largest businesses.

# Please see http://.org/license.
# Just a test

import os
import sys

import logging
import hashlib


import simplejson as json
import web
from wsgilog import WsgiLog, LogIO
from webob.acceptparse import Accept
from lxml import etree

# My own library imports
from JJPS.Station import Station
from JJPS.Model import Model 

import serverConfig

version = "0.01"

urls = (
    # Front-end URIs
    '/', 'index',
    '/schedule', 'schedule',
    '/programs/(.*?)', 'ViewProgram',
    # API URIs
    '/API', 'APIInfo',
    '/API/ownership/(.*?)', 'APIOwnership',
    '/API/journal/(.*?)', 'APIJournal',
    '/API/test/(.*?)', 'APITest',
    '/API/file/(.*?)', 'APIFile',
    '/API/programs', 'APIPrograms',
    # Admin URIs
    '/admin', 'adminIndex',
    '/admin/', 'adminIndex',
    '/admin/logout', 'adminLogout',
    '/admin/shows', 'adminShows'
)

app = web.application(urls, globals())
webDB = web.database(dbn='mysql', db='JJPS', user='JJPS', pw='jjps314')
if web.config.get('_session') is None:
    session = web.session.Session(app, web.session.DiskStore('sessions'),  initializer = {'loggedIn': False})
    web.config._session = session
else:
    session = web.config._session

render = web.template.render('templates/', base = 'layout', cache = serverConfig.cache)
renderAdmin = web.template.render('templates/', base = 'layoutAdmin', cache = serverConfig.cache)
#renderAdmin = web.template.render('templates/', base = 'layoutAdmin', cache = config.cache)

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
        station.reloadXML()
        currentProgram, nextProgram = station.getCurrentAndNextProgram()

        currentProgramName = currentProgram["programName"]
        currentProgramRef = currentProgram["programRef"]

        nextProgramName = nextProgram["programName"]
        nextProgramRef = nextProgram["programRef"]

        currentNextHTML = """<p>On Air: <a href="/programs/%s">%s</a></p>
        <p>Coming Up: <a href="/programs/%s">%s</a></p>
        """ % (currentProgramRef, currentProgramName, nextProgramRef, nextProgramName)

        return render.index(currentNextHTML, "<p>This is a test</p>")

class schedule:
    def GET(self):
        station = StationSingleton.getStation()
        station.reloadXML()
        scheduleHTML = station.getScheduleHTML()
        return render.schedule(scheduleHTML)

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
            journalsXML = station.journalModel.getJournalInfo(journalName)
            web.header("Content-Type", "text/xml; charset=utf-8")
            web.header('Content-Encoding', 'utf-8')
            return journalsXML
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


class APITest:
    def GET(self, arg):
        bestMimetype = checkMimetype(web.ctx.env.get("HTTP_ACCEPT", "application/xml"))
        return bestMimetype

class APIFile:
    def GET(self, arg):
        return arg

    def POST(self, arg):
        print web.ctx.environ
        tmpfile = os.tmpfile()
        contentLength = int(web.ctx.env['CONTENT_LENGTH'])
        if contentLength <= 0:
            raise AssertionError('invalid content length')

        # BEGIN HACK HACK HACK HACK HACK HACK HACK HACK HACK
        # I shouldn't have to do the following...but I do, for some reason, otherwise I get annoying timeout errors when posting from javascript.  See this thread for background info, even though it's a different use-case: http://groups.google.com/group/webpy/browse_thread/thread/b22d7dd17b1e477d/7f823b1aa133ac12?lnk=gst&q=timed+out#7f823b1aa133ac12.
        # This is needed even on files of only 30 bytes or so!
        wsgiInput = web.ctx.env['wsgi.input']

        while contentLength > 0:
            chunk = 1024
            if contentLength < chunk:
                chunk = contentLength
            contentLength -= chunk
            currentChunk = wsgiInput.read(chunk)
            print currentChunk
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
        return data["foo"]

    def PUT(self, arg):
        data = web.input()
        print data.keys()
        #fp = open("foo", "wb")
        #fp.write(data["myfile"])
        #fp.close()

        return "Got "

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
        # Get the flavor of a potential response
        HTTP_ACCEPT = web.ctx.env.get("HTTP_ACCEPT")

        station = StationSingleton.getStation()
        station.reloadXML()
        programHTML = station.getProgramInfoHTML(programRef)
        return render.schedule(programHTML)

# Our admin pages
class adminIndex:
    def GET(self):
        return render.adminIndex(session)

    def POST(self):
        form = web.input()
        result = webDB.query( "select * from users where username = '%s' and    password = '%s'" % (form['username'], hashlib.sha256(form['password']).         hexdigest()))
        if len(result)>0:
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


# The singleton object for our station, so that we're not opening a million of them for each request
class StationSingleton(object):
    station = None

    def getStation():
        if StationSingleton.station == None:
            StationSingleton.station = Station(configFile = "JJPSConfig.ini")
            StationSingleton.station.journalModel = Model(config = StationSingleton.station.config)
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
#if (config.fastcgi):
#    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)

if __name__ == "__main__":
    app.run(Log)
