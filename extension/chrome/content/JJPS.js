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


}

String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, "");
}
