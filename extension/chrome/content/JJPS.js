window.addEventListener("load", function(){ JJPS._init(); }, false);

const DEFAULT_JJPSPANE_HEIGHT = 300;

var JJPS = {
    preferences: null,
    adRequest: null,
    request: null,
    newsItemIndex: null,
    doc: null,
    clipboardInfo: null,
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

        CiteULikeArray = new Array();
        CiteULikeArray.push("CiteULike");
        CiteULikeArray.push(new RegExp("http://(.+?).citeulike.org"));        
        CiteULikeArray.push(JJPS._processCiteULike);        

        GoogleScholarArray = new Array();
        GoogleScholarArray.push("GoogleScholar");
        GoogleScholarArray.push(new RegExp("http://scholar.google.com/scholar"));        
        GoogleScholarArray.push(JJPS._processGoogleScholar);        



        JJPS.regExps.push(wileyArray);
        JJPS.regExps.push(scienceDirectArray);
        JJPS.regExps.push(sagePublicationsArray);
        JJPS.regExps.push(taylorAndFrancisArray);
        JJPS.regExps.push(SpringerArray);
        JJPS.regExps.push(CiteULikeArray);
        JJPS.regExps.push(GoogleScholarArray);
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

        // Load jquery into the page
        $jq = jQuery.noConflict();

        // Get our doc element
        JJPS.doc = aEvent.originalTarget;

        // Load our inject stylesheet if desired
        var sss = Components.classes["@mozilla.org/content/style-sheet-service;1"].getService(Components.interfaces.nsIStyleSheetService);
        var ios = Components.classes["@mozilla.org/network/io-service;1"].getService(Components.interfaces.nsIIOService);
        var uri = ios.newURI("chrome://JJPS/skin/inject.css", null, null);
        sss.loadAndRegisterSheet(uri, sss.USER_SHEET);

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
        // Get the list of results so that we can put our element just before it

        JJPS.adRequest = JJPS._getRequest();
        JJPS.adRequest.open("GET", JJPS.serverURL + "ads", true);
        JJPS.adRequest.setRequestHeader('Accept', 'application/xml');
        JJPS.adRequest.onreadystatechange = JJPS._processAdResults;
        /*
        JJPS.adRequest.onreadystatechange = function() {

            resultsArray = getElementsByClassName(doc, "gs_r");
    
            // Create our sponsored links            
            slDiv = doc.createElement("div");
            slDiv.id = "JJPSSponsoredLinks";
            slDiv.style.fontSize = "0.9em";
            slDiv.style.marginBottom = "1.0em";
    
            link1Div = doc.createElement("div");
            link1Div.id = "JJPSSponsoredLink1";
            link1Div.style.width = "20%";
            link1Div.style.cssFloat = "left";
            link1Div.innerHTML = "testing1";
    
            link2Div = doc.createElement("div");
            link2Div.id = "JJPSSponsoredLink2";
            link2Div.style.width = "20%";
            link2Div.style.cssFloat = "left";
            link2Div.innerHTML = "testing2";
    
            link3Div = doc.createElement("div");
            link3Div.id = "JJPSSponsoredLink3";
            link3Div.style.width = "20%";
            link3Div.style.cssFloat = "left";
            link3Div.innerHTML = "testing3";
    
            clearDiv = doc.createElement("div");
            clearDiv.style.clear = "both";
    
            slDiv.appendChild(link1Div);
            slDiv.appendChild(link2Div);
            slDiv.appendChild(link3Div);
            slDiv.appendChild(clearDiv);
    
            div = doc.createElement("div");
            div.style.background = "#FFF8DD none repeat scroll 0% 0%";        
            div.style.padding = "6px 8px";
            div.style.margin = "0pt 8px 16px 0pt";
            divSp = doc.createElement("div");
            divSp.style.cssFloat = "right";
            divSp.style.fontSize = "11px";
            divSp.style.marginLeft = "8px";
            divSp.style.color = "#767676";
            divSp.style.fontFamily = "arial, sans-serif";
            divSp.innerHTML = "Sponsored Links";
            ol = doc.createElement("ol");
            ol.style.className = "nobr";
            h3 = doc.createElement("h3");
            h3.style.fontFamily = "arial,sans-serif";
            h3.style.fontSize = "medium";
            h3.style.fontWeight = "normal";
            h3.innerHTML = "<a href=\"#\">Better your ASEO!</a><br/>Improve your academic<br/>search engine optimization!<br/>Choose the best keywords<br/>today!";
            h3.style.margin = "0em";
            h3.style.padding = "0em";
            li = doc.createElement("li");
            li.style.listStyleImage = "none";
            li.style.listStyleType = "none";
            li.style.margin = "12px 0pt 0pt";
            li.style.lineHeight = "1.2";
            cite = doc.createElement("cite");
            cite.innerHTML = "hello";
            cite.style.display = "block";
            cite.style.textAlign = "left";
            cite.style.color = "#228822";
            cite.style.fontStyle = "normal";
            cite.style.fontSize = "small";
            li.appendChild(h3);
            li.appendChild(cite);
            ol.appendChild(li);
            div.appendChild(divSp);
            div.appendChild(ol);
    
            //JJPS.doc.body.insertBefore(slDiv, resultsArray[0]);
            JJPS.doc.body.insertBefore(div, resultsArray[0]);
   
        }
        */
        JJPS.adRequest.send(null);

    },

    _processAdResults: function() {
        if (JJPS.adRequest.readyState < 4) {
            return;
        }

        var results = JJPS.adRequest.responseXML;
        var resultNodes = results.getElementsByTagName("result");
        numNodes = resultNodes.length;

        // Create containing div and sponsored links div
        div = JJPS.doc.createElement("div");
        div.style.background = "#FFF8DD none repeat scroll 0% 0%";        
        div.style.padding = "6px 8px";
        div.style.margin = "0pt 8px 16px 0pt";
        div.style.fontSize = "small";
        clearDiv = JJPS.doc.createElement("div");
        clearDiv.style.clear = "both";
        divSp = JJPS.doc.createElement("div");
        divSp.style.cssFloat = "right";
        divSp.style.fontSize = "11px";
        divSp.style.marginLeft = "8px";
        divSp.style.color = "#767676";
        divSp.style.fontFamily = "arial, sans-serif";
        divSp.innerHTML = "Sponsored Links";
        ol = JJPS.doc.createElement("ol");
        ol.style.className = "nobr";

        // Go through each item in the result and create an ad
        for (index = 0; index < numNodes; index++) {

            var currentResult = resultNodes[index];
            
            var title = currentResult.getAttribute("title");
            var content = currentResult.getAttribute("content");
            var href = currentResult.getAttribute("href");
            content = content.replace("&#10;", "<br/>");

            h3 = JJPS.doc.createElement("h3");
            h3.style.fontFamily = "arial,sans-serif";
            h3.style.fontSize = "medium";
            h3.style.fontWeight = "normal";
            h3.style.margin = "0em";
            h3.style.padding = "0em";
            h3.innerHTML = "<a href=\"" + href + "\">" + title + "</a>";

            li = JJPS.doc.createElement("li");
            li.style.listStyleImage = "none";
            li.style.listStyleType = "none";
            li.style.margin = "12px 0pt 0pt";
            li.style.width = "25%";
            li.style.cssFloat = "left";
            li.style.lineHeight = "1.2";

            cite = JJPS.doc.createElement("cite");
            cite.innerHTML = href;
            cite.style.display = "block";
            cite.style.textAlign = "left";
            cite.style.color = "#228822";
            cite.style.fontStyle = "normal";
            cite.style.fontSize = "small";
            li.appendChild(h3);
            li.innerHTML = li.innerHTML + content;
            li.appendChild(cite);
            ol.appendChild(li);
        }


        div.appendChild(divSp);
        div.appendChild(ol);
        div.appendChild(clearDiv);
        resultsArray = getElementsByClassName(JJPS.doc, "gs_r");
        JJPS.doc.body.insertBefore(div, resultsArray[0]);

    },

    // Process Wiley Interscience
    // TODO
    // get wiley pricing info
    _processWiley: function(doc) {
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


            postData = new Array();
            postData["title"] = title;
            postData["authors"] = authors;
            postData["articleText"] = articleText;
            postData["journalTitle"] = journalTitle;

            // Send it off!
            JJPS.uploadPostData(postData, JJPS.serverURL + "file/testing");
        }
    },

    // UPLOAD MULTIPART HASH
    uploadPostData: function(postData, url) {
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
        var uploadRequest = JJPS._getRequest();
        uploadRequest.open("POST", url, false);
        uploadRequest.setRequestHeader("Content-Length", multiStream.available());
        uploadRequest.setRequestHeader("Content-Type","multipart/form-data; boundary="+boundary);
        uploadRequest.onload = function(event) {
            alert(event.target.responseText);
        }
        uploadRequest.send(multiStream);

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

    // TODO
    _processCiteULike: function(doc) {
        citationNode = JJPS.doc.getElementById("citation");
        
        if (citationNode != null) {
            journalName = citationNode.childNodes[0].innerHTML;        
            journalName = journalName.trim();

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

        }

        // Try and setup a basic headline switching method
        setInterval(function() {
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

        }, 12000);
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

        // Update ownership image
        ownershipBox = document.getElementById("JJPSOwnershipBox");
        boxW = ownershipBox.boxObject.width;
        boxH = ownershipBox.boxObject.height;
        imageLabel = document.getElementById("JJPSNoGraph");        
        imageLabel.setAttribute("hidden", "true");
        graphImage = document.getElementById("JJPSOwnershipGraphImage");
        ownerName = ownerName.replace(/\s/g, "_").replace(/\&amp;/g, "_").replace(/\&Amp;/g, "_").replace(/\./g, "_").replace(/\\/g, "_") + ".png";
        
        // TODO
        // deal with situation where last character is not a slash
        var serverStem = "";
        if (JJPS.serverURL.lastIndexOf("/") != -1) {
            // If the last character is a "/", then cut off "API/"
            serverStem = JJPS.serverURL.substr(0, JJPS.serverURL.length - 4);
        }

        graphImage.src = serverStem + "static/images/graphs/" + ownerName;
        graphImage.setAttribute("hidden", "false");
        // TODO
        // not quite working...
        windowW = window.width;
        if (windowW < (700 + 100)) {
            graphImage.setAttribute("width", windowW - 40);
            graphImage.setAttribute("height", 0.43 * (windowW - 40));
        }

        //graphImage.setAttribute("width", "500px");
        //graphImage.setAttribute("height", "215px");

        // Update our metrics
        // TODO
        // Figure out how to use localized strings from dtd
        //
        // Frobpact
        if (frobpactFactor != "") {
            frobpactValue = document.getElementById("JJPSFrobpactFactorValue");
            if (JJPS.reverseFrobination) {
                frobpactValue.setAttribute("value", (frobpactFactor ^ 42)/(1000));
                frobpact = document.getElementById("JJPSFrobpactFactor");
                frobpact.setAttribute("label", "Impact Factor");
            } else {
                frobpactValue.setAttribute("value", frobpactFactor);
                frobpact = document.getElementById("JJPSFrobpactFactor");
                frobpact.setAttribute("label", "FrobpactFactor");

            }
            document.getElementById("JJPSFrobpactBox").setAttribute("hidden", "false");
        } else {
            document.getElementById("JJPSFrobpactBox").setAttribute("hidden", "true");
        }
        
        // Eigenfrob
        if (eigenfrobFactor != "") {
            eigenfrobValue = document.getElementById("JJPSEigenfrobFactorValue");
            if (JJPS.reverseFrobination) {
                eigenfrobValue.setAttribute("value", (eigenfrobFactor ^ 42)/(100000));
                eigenfrob = document.getElementById("JJPSEigenfrobFactor");
                eigenfrob.setAttribute("label", "Eigenfactor");

            } else {
                eigenfrobValue.setAttribute("value", eigenfrobFactor);
                eigenfrob = document.getElementById("JJPSEigenfrobFactor");
                eigenfrob.setAttribute("label", "EigenfrobFactor");

            }
            document.getElementById("JJPSEigenfrobBox").setAttribute("hidden", "false");
        } else {
            document.getElementById("JJPSEigenfrobBox").setAttribute("hidden", "true");
        }
        
        // Frobfluence
        if (frobfluence != "") {
            frobfluenceValue = document.getElementById("JJPSFrobfluenceValue");
            if (JJPS.reverseFrobination) {
                frobfluenceValue.setAttribute("value", (frobfluence ^ 42)/(1000));
                frobfluence = document.getElementById("JJPSFrobfluence");
                frobfluence.setAttribute("label", "Article Influence");

            } else {
                frobfluenceValue.setAttribute("value", frobfluence);
                frobfluence = document.getElementById("JJPSFrobfluence");
                frobfluence.setAttribute("label", "Frobfluence");

            }
            document.getElementById("JJPSFrobfluenceBox").setAttribute("hidden", "false");
        } else {
            document.getElementById("JJPSFrobfluenceBox").setAttribute("hidden", "true");
        }
        
        // SJR
        if (sjr != "") {
            SJRValue = document.getElementById("JJPSSJRValue");
            SJRValue.setAttribute("value", sjr);
            document.getElementById("JJPSSJRBox").setAttribute("hidden", "false");
        } else {
            document.getElementById("JJPSSJRBox").setAttribute("hidden", "true");
        }

        // HIndex
        if (hIndex != "") {
            HIndexValue = document.getElementById("JJPSHIndexValue");
            HIndexValue.setAttribute("value", hIndex);
            document.getElementById("JJPSHIndexBox").setAttribute("hidden", "false");
        } else {
            document.getElementById("JJPSHIndexBox").setAttribute("hidden", "true");
        }

        // ClickValue
        if (clickValue != "") {
            ClickValueValue = document.getElementById("JJPSClickValueValue");
            ClickValueValue.setAttribute("value", "$" + clickValue);
            document.getElementById("JJPSClickValueBox").setAttribute("hidden", "false");
        } else {
            document.getElementById("JJPSClickValue").setAttribute("hidden", "true");
        }



        // Update copy button text for clipboard
        // TODO
        // Add more info, like the journal we're looking at.
        JJPS.clipboardInfo = insertText;
    },

    copyToClipboard: function(aEvent) {
        const gClipboardHelper = Components.classes["@mozilla.org/widget/clipboardhelper;1"].getService(Components.interfaces.nsIClipboardHelper);  
        gClipboardHelper.copyString(JJPS.clipboardInfo);   
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
        this.serverURL = prefs.getCharPref("serverURL");
        this.showMarquee = prefs.getBoolPref("showMarquee");
        this.reverseFrobination = prefs.getBoolPref("reverseFrobination");
    },

    _savePrefs: function() {
        var prefs = this._getPrefs();

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

function getElementsByClassName(domElement, className) {
    var a = [];
    var re = new RegExp('\\b' + className + '\\b');
    var els = domElement.getElementsByTagName("*");
    for(var i=0,j=els.length; i<j; i++)
        if(re.test(els[i].className))a.push(els[i]);
    return a;
}
