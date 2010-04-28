window.addEventListener("load", function(){ JJPS._init(); }, false);

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
        alert("hello");
    },


}

String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, "");
}
