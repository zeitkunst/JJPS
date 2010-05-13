window.addEventListener("load", function(){ JJPS._init(); }, false);

const DEFAULT_JJPSPANE_HEIGHT = 300;

var JJPS = {
    preferences: null,
    request: null,
    doc: null,
    logStream: null,
    logFile: null,
    logDisabled: false,

    // TODO
    // move to preferences
    serverURL: "http://localhost:8080/API/",


    // Methods to run when we initialize
    _init: function() {
        // Setup event listeners for page load
        var appcontent = document.getElementById("appcontent");   // browser
        if(appcontent)
            appcontent.addEventListener("DOMContentLoaded", JJPS.onPageLoad, true);

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

    toggleDisplay: function() {
        var JJPSPane = document.getElementById("JJPSPane");

        if (JJPSPane.getAttribute("hidden") == "true") {
            var isHidden = true;
        }

        if (JJPSPane.getAttribute("collapsed") == "true") {
            var isCollapsed = true;
        }

        if (isHidden || isCollapsed) {
            var makeVisible = true;
        }

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

            var max = document.getElementById('appcontent').boxObject.height;

            if (isHidden) {
                JJPSPane.setAttribute('height', Math.min(savedHeight, max));
                JJPSPane.setAttribute('hidden', false);
            }
            if (isCollapsed) {
                JJPSPane.setAttribute('height', Math.min(savedHeight, max));
                JJPSPane.setAttribute('collapsed', false);
            }

        } else {
            JJPSPane.setAttribute("collapsed", true);
            JJPSPane.height = 0;
            window.content.window.focus();
        }
    },

    processProgramList: function() {
        if (JJPS.request.readyState < 4) {
            return;
        }
        var results = JJPS.request.responseXML;
        description = document.getElementById("JJPSPaneCaption");
        current = results.getElementsByTagName("current")[0];
        next = results.getElementsByTagName("next")[0];
        displayString = "Current Program: " + current.firstChild.nodeValue + "\r\n";
        displayString += "Next Program: " + next.firstChild.nodeValue + "\r\n";
        description.value = displayString
    },

}

String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, "");
}
