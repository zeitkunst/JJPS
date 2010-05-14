window.addEventListener("load", function() { JJPSPreferences.populate(); }, false);

var JJPSPreferences = {
    // Go through each of the preferences and save them
    save: function() {
        textbox = document.getElementById("JJPSServerURL");
        if (textbox != null)
            JJPS.serverURL = textbox.value;

        JJPS._savePrefs();
    },

    // Take preferences from our instance and populate our dialog window
    populate: function() {
        textbox = document.getElementById("JJPSServerURL");
        if (textbox != null)
            textbox.setAttribute("value", JJPS.serverURL);
    },
}
