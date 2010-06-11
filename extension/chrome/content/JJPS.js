window.addEventListener("load", function(){ JJPS._init(); }, false);

const DEFAULT_JJPSPANE_HEIGHT = 300;

var JJPS = {
    preferences: null,
    previousState: null,
    adRequest: null,
    request: null,
    programRequest: null,
    voteRequest: null,
    uploadEnabled: false,
    postData: null,
    newsItemIndex: null,
    headlineSwitchInterval: null,
    doc: null,
    clipboardInfo: null,
    logStream: null,
    logFile: null,
    logDisabled: false,
    regExps: null,
    currentJournalName: null,
    currentArticleTitle: null,
    currentArticleURL: null,
    trendingWords: null,
    trendingWordsIndex: null,
    trendingWordsInterval: null,
    factorsList: new Array("Frobpact Factor", "Eigenfrob Factor", "Frobfluence", "SJR", "HIndex", "Click Value"),

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

        CiteULikeArray = new Array();
        CiteULikeArray.push("CiteULike");
        CiteULikeArray.push(new RegExp("http://(.+?).citeulike.org"));        
        CiteULikeArray.push(JJPS._processCiteULike);        

        GoogleScholarArray = new Array();
        GoogleScholarArray.push("GoogleScholar");
        GoogleScholarArray.push(new RegExp("http://scholar.google.com/scholar"));        
        GoogleScholarArray.push(JJPS._processGoogleScholar);        

        IngentaConnectArray = new Array();
        IngentaConnectArray.push("IngentaConnect");
        IngentaConnectArray.push(new RegExp("http://(.+?).ingentaconnect.com"));        
        IngentaConnectArray.push(JJPS._processIngentaConnect);        

        InformaWorldArray = new Array();
        InformaWorldArray.push("InformaWorld");
        InformaWorldArray.push(new RegExp("http://(.+?).informaworld.com"));        
        InformaWorldArray.push(JJPS._processInformaWorld);        


        JJPS.regExps.push(wileyArray);
        JJPS.regExps.push(scienceDirectArray);
        JJPS.regExps.push(sagePublicationsArray);
        JJPS.regExps.push(taylorAndFrancisArray);
        JJPS.regExps.push(SpringerArray);
        JJPS.regExps.push(CiteULikeArray);
        JJPS.regExps.push(GoogleScholarArray);
        JJPS.regExps.push(IngentaConnectArray);
        JJPS.regExps.push(InformaWorldArray);
    },

    // Create the factors subpanel for the header
    _createFactorsSubpanel: function() {
        var list = JJPS.factorsList;        

        var div = JJPS.doc.createElement("div");
        div.className = "subpanel";

        var h3 = JJPS.doc.createElement("h3");
        h3.innerHTML = "Factors";

        var ul = JJPS.doc.createElement("ul");
        ul.id = "JJPSHeaderFactorsUL";

        numElements = list.length;

        for (i = 0; i < numElements; i++) {
            var factor = JJPS.factorsList[i];
            var factorNospaces = factor.replace(/ /, "");

            var li = JJPS.doc.createElement("li");
            li.id = "JJPS" + factorNospaces;

            var span = JJPS.doc.createElement("span");
            span.id = "JJPS" + factorNospaces + "Name";
            span.innerHTML = factor + ": ";
            li.appendChild(span);

            var span = JJPS.doc.createElement("span");
            span.id = "JJPS" + factorNospaces + "Value";
            span.innerHTML = "";
            li.appendChild(span);
            
            ul.appendChild(li);
        }

        div.appendChild(ul);

        var li = JJPS.doc.createElement("li");
        li.id = "JJPSFactorsSubpanel";
        var a = JJPS.doc.createElement("a");
        a.setAttribute("href", "#");
        a.innerHTML = "Factors";
        li.appendChild(a);
        li.appendChild(div);

        return li;
    },

    // Create the graph subpanel
    _createGraphSubpanel: function(ownerName) {

        var div = JJPS.doc.createElement("div");
        div.className = "subpanel";

        var h3 = JJPS.doc.createElement("h3");
        h3.innerHTML = "Ownership Graph for " + ownerName;
        
        var img = JJPS.doc.createElement("img");
        img.id = "JJPSGraphImage";

        div.appendChild(img);
        div.appendChild(h3);

        var li = JJPS.doc.createElement("li");
        li.id = "JJPSGraphSubpanel";
        var a = JJPS.doc.createElement("a");
        a.setAttribute("href", "#");
        a.innerHTML = "Graph";
        li.appendChild(a);
        li.appendChild(div);

        return li;
    },


    // Setup the jquery methods for our panel
    _setPanelsJQuery: function() {
        $jq = jQuery.noConflict();

        $jq("#JJPSFactorsSubpanel a:first, #JJPSGraphSubpanel a:first", JJPS.doc).click(
        function() {
            if ($jq(this, JJPS.doc).next(".subpanel").is(":visible")) {
                $jq(this, JJPS.doc).next(".subpanel").fadeOut("slow");
                $jq("#JJPSHeaderDiv li a").removeClass("active");
            } else {
                $jq(".subpanel", JJPS.doc).fadeOut("slow");
                // TODO
                // Figure out why toggle doesn't work on the next line
                $jq(this, JJPS.doc).next(".subpanel").css("display", "block");
                $jq(this, JJPS.doc).next(".subpanel").css("opacity", 0.0);
                $jq(this, JJPS.doc).next(".subpanel").animate({"opacity": 1.0}, 600);
                $jq("#JJPSHeaderDiv li a").removeClass("active");
                $jq(this, JJPS.doc).toggleClass("active");
            }

            return false;
        });
    },

    _resetVariables: function() {
        JJPS.uploadEnabled = false;
        JJPS.postData = new Array();
    },

    _setupCopy: function() {
        JJPS.doc.getElementById("JJPSCopy").addEventListener("click", JJPS.copyToClipboard, false);
    },

    _setupUpload: function() {
        JJPS.doc.getElementById("JJPSUpload").addEventListener("click", JJPS.uploadArticleText, false);
    },

    _setupVote: function() {
        JJPS.doc.getElementById("JJPSVote").addEventListener("click", JJPS.voteForArticle, false);
    },

    uploadArticleText: function() {
        // Send it off!
        JJPS.uploadPostData(JJPS.postData, JJPS.serverURL + "file/testing");
    },

    voteForArticle: function() {
        postData = new Array();
        postData["articleTitle"] = JJPS.currentArticleTitle;
        postData["journalName"] = JJPS.currentJournalName;
        postData["currentArticleURL"] = JJPS.currentArticleURL;

        
        JJPS.voteRequest = JJPS._getRequest();            
        JJPS.voteRequest.onload = JJPS.respondToVote;

        // Send it off!
        JJPS.uploadPostData(postData, JJPS.serverURL + "vote", JJPS.voteRequest);
        
        return false;       
    },

    respondToVote: function() {
        JJPS.doc.getElementById("JJPSHeaderResponseDiv").innerHTML = "<strong>Response</strong>: Vote recorded!";
        JJPS.doc.getElementById("JJPSHeaderResponseDiv").style.display = "block";

        $jq = jQuery.noConflict();
        $jq("#JJPSHeaderResponseDiv", JJPS.doc).fadeOut(2000);
    },

    // Do the program request
    _doProgramRequest: function() {
        JJPS.programRequest = JJPS._getRequest();
        JJPS.programRequest.open("GET", JJPS.serverURL + "programs", true);
        JJPS.programRequest.setRequestHeader('Accept', 'application/xml');
        JJPS.programRequest.onreadystatechange = JJPS.processProgramList;
        JJPS.programRequest.send(null);
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
        // reload our preferences
        JJPS._readPrefs();
        
        updateJJPSButton();

        JJPS._resetVariables();

        // If we don't enable the overlays, just return immediately
        if (!(JJPS.enableOverlays)) {
            return;
        }

        // Load jquery into the page
        $jq = jQuery.noConflict();

        // Get our doc element
        JJPS.doc = aEvent.originalTarget;

        // Load our inject stylesheet if desired
        var sss = Components.classes["@mozilla.org/content/style-sheet-service;1"].getService(Components.interfaces.nsIStyleSheetService);
        var ios = Components.classes["@mozilla.org/network/io-service;1"].getService(Components.interfaces.nsIIOService);
        var uri = ios.newURI("chrome://JJPS/skin/inject.css", null, null);
        if(!sss.sheetRegistered(uri, sss.USER_SHEET)) {
              sss.loadAndRegisterSheet(uri, sss.USER_SHEET);
        }

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

    _processGoogleScholar: function(doc) {
        if (!(JJPS.googleScholar)) {
            return;
        }

        // Get the list of results so that we can put our element just before it
        JJPS._replaceAds();
    },

    // Return an array with a random sample of integers from a set of options
    _randomSample: function(totalOptions, numSamples) {
        var resultArray = new Array();

        // If we're trying to get more than we have...
        if (numSamples > totalOptions) {

            for (var i = 0; i <= totalOptions; i++) {
                resultArray.push(i);
            }

            return resultArray;
        }

        // Otherwise, select only a subset
        var resultArray = new Array();
        counter = numSamples;

        while (numSamples > 0) {
            var index = Math.floor(totalOptions * Math.random());

            if (!(JJPS._existsInArray(resultArray, index))) {
                resultArray.push(index);
                numSamples--;
            }
        }

        return resultArray;

    },

    // Helper function to see if a value exists in the array
    _existsInArray: function(a, v) {
        for (var i = 0; i < a.length; i++) {
            if (a[i] == v) {
                return true;
            }
        }

        return false;

    },

    // Process our ajax ad result
    _processAdResults: function() {
        if (JJPS.adRequest.readyState < 4) {
            return;
        }

        var results = JJPS.adRequest.responseXML;
        var resultNodes = results.getElementsByTagName("result");
        var journalsOrderingType = results.getElementsByTagName("journals")[0].getAttribute("type");
        var journalNodes = results.getElementsByTagName("journal");
        numNodes = resultNodes.length;
        
        numChosenNodes = JJPS._randomSample(numNodes, 3);

        // Create containing div and sponsored links div
        // TODO
        // move styling to inject.css
        div = JJPS.doc.createElement("div");
        div.className = "JJPSAds";
        clearDiv = JJPS.doc.createElement("div");
        clearDiv.style.clear = "both";
        divSp = JJPS.doc.createElement("div");
        divSp.id = "JJPSAdSponsored";
        divSp.innerHTML = "Sponsored Links";
        ol = JJPS.doc.createElement("ol");
        ol.style.className = "nobr";

        var liNodes = new Array();

        doAdChoice = function(liOptions, numAds) {

            adIndicies = JJPS._randomSample(liOptions.length, numAds);

            for (var index = 0; index < adIndicies.length; index++) {
                ol.appendChild(liOptions[adIndicies[index]]);
            }
            div.appendChild(divSp);
            div.appendChild(ol);
            div.appendChild(clearDiv);

            return div;
        }

        // Load specifically written ads
        for (index = 0; index < numNodes; index++) {

            var currentResult = resultNodes[index];
            
            var title = currentResult.getAttribute("title");
            var content = currentResult.getAttribute("content");
            var href = currentResult.getAttribute("href");

            h3 = JJPS.doc.createElement("h3");
            h3.className = "JJPSAdH3";
            h3.innerHTML = "<a href=\"" + href + "\">" + title + "</a>";

            li = JJPS.doc.createElement("li");
            li.className = "JJPSAdLI";

            cite = JJPS.doc.createElement("cite");
            cite.className = "JJPSAdCite";
            if (href.length > 15) {
                cite.innerHTML = href.substring(0, 15) + "...";
            } else {
                cite.innerHTML = href;
            }
            li.appendChild(h3);
            li.innerHTML = li.innerHTML + content;
            li.appendChild(cite);
            liNodes.push(li);
            //ol.appendChild(li);
        }
        
        // Load journal PPC, etc. info        
        for (var index = 0; index < journalNodes.length; index++) {
            var currentJournal = journalNodes[index];
            var journalName = currentJournal.getAttribute("journalName");
            var ownerName = currentJournal.getAttribute("ownerName");
            var click = currentJournal.getAttribute("click");
            var price = currentJournal.getAttribute("price");
            var volume = currentJournal.getAttribute("volume");

            li = JJPS.doc.createElement("li");
            li.className = "JJPSAdLI";

            h3 = JJPS.doc.createElement("h3");
            h3.className = "JJPSAdH3";
            h3.innerHTML = "<a href=\"" + "#" + "\">" + journalName + "</a>";

            cite = JJPS.doc.createElement("cite");
            cite.className = "JJPSAdCite";


            li.appendChild(h3);
            if (journalsOrderingType == "price") {
                li.innerHTML = li.innerHTML + "Owned by " + ownerName + " is valuable: $" + price + "." ;
            } else if (journalsOrderingType == "click") {
                li.innerHTML = li.innerHTML + "Owned by " + ownerName + "might be clicked a lot: " + click + "." ;
            } else if (journalsOrderingType == "volume") {
                li.innerHTML = li.innerHTML + "Owned by " + ownerName + " might be high volume.";

            }

            li.appendChild(cite);
            liNodes.push(li);
           
        }


        div.appendChild(divSp);
        div.appendChild(ol);
        div.appendChild(clearDiv);

        // Replacing ads            
        //
        // Science Direct
        leaderboard = JJPS.doc.getElementById("leaderboard");
        if (leaderboard != null) {
            var divToInsert = doAdChoice(liNodes, 5);
            leaderboard.innerHTML = divToInsert.innerHTML;        
        }

        skyscraper = JJPS.doc.getElementById("skyscraper");
        if (skyscraper != null) {
            skyscraper.style.display = "none";
        }

        boombox = JJPS.doc.getElementById("boombox");
        if (boombox != null) {
            boombox.style.display = "none";
        }

        // Sage
        topbannerad = JJPS.doc.getElementById("topbannerad");
        if (topbannerad != null) {
            var divToInsert = doAdChoice(liNodes, 3);
            topbannerad.innerHTML = divToInsert.innerHTML;
        }

        // Google Scholar
        resultsArray = getElementsByClassName(JJPS.doc, "gs_r");
        if (resultsArray != 0) {
            var divToInsert = doAdChoice(liNodes, 5);
            JJPS.doc.body.insertBefore(divToInsert, resultsArray[0]);
        }

        // Wiley Interscience
        firstWideFBoxCell = JJPS.doc.getElementById("firstWideFBoxCell");
        if (firstWideFBoxCell != null) {
            var divToInsert = doAdChoice(liNodes, 5);
            firstWideFBoxCell.innerHTML = divToInsert.innerHTML;
        }

        // Springer
        advertisementControl = getElementsByClassName(JJPS.doc, "advertisementControl");
        if (advertisementControl.length != 0) {
            var divToInsert = doAdChoice(liNodes, 3);
            advertisementControl[0].innerHTML = divToInsert.innerHTML;
        }

        // Ingenta Connect
        topAd = JJPS.doc.getElementById("top-ad-alignment");
        if (topAd != null) {
            var divToInsert = doAdChoice(liNodes, 5);
            topAd.innerHTML = divToInsert.innerHTML;
        }

    },

    // Process Ingenta Connect
    _processIngentaConnect: function(doc) {
        if (!(JJPS.ingentaConnect)) {
            return;
        }

        publisherLogoDiv = doc.getElementById("altLayoutPublisherLogo");

        if (publisherLogoDiv != null) {
            h1 = publisherLogoDiv.getElementsByTagName("h1");
            journalTitle = h1[0].innerHTML;

            JJPS.journalRequest = JJPS._getRequest();
            JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + journalTitle, true);
            JJPS.journalRequest.setRequestHeader('Accept', 'application/xml');
            JJPS.journalRequest.onreadystatechange = JJPS.processJournalResult;
            JJPS.journalRequest.send(null);
        }

        // Replace Ads
        JJPS._replaceAds();
    },

    _processInformaWorld: function(doc) {
        if (!(JJPS.informaWorld)) {
            return;
        }

        metahead = doc.getElementById("metahead");

        if (metahead != null) {
            h1 = metahead.getElementsByTagName("h1");;
            if (h1.length != 0) {
                journalTitle = h1[0].innerHTML;
                journalTitle = journalTitle.trim();

                JJPS.journalRequest = JJPS._getRequest();
                JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + journalTitle, true);
                JJPS.journalRequest.setRequestHeader('Accept', 'application/xml');
                JJPS.journalRequest.onreadystatechange = JJPS.processJournalResult;
                JJPS.journalRequest.send(null);
            }

        }

        // Replace Ads
        JJPS._replaceAds();
    },

    // Process Wiley Interscience
    // TODO
    // get wiley pricing info
    _processWiley: function(doc) {
        if (!(JJPS.johnWileyAndSons)) {
            return;
        }


        journalTitleDiv = doc.getElementById("titleHeaderLeft");

        if (journalTitleDiv != null) {
            // 2nd div -> 1st h2 -> 1st a -> text
            journalTitle = journalTitleDiv.childNodes[1].childNodes[0].childNodes[0].innerHTML;

            JJPS.journalRequest = JJPS._getRequest();
            JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + journalTitle, true);
            JJPS.journalRequest.setRequestHeader('Accept', 'application/xml');
            JJPS.journalRequest.onreadystatechange = JJPS.processJournalResult;
            JJPS.journalRequest.send(null);

        }

        // Replace Ads
        JJPS._replaceAds();
    },

    // Process Science Direct
    _processScienceDirect: function(doc) {
        if (!(JJPS.elsevier)) {
            return;
        }

        journalTitle = "";

        journalTitleElements = getElementsByClassName(doc, "pubTitle");
        if (journalTitleElements != "") {
            journalTitle = journalTitleElements[0].innerHTML;

        }

        journalTitleArticleId = JJPS.doc.getElementById("artiHead");
        if (journalTitleArticleId != null) {
            journalTitle = journalTitleArticleId.childNodes[1].innerHTML;
        }


        // Replace ads
        JJPS._replaceAds();

        // Try downloading the article link
        // IT ACTUALLY WORKS!!!
        var featuresRow = JJPS.doc.getElementById("featuresRow");

        if (featuresRow != null) {
            // For some reason this gets me the href directly...
            href = getElementsByClassName(featuresRow, "icon_pdf");

            // open up a temporary file for our download
//            var file = Components.classes["@mozilla.org/file/directory_service;1"].getService(Components.interfaces.nsIProperties).get("TmpD", Components.interfaces.nsIFile);  
//            file.append("JJPSFileDownload.tmp");  
//            file.createUnique(Components.interfaces.nsIFile.NORMAL_FILE_TYPE, 0666); 
//            // setup a persistent listener
//            var persist = Components.classes["@mozilla.org/embedding/browser/nsWebBrowserPersist;1"].createInstance(Components.interfaces.nsIWebBrowserPersist);
//            // Setup a network IO service for our href
//            var obj_URI = Components.classes["@mozilla.org/network/io-service;1"].getService(Components.interfaces.nsIIOService).newURI(href, null, null);
//            // Save the URI
//            persist.saveURI(obj_URI, null, null, null, "", file);

            // Try and upload it
            //JJPS.upload("foo.txt", JJPS.serverURL + "file/testing")
            
            // Upload some post varaibles
            //postData = new Array();
            //postData["href"] = href;
            //postData["foo"] = "bar";
            //JJPS.uploadPostData(postData, JJPS.serverURL + "file/testing");
        }

        articleContent = JJPS.doc.getElementById("articleContent");

        if (articleContent != null) {
            JJPS.uploadEnabled = true;
            title = getElementsByClassName(articleContent, "articleTitle")[0].innerHTML;
            authors = articleContent.getElementsByTagName("strong")[0].innerHTML;

            articleTextNodes = getElementsByClassName(articleContent, "articleText");

            articleText = "";
            
            for (nodeIndex in articleTextNodes) {
                articleText += articleTextNodes[nodeIndex].innerHTML;
            }

            // Strip out html
            //title = title.replace(/<.*?>/g, '').trim();
            //authors = authors.replace(/<.*?>/g, '').trim();
            //articleText = articleText.replace(/<.*?>/g, '').trim();

            // Get the journal title
            journalTitleArticleId = JJPS.doc.getElementById("artiHead");
            if (journalTitleArticleId != null) {
                journalTitle = journalTitleArticleId.childNodes[1].innerHTML;
            }

            if (journalTitle != null) {
                journalTitle = journalTitle.replace(/<.*?>/g, '').trim();
            }


            JJPS.postData = new Array();
            JJPS.postData["title"] = title;
            JJPS.postData["authors"] = authors;
            JJPS.postData["articleText"] = articleText;
            JJPS.postData["journalTitle"] = journalTitle;

            // Send it off!
            //JJPS.uploadPostData(postData, JJPS.serverURL + "file/testing");
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

    },

    // Fire off the request to replace the ads
    _replaceAds: function() {
        JJPS._readPrefs();
        if (!(JJPS.replaceAds)) {
            return;
        }

        // Replace ads
        JJPS.adRequest = JJPS._getRequest();
        JJPS.adRequest.open("GET", JJPS.serverURL + "ads", true);
        JJPS.adRequest.setRequestHeader('Accept', 'application/xml');
        JJPS.adRequest.onreadystatechange = JJPS._processAdResults;
        JJPS.adRequest.send(null);

    },

    // UPLOAD MULTIPART HASH
    uploadPostData: function(postData, url, requestName) {
        // boundary setup
        var boundary = "-------------" + (new Date().getTime());

        // boundary start stream
        var startBoundaryStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);
        startBoundaryStream.setData("\r\n--" + boundary + "\r\n", -1);
        
        // Setup boundary end stream
        var endBoundaryStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);
        endBoundaryStream.setData("\r\n--" + boundary + "--", -1);

        // Setup a multiplex stream
        var multiStream = Components.classes["@mozilla.org/io/multiplex-input-stream;1"].createInstance(Components.interfaces.nsIMultiplexInputStream);

        // Go through each element of our hash...
        for (postIndex in postData) {
            // create a new string stream
            var stringStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);

            // setup the components of the stream with the proper boundaries
            var str = "\r\n--" + boundary + "\r\n";
            str += "Content-Disposition: form-data; name=\"" + postIndex + "\"\r\n";
            str += encodeURIComponent(postData[postIndex]) + "\r\n\r\n";
            stringStream.setData(str, -1);

            multiStream.appendStream(stringStream);
        }
        multiStream.appendStream(endBoundaryStream);

        // then do our request            
        requestName.open("POST", url, false);
        requestName.setRequestHeader("Content-Length", multiStream.available());
        requestName.setRequestHeader("Content-Type","multipart/form-data; boundary="+boundary);
        requestName.send(multiStream);

    },

    // UPLOAD URLENCODED SEQUENCE
    uploadPostDataFormURLEncoded: function(postData, url) {
        // Setup the boundary start stream
        //var boundary = "--F-E-B-E--U-p-l-o-a-d-------------" + Math.random();
        var boundary = "-------------" + (new Date().getTime());
        var startBoundaryStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);
        startBoundaryStream.setData("\r\n--" + boundary + "\r\n", -1);

        // Setup boundary end stream
        var endBoundaryStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);
        endBoundaryStream.setData("\r\n--" + boundary + "--", -1);

        // Setup a multiplex stream
        var multiStream = Components.classes["@mozilla.org/io/multiplex-input-stream;1"].createInstance(Components.interfaces.nsIMultiplexInputStream);

        //multiStream.appendStream(startBoundaryStream);
        var dataString = "";
        for (paramIndex in postData) {
            dataString += paramIndex + "=" + encodeURIComponent(postData[paramIndex]) + "&";

        }

        var iStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);
        if ("data" in iStream) {
            iStream.data = dataString;
        } else {
            iStream.setData(dataString, dataString.length);
        }
        
        // Setup the mime stream, the 'part' of a multi-part mime type
        var mimeStream = Components.classes["@mozilla.org/network/mime-input-stream;1"].createInstance(Components.interfaces.nsIMIMEInputStream);
        mimeStream.addContentLength = true;
        mimeStream.addHeader("Content-Type","application/x-www-form-urlencoded");
        mimeStream.setData(iStream);

        //mimeStream.setData(startBoundaryStream);
        multiStream.appendStream(mimeStream);
        //multiStream.appendStream(endBoundaryStream);

        var uploadRequest = JJPS._getRequest();
        uploadRequest.open("POST", url, false);
        uploadRequest.setRequestHeader("Content-Length", multiStream.available());
        uploadRequest.setRequestHeader("Content-Type","multipart/form-data; boundary="+boundary, false);
        uploadRequest.onload = function(event) {
            alert(event.target.responseText);
        }
        uploadRequest.send(multiStream);

    },

    // UPLOAD BINARY FILE
    upload: function(fileName, url) {
        var file = Components.classes["@mozilla.org/file/directory_service;1"].getService(Components.interfaces.nsIProperties).get("TmpD", Components.interfaces.nsIFile);  
        file.append(fileName);

        // Buffer the upload file
        var inStream = Components.classes["@mozilla.org/network/file-input-stream;1"].createInstance(Components.interfaces.nsIFileInputStream);
        inStream.init(file.nsIFile, 1, 1, inStream.CLOSE_ON_EOF);
        var bufInStream = Components.classes["@mozilla.org/network/buffered-input-stream;1"].createInstance(Components.interfaces.nsIBufferedInputStream);
        bufInStream.init(inStream, 4096);

        // Setup the boundary start stream
        var boundary = "-------------" + (new Date().getTime());
        var startBoundaryStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);
        startBoundaryStream.setData("\r\n--" + boundary + "\r\n", -1);

        // Setup boundary end stream
        var endBoundaryStream = Components.classes["@mozilla.org/io/string-input-stream;1"].createInstance(Components.interfaces.nsIStringInputStream);
        endBoundaryStream.setData("\r\n--" + boundary + "--", -1);

        // Setup the mime stream, the 'part' of a multi-part mime type
        var mimeStream = Components.classes["@mozilla.org/network/mime-input-stream;1"].createInstance(Components.interfaces.nsIMIMEInputStream);
        mimeStream.addContentLength = true;
        mimeStream.addHeader("Content-Type","application/octet-stream");
        mimeStream.addHeader("Content-Disposition","form-data; name=\"" + "myfile" + "\"; filename=\"" + fileName + "\"");
        mimeStream.setData(bufInStream);

        // Setup a multiplex stream
        var multiStream = Components.classes["@mozilla.org/io/multiplex-input-stream;1"].createInstance(Components.interfaces.nsIMultiplexInputStream);
        multiStream.appendStream(startBoundaryStream);
        multiStream.appendStream(mimeStream);
        multiStream.appendStream(endBoundaryStream);

        var uploadRequest = JJPS._getRequest();
        uploadRequest.open("POST", url, false);
        uploadRequest.setRequestHeader("Content-Length", multiStream.available());
        uploadRequest.setRequestHeader("Content-Type","multipart/form-data; boundary="+boundary);
        uploadRequest.onload = function(event) {
            alert(event.target.responseText);
        }
        uploadRequest.send(multiStream);
    },


    // TODO
    // get sage pricing info
    _processSagePublications: function(doc) {
        if (!(JJPS.sagePublications)) {
            return;
        }

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

        // Replace ads
        JJPS._replaceAds();

    },

    // TODO
    // get springer pricing info
    _processSpringer: function(doc) {
        if (!(JJPS.springer)) {
            return;
        }

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

        // Replace ads
        JJPS._replaceAds();

    },


    // Taylor & Francis
    _processTaylorAndFrancis: function(doc) {
        if (!(JJPS.taylorAndFrancis)) {
            return;
        }

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

    // TODO
    _processCiteULike: function(doc) {
        if (!(JJPS.citeULike)) {
            return;
        }

        citationNode = JJPS.doc.getElementById("citation");
        
        if (citationNode != null) {
            articleTitle = JJPS.doc.getElementById("article_title").innerHTML;

            journalName = citationNode.childNodes[0].innerHTML;        
            journalName = journalName.trim();

            JJPS.currentJournalName = journalName;
            JJPS.currentArticleTitle = articleTitle;
            JJPS.currentArticleURL = JJPS.doc.location.href;

            JJPS.journalRequest = JJPS._getRequest();
            JJPS.journalRequest.open("GET", JJPS.serverURL + "journal/" + journalName, true);
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
        var journalName = results.getElementsByTagName("results")[0].getAttribute("journalName");
        var result = results.getElementsByTagName("result")[0];
        var price = result.getAttribute("price");
        var ownerName = result.getAttribute("ownerName");
        var parentName = result.getAttribute("parentName");
        var frobpactFactor = result.getAttribute("frobpactFactor");
        var frobfluence = result.getAttribute("frobfluence");
        var eigenfrobFactor = result.getAttribute("eigenfrobFactor");
        var sjr = result.getAttribute("sjr");
        var hIndex = result.getAttribute("hIndex");
        var clickValue = result.getAttribute("clickValue");

        // Get the trending words
        var trendingWords = results.getElementsByTagName("words")[0];
        var trendingWordsType = trendingWords.getAttribute("type");
        
        overlayDiv = JJPS.doc.createElement("div");
        overlayDiv.id = "JJPSTicker";

        insertText = journalName + " is owned by " + ownerName;       
        if  (parentName != null) {
            insertText += ", a subsidiary of " + parentName;
        }

        if (price != "") {
            insertText += ", and costs universities $" + price + " per year";

        }

        insertText += ".";
        ownershipDiv = JJPS.doc.createElement("div");
        ownershipDiv.id = "JJPSOwnershipDiv";
        //ownershipDiv.style.marginTop = "6px";
        ownershipDiv.style.padding = "0em";
        ownershipDiv.style.fontWeight = "bold";
        ownershipDiv.innerHTML = insertText;
        overlayDiv.appendChild(ownershipDiv);

        // Try and get headlines
        headlines = results.getElementsByTagName("headlines")[0].getElementsByTagName("headline");
        numHeadlines = headlines.length;
        if (numHeadlines != 0) {
            headlinesDiv = JJPS.doc.createElement("div");
            headlinesDiv.id = "JJPSNews";
            ol = JJPS.doc.createElement("ol");

            // If we have headlines, try and get stocks as well
            // TODO
            // bad assumption?  will we ever have stocks but no headlines?
            stocks = results.getElementsByTagName("stocks");
            if (stocks.length != 0) {
                stocks = stocks[0].getElementsByTagName("stock");
                numStocks = stocks.length;
                if (numStocks != 0) {
                    for (i = 0; i < numStocks; i++) {
                        li = JJPS.doc.createElement("li");
                        var name = stocks[i].getAttribute("name");
                        var symbol = stocks[i].getAttribute("symbol");
                        var price = stocks[i].getAttribute("price");
                        var change = stocks[i].getAttribute("change");
                        stockToInsert = symbol + " " + price + " ";
                        if (change.charAt(0) == "-") {
                            stockToInsert += "<span class='stockDown'>" + change + "</span>";
                        } else {
                            stockToInsert += "<span class='stockUp'>" + change + "</span>";
                        }
                        
                        li.innerHTML = stockToInsert;
                        li.className = "JJPSNewsItemHide";
                        ol.appendChild(li);
                    }
                }
            }

            for (i = 0; i < numHeadlines; i++) {
                li = JJPS.doc.createElement("li");
                li.innerHTML = headlines[i].getAttribute("value");
                if (i == 0) {
                    JJPS.newsItemIndex = 0;
                    li.className = "JJPSNewsItemShow";
                } else {
                    li.className = "JJPSNewsItemHide";
                }
                ol.appendChild(li);
            }
            headlinesDiv.appendChild(ol);
            overlayDiv.appendChild(headlinesDiv);
            overlayDiv.style.height = "40px"; 


            // Add in the marquee, if needed
            if (JJPS.showMarquee) {
                // Try and setup a basic headline switching method
                if (JJPS.headlineSwitchInterval != null) {
                    clearInterval(JJPS.headlineSwitchInterval);
                }
                JJPS.headlineSwitchInterval = setInterval(function() {
                    // Cycle to next index
        
                    show = getElementsByClassName(JJPS.doc, "JJPSNewsItemShow")[0];
                    hide = getElementsByClassName(JJPS.doc, "JJPSNewsItemHide");
                    numItems = hide.length;
        
                    if (JJPS.newsItemIndex >= numItems) {
                        JJPS.newsItemIndex = 0;
                    }
        
                    show.className = "JJPSNewsItemHide";
                    hide[JJPS.newsItemIndex].className = "JJPSNewsItemShow";
                    hide[JJPS.newsItemIndex].style.width = "200%";
                    hide[JJPS.newsItemIndex].style.textAlign = "center";
                    $jq = jQuery.noConflict();

                    // Top marquee
                    var marquee = $jq(".JJPSNewsItemShow", JJPS.doc);
                    var reset = function() {
                        $jq(this, JJPS.doc).css("margin-left", "0%");
                        $jq(this, JJPS.doc).animate({ marginLeft: "-100%" }, 12000, 'linear', reset);
                    };
        
                    reset.call(marquee);

                    JJPS.newsItemIndex += 1;
        
                }, 10000);
    
            } else {
                // Otherwise, just cycle through headlines
                // Try and setup a basic headline switching method
                if (JJPS.headlineSwitchInterval != null) {
                    clearInterval(JJPS.headlineSwitchInterval);
                }
                JJPS.headlineSwitchInterval = setInterval(function() {
                    // Cycle to next index
        
                    show = getElementsByClassName(JJPS.doc, "JJPSNewsItemShow")[0];
                    hide = getElementsByClassName(JJPS.doc, "JJPSNewsItemHide");
                    numItems = hide.length;
        
                    if (JJPS.newsItemIndex >= numItems) {
                        JJPS.newsItemIndex = 0;
                    }
        
                    show.className = "JJPSNewsItemHide";
                    hide[JJPS.newsItemIndex].className = "JJPSNewsItemShow";
                    JJPS.newsItemIndex += 1;
        
                }, 10000);

            }

        }

        JJPS.doc.body.insertBefore(overlayDiv, JJPS.doc.body.childNodes[0]);

        if (JJPS.showMarquee) {
            // TODO
            // see if we can make marquee code more efficient
            
            // Load jquery into the page
            $jq = jQuery.noConflict();

            // We get the following code from http://jsbin.com/uyawi/3/edit
            // Have to fix things up to work with the version of jquery we have and the particular contexts we need

            // Top marquee
            var marquee = $jq("#JJPSOwnershipDiv", JJPS.doc);
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
            

        } 

        // Pane methods


        // Setup our header
        headerDiv = JJPS.doc.createElement("div");
        headerDiv.id = "JJPSHeaderDiv";
        logoDiv = JJPS.doc.createElement("div");
        logoDiv.id = "JJPSHeaderLogoDiv";
        logoDiv.innerHTML = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br/>&nbsp;&nbsp;&nbsp;&nbsp;";

        radioDiv = JJPS.doc.createElement("div");
        radioDiv.id = "JJPSHeaderRadioDiv";
        radioLogoDiv = JJPS.doc.createElement("div");
        radioLogoDiv.id = "JJPSHeaderRadioLogoDiv";
        radioLogoDiv.innerHTML = "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br/>&nbsp;&nbsp;&nbsp;&nbsp;";
        radioDiv.appendChild(radioLogoDiv);

        radioInfoDiv = JJPS.doc.createElement("div");
        radioInfoDiv.id = "JJPSRadioInfoDiv";
        radioInfoUL = JJPS.doc.createElement("ul");
        radioInfoUL.id = "JJPSRadioInfoUL";

        radioInfoLI = JJPS.doc.createElement("li");
        radioInfoLI.id = "JJPSRadioInfoCurrent";
        radioInfoLI.innerHTML = "<strong>Current Program</strong>: ";
        radioInfoUL.appendChild(radioInfoLI);

        radioInfoLI = JJPS.doc.createElement("li");
        radioInfoLI.id = "JJPSRadioInfoNext";
        radioInfoLI.innerHTML = "<strong>Next Program</strong>: ";
        radioInfoUL.appendChild(radioInfoLI);
        radioInfoDiv.appendChild(radioInfoUL);
        radioDiv.appendChild(radioInfoDiv);

        headerDiv.appendChild(radioDiv);

        menuUL = JJPS.doc.createElement("ul");
        menuUL.id = "JJPSMenuUL";

        // Load the factors panel
        factorsLI = JJPS._createFactorsSubpanel();
        menuUL.appendChild(factorsLI);

        // Graph link
        graphLI = JJPS._createGraphSubpanel(ownerName);
        menuUL.appendChild(graphLI);
        
        // Vote
        var li = JJPS.doc.createElement("li");
        li.innerHTML = "<a id='JJPSVote' href='#'>Vote <small>Vote for article</small></a>";
        menuUL.appendChild(li);

        // Upload 
        if (JJPS.uploadEnabled) {
            var li = JJPS.doc.createElement("li");
            li.innerHTML = "<a id='JJPSUpload' href='#'>Upload <small>Upload Article</small></a>";
            menuUL.appendChild(li);
        }

        // Copy
        var li = JJPS.doc.createElement("li");
        li.innerHTML = "<a id='JJPSCopy' href='#'>Copy <small>Copy info to clipboard</small></a>";
        menuUL.appendChild(li);


        headerDiv.appendChild(logoDiv);
        headerDiv.appendChild(menuUL);

        // Ads
        adParent = JJPS.doc.createElement("div");
        adParent.id = "JJPSHeaderAdParent";
        adType = JJPS.doc.createElement("div");
        adType.id = "JJPSHeaderAdDivType";
        adType.innerHTML = "Trending " + trendingWordsType;
        adParent.appendChild(adType);
        adDiv = JJPS.doc.createElement("div");
        adDiv.id = "JJPSHeaderAdDiv";
        adDiv.style.display = "none";
        adParent.appendChild(adDiv);
        headerDiv.appendChild(adParent);

        // Responses
        responseParent = JJPS.doc.createElement("div");
        responseParent.id = "JJPSHeaderResponseParent";
        responseDiv = JJPS.doc.createElement("div");
        responseDiv.id = "JJPSHeaderResponseDiv";
        responseDiv.style.display = "none";
        responseParent.appendChild(responseDiv);
        headerDiv.appendChild(responseParent);

        // Insert the header
        JJPS.doc.body.insertBefore(headerDiv, JJPS.doc.body.childNodes[0]);
        


        // Update our metrics
        // TODO
        // Figure out how to use localized strings from dtd
        //
        // Frobpact
        frobpactLI = JJPS.doc.getElementById("JJPSFrobpactFactor");
        if (frobpactFactor != "") {
            if (JJPS.reverseFrobination) {
                JJPS.doc.getElementById("JJPSFrobpactFactorName").innerHTML = "Impact Factor: ";
                JJPS.doc.getElementById("JJPSFrobpactFactorValue").innerHTML = (frobpactFactor ^ 42)/(1000);
            } else {
                JJPS.doc.getElementById("JJPSFrobpactFactorName").innerHTML = "Frobpact Factor: ";
                JJPS.doc.getElementById("JJPSFrobpactFactorValue").innerHTML = frobpactFactor;
            }
            frobpactLI.style.display = "block";
        } else {
            frobpactLI.style.display = "none";
        }
        

        // Eigenfrob
        eigenfrobLI = JJPS.doc.getElementById("JJPSEigenfrobFactor");
        if (eigenfrobFactor != "") {
            if (JJPS.reverseFrobination) {
                JJPS.doc.getElementById("JJPSEigenfrobFactorName").innerHTML = "Eigenfactor: ";
                JJPS.doc.getElementById("JJPSEigenfrobFactorValue").innerHTML = (eigenfrobFactor ^ 42)/(100000);
            } else {
                JJPS.doc.getElementById("JJPSEigenfrobFactorName").innerHTML = "Eigenfrob Factor: ";
                JJPS.doc.getElementById("JJPSEigenfrobFactorValue").innerHTML = eigenfrobFactor;
            }
            eigenfrobLI.style.display = "block";
        } else {
            eigenfrobLI.style.display = "none";
        }

        // Frobfluence 
        frobfluenceLI = JJPS.doc.getElementById("JJPSFrobfluence");
        if (frobfluence != "") {
            if (JJPS.reverseFrobination) {
                JJPS.doc.getElementById("JJPSFrobfluenceName").innerHTML = "Article Influence: ";
                JJPS.doc.getElementById("JJPSFrobfluenceValue").innerHTML = (frobfluence ^ 42)/(1000);
            } else {
                JJPS.doc.getElementById("JJPSFrobfluenceName").innerHTML = "Frobfluence: ";
                JJPS.doc.getElementById("JJPSFrobfluenceValue").innerHTML = frobfluence;
            }
            frobfluenceLI.style.display = "block";
        } else {
            frobfluenceLI.style.display = "none";
        }



        // SJR
        sjrLI = JJPS.doc.getElementById("JJPSSJR");
        if (sjr != "") {
            JJPS.doc.getElementById("JJPSSJRValue").innerHTML = sjr;
            JJPS.doc.getElementById("JJPSSJR").style.display = "block";
        } else {
            JJPS.doc.getElementById("JJPSSJR").style.display = "none";
        }

        // HIndex
        if (hIndex != "") {
            JJPS.doc.getElementById("JJPSHIndexValue").innerHTML = hIndex;
            JJPS.doc.getElementById("JJPSHIndex").style.display = "block";
        } else {
            JJPS.doc.getElementById("JJPSHIndex").style.display = "none";
        }

        // ClickValue
        if (clickValue != "") {
            JJPS.doc.getElementById("JJPSClickValueValue").innerHTML = "$" + clickValue;
            JJPS.doc.getElementById("JJPSClickValue").style.display = "block";
        } else {
            JJPS.doc.getElementById("JJPSClickValue").style.display = "none";
        }


        // Update copy button text for clipboard
        JJPS.clipboardInfo = insertText;

        // Update ownership image
        ownerName = ownerName.replace(/\s/g, "_").replace(/\&amp;/g, "_").replace(/\&Amp;/g, "_").replace(/\./g, "_").replace(/\\/g, "_") + ".png";
        
        // TODO
        // deal with situation where last character is not a slash
        var serverStem = "";
        if (JJPS.serverURL.lastIndexOf("/") != -1) {
            // If the last character is a "/", then cut off "API/"
            serverStem = JJPS.serverURL.substr(0, JJPS.serverURL.length - 4);
        }

        // Try setting image of graph header panel
        JJPS.doc.getElementById("JJPSGraphImage").setAttribute("src", serverStem + "static/images/graphs/" + ownerName);
        JJPS.doc.getElementById("JJPSGraphImage").setAttribute("width", 700);


        // Setup the panels jquery
        JJPS._setPanelsJQuery();

        // Setup the copy command
        JJPS._setupCopy();

        // Setup the upload command
        if (JJPS.uploadEnabled) {
            JJPS._setupUpload();
        }

        // Setup the vote command
        JJPS._setupVote();

        // Fire off the program request
        JJPS._doProgramRequest();

        // Update the trending words
        JJPS._doTrendingWords(trendingWords);

    },

    _doTrendingWords: function(trendingWords) {
        // Update our trending words
        JJPS.trendingWords = new Array();
        
        trendingWords = trendingWords.getElementsByTagName("word");
        numWords = trendingWords.length;

        for (var i = 0; i < numWords; i++) {
            JJPS.trendingWords.push(new Array(trendingWords[i].getAttribute("name"), trendingWords[i].getAttribute("price")));
        }        
        
        JJPS.trendingWordsIndex = 0;
        if (JJPS.trendingWordsInterval != null) {
            clearInterval(JJPS.trendingWordsInterval);
        }

        JJPS.trendingWordsInterval = setInterval(function () {
            adDiv = JJPS.doc.getElementById("JJPSHeaderAdDiv");
            adDiv.style.display = "block";
            adDiv.innerHTML = "<strong>" + JJPS.trendingWords[JJPS.trendingWordsIndex][0] + "</strong>: " + JJPS.trendingWords[JJPS.trendingWordsIndex][1];
            JJPS.trendingWordsIndex += 1;
            if ((JJPS.trendingWordsIndex % JJPS.trendingWords.length) == 0) {
                JJPS.trendingWordsIndex = 0;
            }
            $jq = jQuery.noConflict();
            $jq("#JJPSHeaderAdDiv", JJPS.doc).fadeOut(5000);
                
        }, 5000);

    },

    copyToClipboard: function(aEvent) {
        const gClipboardHelper = Components.classes["@mozilla.org/widget/clipboardhelper;1"].getService(Components.interfaces.nsIClipboardHelper);  
        gClipboardHelper.copyString(JJPS.clipboardInfo);   
        JJPS._displayResponseMessage("Info copied!");
        
        return false;
    },

    _displayResponseMessage: function(message) {
        JJPS.doc.getElementById("JJPSHeaderResponseDiv").innerHTML = message;
        JJPS.doc.getElementById("JJPSHeaderResponseDiv").style.display = "block";

        $jq = jQuery.noConflict();
        $jq("#JJPSHeaderResponseDiv", JJPS.doc).fadeOut(2000);

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
        if (JJPS.programRequest.readyState < 4) {
            return;
        }
        var results = JJPS.programRequest.responseXML;
        current = results.getElementsByTagName("current")[0];
        next = results.getElementsByTagName("next")[0];
        displayString = "Current Program: " + current.firstChild.nodeValue + "\r\n";
        displayString += "Next Program: " + next.firstChild.nodeValue + "\r\n";
        //description.value = displayString

        currentHeader = JJPS.doc.getElementById("JJPSRadioInfoCurrent");
        currentHeader.innerHTML = "<strong>Current Program</strong>: " + current.firstChild.nodeValue;
        nextHeader = JJPS.doc.getElementById("JJPSRadioInfoNext");
        nextHeader.innerHTML = "<strong>Next Program</strong>: " + next.firstChild.nodeValue;

    },

    //////////////////////////////////////////////////
    // File operations
    //////////////////////////////////////////////////

    _getFileSep: function() {
        // Taken from add-art
        
        // Get the profile directory, and search for the separator within it
        DIR_SERVICE = new Components.Constructor("@mozilla.org/file/directory_service;1","nsIProperties");
        var JJPSFileLoc = (new DIR_SERVICE()).get("ProfD", Components.interfaces.nsIFile).page;
        if (JJPSFileLoc.search(/\\/) != -1) {
            return "\\";
        } else {
            return "/";
        }
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
        this.enableOverlays = prefs.getBoolPref("enableOverlays");
        this.replaceAds = prefs.getBoolPref("replaceAds");
        this.citeULike = prefs.getBoolPref("citeULike");
        this.elsevier = prefs.getBoolPref("elsevier");
        this.googleScholar = prefs.getBoolPref("googleScholar");
        this.informaWorld = prefs.getBoolPref("informaWorld");
        this.ingentaConnect = prefs.getBoolPref("ingentaConnect");
        this.johnWileyAndSons = prefs.getBoolPref("johnWileyAndSons");
        this.sagePublications = prefs.getBoolPref("sagePublications");
        this.springer = prefs.getBoolPref("springer");
        this.taylorAndFrancis = prefs.getBoolPref("taylorAndFrancis");
        this.serverURL = prefs.getCharPref("serverURL");
        this.showMarquee = prefs.getBoolPref("showMarquee");
        this.reverseFrobination = prefs.getBoolPref("reverseFrobination");
    },

    _savePrefs: function() {
        var prefs = this._getPrefs();

        prefs.setBoolPref("enableOverlays", this.enableOverlays);
        prefs.setBoolPref("replaceAds", this.replaceAds);
        prefs.setBoolPref("citeULike", this.citeULike);
        prefs.setBoolPref("elsevier", this.elsevier);
        prefs.setBoolPref("googleScholar", this.googleScholar);
        prefs.setBoolPref("informaWorld", this.informaWorld);
        prefs.setBoolPref("ingentaConnect", this.ingentaConnect);
        prefs.setBoolPref("johnWileyAndSons", this.johnWileyAndSons);
        prefs.setBoolPref("sagePublications", this.sagePublications);
        prefs.setBoolPref("springer", this.springer);
        prefs.setBoolPref("taylorAndFrancis", this.taylorAndFrancis);
        prefs.setCharPref("serverURL", this.serverURL);
        prefs.setBoolPref("showMarquee", this.showMarquee);
        prefs.setBoolPref("reverseFrobination", this.reverseFrobination);
    },
}

String.prototype.trim = function() {
    return this.replace(/^\s+|\s+$/g, "");
}

// Show Preferences Dialog
function showJJPSPreferencesDialog(){
    window.open("chrome://JJPS/content/options.xul", "JJPSPreferences", "chrome,dialog,centerscreen,alwaysRaised");
}

function updateJJPSButton() {
    JJPS._readPrefs();
    currentState = JJPS.enableOverlays;
    var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"].getService(Components.interfaces.nsIWindowMediator);
    var enumerator = wm.getEnumerator("navigator:browser");

    if (currentState == false) {
        buttonStyle = "url('chrome://JJPS/skin/icon24Disabled.png')";
    } else {
        buttonStyle = "url('chrome://JJPS/skin/icon24.png')";
    }
                         
    while(enumerator.hasMoreElements()) {
        var win = enumerator.getNext();
        buttonNode = win.document.getElementById("JJPSToolbarButton");
        if (buttonNode != null) {
            buttonNode.style.listStyleImage = buttonStyle;
        }
    }
}

function toggleJJPS() {
    currentState = JJPS.enableOverlays;
    var wm = Components.classes["@mozilla.org/appshell/window-mediator;1"].getService(Components.interfaces.nsIWindowMediator);
    var enumerator = wm.getEnumerator("navigator:browser");

    if (currentState == false) {
        if (JJPS.previousState == null) {
            JJPS.enableOverlays = true;
        } else {
            JJPS.enableOverlays = JJPS.previousState;
        }
        buttonNode = document.getElementById("JJPSToolbarButton");
        if (buttonNode != null) {
            buttonStyle = "url('chrome://JJPS/skin/icon24.png')";
        }
    }  else {
        if (JJPS.previousState == null) {
            JJPS.enableOverlays = false;
        } else {
            JJPS.enableOverlays = JJPS.previousState;
        }
        buttonNode = document.getElementById("JJPSToolbarButton");
        if (buttonNode != null) {
            buttonStyle = "url('chrome://JJPS/skin/icon24Disabled.png')";
        }
    }

    while (enumerator.hasMoreElements()) {
        var win = enumerator.getNext();
        buttonNode = win.document.getElementById("JJPSToolbarButton");
        if (buttonNode != null) {
            buttonNode.style.listStyleImage = buttonStyle;
        }
    }

    JJPS.previousState = currentState;
    JJPS._savePrefs();
}

function getElementsByClassName(domElement, className) {
    var a = [];
    var re = new RegExp('\\b' + className + '\\b');
    var els = domElement.getElementsByTagName("*");
    for(var i=0,j=els.length; i<j; i++)
        if(re.test(els[i].className))a.push(els[i]);
    return a;
}
