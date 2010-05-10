#!/usr/bin/env python
# The code in JJPS is available under the GNU GPL V3 (http://www.gnu.org/copyleft/gpl.html) with the following modifications:

# The words "you", "licensee", and "recipient" are redefined to be as follows: "You", "licensee", and "recipient" is defined as anyone as long as s/he is not an EXCLUDED PERSON. An EXCLUDED PERSON is any individual, group, unit, component, synergistic amalgamation, cash-cow, chunk, CEO, CFO, worker, or organization of a corporation that is a member, as of the date of acquisition of this software, of the Fortune 1000 list of the world's largest businesses. (See http://money. cnn.com/magazines/fortune/global500/2008/full_list/ for an example of the top 500.) An EXCLUDED PERSON shall also include anyone working in a contractor, subcontractor, slave, or freelance capacity for any member of the Fortune 1000 list of the world's largest businesses.

# Please see http://.org/license.
# Just a test

import sys

import urllib
import urllib2
import datetime
import threading
import operator
import logging
import hashlib
from xml.sax.saxutils import escape, quoteattr


import feedparser
import PyRSS2Gen
from BeautifulSoup import BeautifulSoup
from lxml import etree
import web
from wsgilog import WsgiLog, LogIO
import textile

# My own library imports
from JJPS.Station import Station

import serverConfig

version = "0.01"

urls = (
    '/', 'index',
    '/schedule', 'schedule',
    '/programs/(.*?)', 'ViewProgram'
)

app = web.application(urls, globals())
#webDB = web.database(dbn='mysql', db='MAICgregator', user='MAICgregator', pw='violas')
if web.config.get('_session') is None:
    session = web.session.Session(app, web.session.DiskStore('sessions'),  initializer = {'loggedIn': False})
    web.config._session = session
else:
    session = web.config._session

render = web.template.render('templates/', base = 'layout', cache = serverConfig.cache)
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

class ViewProgram:
    def GET(self, programRef):
        station = StationSingleton.getStation()
        station.reloadXML()
        programHTML = station.getProgramInfoHTML(programRef)
        return render.schedule(programHTML)


class StationSingleton(object):
    station = None

    def getStation():
        if StationSingleton.station == None:
            StationSingleton.station = Station(configFile = "JJPSConfig.ini")
        return StationSingleton.station
    getStation = staticmethod(getStation)

# Finally, setup our web application
#if (config.fastcgi):
#    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)

if __name__ == "__main__":
    app.run(Log)
