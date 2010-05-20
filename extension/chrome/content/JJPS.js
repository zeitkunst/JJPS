window.addEventListener("load", function(){ JJPS._init(); }, false);

const DEFAULT_JJPSPANE_HEIGHT = 300;

var JJPS = {
    preferences: null,
    request: null,
    doc: null,
    logStream: null,
    logFile: null,
    logDisabled: false,
    regExps: null,

    // Methods to run when we initialize
    _init: function() {
        // Read preferences before we setup event handler
        this._readPrefs();

        // Open SQLite file
        this._getSqlite();

        // Create regexps and their corresponding methods
        this._setupRegexps();

        // Setup event listeners for page load
        var appcontent = document.getElementById("appcontent");   // browser
        if(appcontent)
            appcontent.addEventListener("DOMContentLoaded", JJPS.onPageLoad, true);

    },

    // Setup our regular expressions
    _setupRegexps: function() {
        JJPS.regExps = new Array();

        wileyArray = new Array();
        wileyArray.push("Wiley Interscience");
        wileyArray.push(new RegExp("http://(.+?).interscience.wiley.com"));        
        wileyArray.push(JJPS._processWiley);        

        scienceDirectArray = new Array();
        scienceDirectArray.push("Science Direct");
        scienceDirectArray.push(new RegExp("http://(.+?).sciencedirect.com"));        
        scienceDirectArray.push(JJPS._processScienceDirect);        

        sagePublicationsArray = new Array();
        sagePublicationsArray.push("Sage Publications");
        sagePublicationsArray.push(new RegExp("http://(.+?).sagepub.com"));        
        sagePublicationsArray.push(JJPS._processSagePublications);        

        taylorAndFrancisArray = new Array();
        taylorAndFrancisArray.push("Taylor & Francis");
        taylorAndFrancisArray.push(new RegExp("http://(.+?).tandf.co.uk"));        
        taylorAndFrancisArray.push(JJPS._processTaylorAndFrancis);        

        SpringerArray = new Array();
        SpringerArray.push("Springer");
        SpringerArray.push(new RegExp("http://(.+?).springerlink.com"));        
        SpringerArray.push(JJPS._processSpringer);        


        JJPS.regExps.push(wileyArray);
        JJPS.regExps.push(scienceDirectArray);
        JJPS.regExps.push(sagePublicationsArray);
        JJPS.regExps.push(taylorAndFrancisArray);
        JJPS.regExps.push(SpringerArray);
    },

    // Return a connection to a local SQL store
    // TODO
    // Do we need this?
    _getSqlite: function() {
        var file = Components.classes["@mozilla.org/file/directory_service;1"].getService(Components.interfaces.nsIProperties).get("ProfD", Components.interfaces.nsIFile); 
        file.append("JJPS.sqlite");
        var storageService = Components.classes["@mozilla.org/storage/service;1"].getService(Components.interfaces.mozIStorageService);
        var mDBConn = storageService.openDatabase(file); // Will also create the file if it does not exist
        this.dbConn = mDBConn;
    },

    // Get a particular request object
    // TODO
    // Do we need this?  Probably, because we have a few different types of requests possibly going on...
    _getRequest: function() {
        var newRequest = null;
        newRequest = Components.classes["@mozilla.org/xmlextras/xmlhttprequest;1"].createInstance(Components.interfaces.nsIXMLHttpRequest);

        if (newRequest.channel instanceof Components.interfaces.nsISupportsPriority) {
            newRequest.channel.priority = Components.interfaces.nsISupportsPriority.PRIORITY_LOWEST;
        }
        
        return newRequest;
    },

    onPageLoad: function(aEvent) {
        // Load jquery into the page
        $jq = jQuery.noConflict();

        // Get our doc element
        JJPS.doc = aEvent.originalTarget;

        var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"].getService(Components.interfaces.nsIWindowMediator);
        var enumerator = wm.getEnumerator("navigator:browser");

        JJPS.request = Components.classes["@mozilla.org/xmlextras/xmlhttprequest;1"].createInstance(Components.interfaces.nsIXMLHttpRequest);

        if (JJPS.request.channel instanceof Components.interfaces.nsISupportsPriority) {
            JJPS.request.channel.priority = Components.interfaces.nsISupportsPriority.PRIORITY_LOWEST;
        }

        // Get current location
        var loc = JJPS.doc.location.href;

        // Save the site index (if we get it)
        var siteIndex = -1;

        for (regExIndex in JJPS.regExps) {
            currentRegExp = JJPS.regExps[regExIndex];
            regExpResult = currentRegExp[1].exec(loc);

            if (loc != null && regExpResult != null) {
                // Okay, this is the one
                siteIndex = regExIndex;
                break;
            }
        }

        // Not on a site that we can do anything with, so return
        if (siteIndex == -1) {
            return;
        }

        // Okay, start the scraping!
        siteName = JJPS.regExps[siteIndex][0];
        siteMethod = JJPS.regExps[siteIndex][2];
        siteMethod(JJPS.doc);
       
    },

    // Process Wiley Interscience
    // TODO
    // get wiley pricing info
    _processWiley: function(doc) {
        journalTitleDiv = doc.getElementById("titleHeaderLeft");

        if (journalTitleDiv != null) {
            // 2nd div -> 1st h2 -> 1st a -> text
            journalTitle = journalTitleDiv.childNodes[1].childNodes[0].childNodes[0].innerHTML;
            alert(journalTitle);
        }
    },

    // Process Science Direct
    _processScienceDirect: function(doc) {
        journalTitle = "";

        journalTitleElements = getElementsByClassName(doc, "pubTitle");
        if (journalTitleElements != "") {
            journalTitle = journalTitleElements[0].innerHTML;

        }

        journalTitleArticleId = JJPS.doc.getElementById("artiHead");
        if (journalTitleArticleId != null) {
            journalTitle = journalTitleArticleId.childNodes[1].innerHTML;
        }

        // If we actually have something, do the request
        if (journalTitle != "") {
            journalTitle = journalTitle.replace(/<.*?>/g, '').trim();

            JJPS.journalRequest = JJPS._getRequest();
            JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + journalTitle, true);
            JJPS.journalRequest.setRequestHeader('Accept', 'application/xml');
            JJPS.journalRequest.onreadystatechange = JJPS.processJournalResult;
            JJPS.journalRequest.send(null);
        }

        // Replacing ads            
        leaderboard = JJPS.doc.getElementById("leaderboard");
        if (leaderboard != null) {
            leaderboard.innerHTML = "<p style='font-size: 4em;'><blink>BUY ME!!!</blink><p>";        
        }

        skyscraper = JJPS.doc.getElementById("skyscraper");
        if (skyscraper != null) {
            skyscraper.innerHTML = "<p style='font-size: 4em;'><blink>BUY ME!!!</blink><p>";        
        }

        boombox = JJPS.doc.getElementById("boombox");
        if (boombox != null) {
            boombox.innerHTML = "<p style='font-size: 4em;'><blink>BUY ME!!!</blink><p>";        
        }
    },

    // TODO
    // get sage pricing info
    _processSagePublications: function(doc) {
        pageTitle = JJPS.doc.getElementsByTagName("title")[0].innerHTML;
        
        if ((pageTitle.match(/^Browse/) != null) || (pageTitle.match(/^SAGE/) != null) || (pageTitle.match(/^My Marked/) != null)) {
            return;
        }         

        if (pageTitle != "") {
            pageTitle = pageTitle.replace(/<.*?>/g, '').trim();

            JJPS.journalRequest = JJPS._getRequest();
            JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + pageTitle, true);
            JJPS.journalRequest.setRequestHeader('Accept', 'application/xml');
            JJPS.journalRequest.onreadystatechange = JJPS.processJournalResult;
            JJPS.journalRequest.send(null);
        }

    },

    // TODO
    // get springer pricing info
    _processSpringer: function(doc) {
        h2Node = getElementsByClassName(doc, "MPReader_Profiles_SpringerLink_Content_PrimitiveHeadingControlName");
        
        if (h2Node != "") {
            pageTitle = h2Node[0].innerHTML;
        } else {
            pageTitle = "";
        }

        if (pageTitle != "") {
            pageTitle = pageTitle.replace(/<.*?>/g, '').trim();

            JJPS.journalRequest = JJPS._getRequest();
            JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + pageTitle, true);
            JJPS.journalRequest.setRequestHeader('Accept', 'application/xml');
            JJPS.journalRequest.onreadystatechange = JJPS.processJournalResult;
            JJPS.journalRequest.send(null);
        }
    },


    // Taylor & Francis
    _processTaylorAndFrancis: function(doc) {
        var journalProductNode = JJPS.doc.getElementById("productSection");
        var journalH1 = journalProductNode.getElementsByTagName("h1")[0];

        journalTitle = journalH1.innerHTML;

        if (journalTitle != "") {
            journalTitle = journalTitle.replace(/<.*?>/g, '').trim();

            JJPS.journalRequest = JJPS._getRequest();
            JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + journalTitle, true);
            JJPS.journalRequest.setRequestHeader('Accept', 'application/xml');
            JJPS.journalRequest.onreadystatechange = JJPS.processJournalResult;
            JJPS.journalRequest.send(null);
        }
    },


    // Process the result info from our journal request
    processJournalResult: function() {
        if (JJPS.journalRequest.readyState < 4) {
            return;
        }

        // Reread our preferences
        JJPS._readPrefs();

        var results = JJPS.journalRequest.responseXML;
        var result = results.getElementsByTagName("result")[0];
        var price = result.getAttribute("price");
        var ownerName = result.getAttribute("ownerName");
        var parentName = result.getAttribute("parentName");
        
        overlayDiv = JJPS.doc.createElement("div");
        overlayDiv.id = "JJPSInfoDiv";
        overlayDiv.style.position = "fixed";
        overlayDiv.style.bottom = "0em";
        overlayDiv.style.left = "0em";
        overlayDiv.style.width = "100%";
        overlayDiv.style.height = "2em";
        overlayDiv.style.fontSize = "0.8em";
        overlayDiv.style.backgroundColor = "#000000";
        overlayDiv.style.color = "#ff0000";
        overlayDiv.style.zIndex = "100";
        if (JJPS.showMarquee) {
            // TODO
            // work on marquee code to slow it down!
            overlayDiv.innerHTML = "<div id='testMarquee'>This journal is owned by " + ownerName + ", a subsidiary of " + parentName + ", and costs universities $" + price + " per year!</div>";
            

            // Load jquery into the page
            JJPS.doc.body.insertBefore(overlayDiv, JJPS.doc.body.childNodes[0]);
            $jq = jQuery.noConflict();

            // We get the following code from http://jsbin.com/uyawi/3/edit
            // Have to fix things up to work with the version of jquery we have and the particular contexts we need
            var marquee = $jq("#testMarquee", JJPS.doc);
            marquee.css({"overflow": "hidden", "width": "100%"});

            // wrap "My Text" with a span (IE doesn't like divs inline-block)
            marquee.wrapInner("<span>");
            marquee.find("span").css({ "width": "50%", "display": "inline-block", "text-align":"center" });
            marquee.append(marquee.find("span").clone()); // now there are two spans with "My Text"

            marquee.wrapInner("<div>");
            marquee.find("div").css("width", "200%");

            var reset = function() {
                $jq(this, JJPS.doc).css("margin-left", "0%");
                $jq(this, JJPS.doc).animate({ marginLeft: "-100%" }, 12000, 'linear', reset);
            };

            reset.call(marquee.find("div"));
            //marquee.animate({ "margin-left": "-100%" }, {queue: false, duration: 3000});
            //reset.call(marquee.find("div"));

        } else {
            overlayDiv.innerHTML = "This journal is owned by " + ownerName + ", a subsidiary of " + parentName + ", and costs universities $" + price + " per year!";
        }
        JJPS.doc.body.insertBefore(overlayDiv, JJPS.doc.body.childNodes[0]);
    },

    // Toggle the display of the bottom panel
    // Taken and modified from the similar method in zotero
    toggleDisplay: function() {
        var JJPSPane = document.getElementById("JJPSPane");
        var JJPSSplitter = document.getElementById("JJPSSplitter");

        if (JJPSPane.getAttribute("hidden") == "true") {
            var isHidden = true;
        }

        if (JJPSPane.getAttribute("collapsed") == "true") {
            var isCollapsed = true;
        }

        if (isHidden || isCollapsed) {
            var makeVisible = true;
        }
        
        JJPSSplitter.setAttribute('hidden', !makeVisible);

        if (JJPSPane.hasAttribute('savedHeight')) {
            var savedHeight = JJPSPane.getAttribute('savedHeight');
        } else {
            var savedHeight = DEFAULT_JJPSPANE_HEIGHT;
        }

        if (makeVisible) {
            // Load up current and next program list
            // TODO
            // save in cache and only retrieve after a certain amount of time has passed
            // or, possibly, setup a timer to check regularly
            JJPS.request.open("GET", JJPS.serverURL + "programs", true);
            JJPS.request.setRequestHeader('Accept', 'application/xml');
            JJPS.request.onreadystatechange = JJPS.processProgramList;
            JJPS.request.send(null);

            var max = document.getElementById('appcontent').boxObject.height - JJPSSplitter.boxObject.height;

            if (isHidden) {
                JJPSPane.setAttribute('height', Math.min(savedHeight, max));
                JJPSPane.setAttribute('hidden', false);
            }
            else if (isCollapsed) {
                JJPSPane.setAttribute('height', Math.min(savedHeight, max));
                JJPSPane.setAttribute('collapsed', false);
            }

        } else {
            JJPSPane.setAttribute("collapsed", true);
            JJPSPane.height = 0;
            window.content.window.focus();
        }
    },

    isShowing: function() {
        var JJPSPane = document.getElementById("JJPSPane");
        return JJPSPane.getAttribute('hidden') != 'true' && JJPSPane.getAttribute('collapsed') != 'true';
    },

    updatePaneHeight: function() {
        var JJPSPane = document.getElementById("JJPSPane");
        
        if (this.isShowing()) {
            JJPSPane.setAttribute('savedHeight', JJPSPane.boxObject.height);
        }
    },

    // Process the returned program list from our API and update the labels
    processProgramList: function() {
        if (JJPS.request.readyState < 4) {
            return;
        }
        var results = JJPS.request.responseXML;
        description = document.getElementById("JJPSPaneCaption");
        currentLabel = document.getElementById("JJPSRadioCurrent");
        nextLabel = document.getElementById("JJPSRadioNext");
        current = results.getElementsByTagName("current")[0];
        next = results.getElementsByTagName("next")[0];
        displayString = "Current Program: " + current.firstChild.nodeValue + "\r\n";
        displayString += "Next Program: " + next.firstChild.nodeValue + "\r\n";
        //description.value = displayString
        currentLabel.value = current.firstChild.nodeValue;
        nextLabel.value = next.firstChild.nodeValue;
    },

    //////////////////////////////////////////////////
    // Preferences
    //////////////////////////////////////////////////

    // Return a preferences instance
    _getPrefs: function() {
        if (!this.preferences){
            var prefSvc = Components.classes["@mozilla.org/preferences-service;1"].getService(Components.interfaces.nsIPrefService);
            this.preferences = prefSvc.getBranch("extensions.JJPS.");
        }
        return this.preferences;
    },

    _readPrefs: function() {
        var prefs = this._getPrefs();
        this.serverURL = prefs.getCharPref("serverURL");
        this.showMarquee = prefs.getBoolPref("showMarquee");
    },

    _savePrefs: function() {
        var prefs = this._getPrefs();

        prefs.setCharPref("serverURL", this.serverURL);
        prefs.setBoolPref("showMarquee", this.showMarquee);
    },
}

String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, "");
}

// Show Preferences Dialog
function showJJPSPreferencesDialog(){
    window.open("chrome://JJPS/content/options.xul", "JJPSPreferences", "chrome,dialog,centerscreen,alwaysRaised");
}

function getElementsByClassName(domElement, className) {
    var a = [];
    var re = new RegExp('\\b' + className + '\\b');
    var els = domElement.getElementsByTagName("*");
    for(var i=0,j=els.length; i<j; i++)
        if(re.test(els[i].className))a.push(els[i]);
    return a;
}
