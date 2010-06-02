window.addEventListener("load", function() { JJPSPreferences.populate(); }, false);

var JJPSPreferences = {
    // Go through each of the preferences and save them
    save: function() {
        var checkbox = document.getElementById("JJPSEnableOverlays");
        if (checkbox != null)
            JJPS.enableOverlays = checkbox.checked;

        var textbox = document.getElementById("JJPSServerURL");
        if (textbox != null)
            JJPS.serverURL = textbox.value;

        var checkbox = document.getElementById("JJPSShowMarquee");
        if (checkbox != null)
            JJPS.showMarquee = checkbox.checked;

        var checkbox = document.getElementById("JJPSReverseFrobination");
        if (checkbox != null)
            JJPS.reverseFrobination = checkbox.checked;

        JJPS._savePrefs();
    },

    // Take preferences from our instance and populate our dialog window
    populate: function() {
        var checkbox = document.getElementById("JJPSEnableOverlays");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.enableOverlays);

        textbox = document.getElementById("JJPSServerURL");
        if (textbox != null)
            textbox.setAttribute("value", JJPS.serverURL);

        var checkbox = document.getElementById("JJPSShowMarquee");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.showMarquee);

        var checkbox = document.getElementById("JJPSReverseFrobination");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.reverseFrobination);

    },
}
