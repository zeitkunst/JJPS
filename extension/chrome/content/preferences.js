window.addEventListener("load", function() { JJPSPreferences.populate(); }, false);

var JJPSPreferences = {
    save: function() {
        textbox = document.getElementById("JJPSServerURL");
        if (textbox != null)
            JJPS.serverURL = textbox.value;

        JJPS._savePrefs();
    },

    populate: function() {
        textbox = document.getElementById("JJPSServerURL");
        if (textbox != null)
            textbox.setAttribute("value", JJPS.serverURL);
    },
}
