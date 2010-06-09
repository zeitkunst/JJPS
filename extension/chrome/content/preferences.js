window.addEventListener("load", function() { JJPSPreferences.populate(); }, false);

var JJPSPreferences = {
    // Go through each of the preferences and save them
    save: function() {
        var checkbox = document.getElementById("JJPSEnableOverlays");
        if (checkbox != null)
            JJPS.enableOverlays = checkbox.checked;

        var checkbox = document.getElementById("JJPSReplaceAds");
        if (checkbox != null)
            JJPS.replaceAds = checkbox.checked;

        var checkbox = document.getElementById("JJPSCiteULike");
        if (checkbox != null)
            JJPS.citeULike = checkbox.checked;

        var checkbox = document.getElementById("JJPSGoogleScholar");
        if (checkbox != null)
            JJPS.googleScholar = checkbox.checked;

        var checkbox = document.getElementById("JJPSElsevier");
        if (checkbox != null)
            JJPS.elsevier = checkbox.checked;

        var checkbox = document.getElementById("JJPSInformaWorld");
        if (checkbox != null)
            JJPS.informaWorld = checkbox.checked;

        var checkbox = document.getElementById("JJPSIngentaConnect");
        if (checkbox != null)
            JJPS.ingentaConnect = checkbox.checked;

        var checkbox = document.getElementById("JJPSJohnWileyAndSons");
        if (checkbox != null)
            JJPS.johnWileyAndSons = checkbox.checked;

        var checkbox = document.getElementById("JJPSSagePublications");
        if (checkbox != null)
            JJPS.sagePublications = checkbox.checked;

        var checkbox = document.getElementById("JJPSSpringer");
        if (checkbox != null)
            JJPS.springer = checkbox.checked;

        var checkbox = document.getElementById("JJPSTaylorAndFrancis");
        if (checkbox != null)
            JJPS.taylorAndFrancis = checkbox.checked;

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
        var checkbox = document.getElementById("JJPSReplaceAds");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.replaceAds);

        var checkbox = document.getElementById("JJPSEnableOverlays");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.enableOverlays);

        var checkbox = document.getElementById("JJPSCiteULike");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.citeULike);

        var checkbox = document.getElementById("JJPSGoogleScholar");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.googleScholar);

        var checkbox = document.getElementById("JJPSElsevier");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.elsevier);

        var checkbox = document.getElementById("JJPSInformaWorld");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.informaWorld);

        var checkbox = document.getElementById("JJPSIngentaConnect");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.ingentaConnect);

        var checkbox = document.getElementById("JJPSJohnWileyAndSons");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.johnWileyAndSons);

        var checkbox = document.getElementById("JJPSSagePublications");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.sagePublications);

        var checkbox = document.getElementById("JJPSSpringer");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.springer);

        var checkbox = document.getElementById("JJPSTaylorAndFrancis");
        if (checkbox != null)
            checkbox.setAttribute("checked", JJPS.taylorAndFrancis);

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
