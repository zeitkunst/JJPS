window.addEventListener("load", function(){ JJPS._init(); }, false);

const DEFAULT_JJPSPANE_HEIGHT = 300;

var JJPS = {
    preferences: null,
    request: null,
    doc: null,
    logStream: null,
    logFile: null,
    logDisabled: false,

    // Methods to run when we initialize
    _init: function() {
        // Read preferences before we setup event handler
        this._readPrefs();

        // Open SQLite file
        this._getSqlite();

        // Setup event listeners for page load
        var appcontent = document.getElementById("appcontent");   // browser
        if(appcontent)
            appcontent.addEventListener("DOMContentLoaded", JJPS.onPageLoad, true);

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

    onPageLoad: function(aEvent) {
        // Load jquery into the page
        $jq = jQuery.noConflict();

        var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"].getService(Components.interfaces.nsIWindowMediator);
        var enumerator = wm.getEnumerator("navigator:browser");

        JJPS.request = Components.classes["@mozilla.org/xmlextras/xmlhttprequest;1"].createInstance(Components.interfaces.nsIXMLHttpRequest);

        if (JJPS.request.channel instanceof Components.interfaces.nsISupportsPriority) {
            JJPS.request.channel.priority = Components.interfaces.nsISupportsPriority.PRIORITY_LOWEST;
        }


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
    },

    _savePrefs: function() {
        var prefs = this._getPrefs();

        prefs.setCharPref("serverURL", this.serverURL);
    },
}

String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, "");
}

// Show Preferences Dialog
function showJJPSPreferencesDialog(){
    window.open("chrome://JJPS/content/options.xul",                  "JJPSPreferences", "chrome,dialog,centerscreen,alwaysRaised");
}
