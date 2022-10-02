
searchId = 1;
resultsData = {};

function geocode() {
    // get search input and clear
    input = document.querySelector('input[name="search-input"]');
    search = input.value;
    console.log(search);
    input.value = '';

    // search for name
    apiSearchUrl = 'api/search/name_hierarchy?search='+search;
    fetch(apiSearchUrl).then(result=>result.json()).then(data=>receiveResults(data))
    return false;
}

function receiveResults(data) {
    storeResultData(data);
    autoSelectMatch(searchId);
    addMatchToList(searchId); // only adds an empty item, details will be filled later
    updateListEntry(searchId); // fills in the details from above
    geomMatchId = data['chosen_geom_id'];
    console.log(geomMatchId);
    requestChosenGeomMatch(searchId, geomMatchId);
    updateResultCounts();
    searchId += 1;
}

function updateResultCounts() {
    // get count
    count = Object.keys(resultsData).length;
    // update count elements
    for (elem of document.querySelectorAll('.results-count')) {
        elem.innerText = count;
    };
}

function storeResultData(data) {
    resultsData[searchId] = data;
}

function autoSelectMatch(id) {
    // for a given search id, sets the chosen matches to the data dicts
    autoDisambiguateNames(id);
    autoDisambiguateGeoms(id);
}

function addMatchToList(searchId) {
    // only adds an empty item, details will be filled later
    results = document.getElementById('search-results');

    searchData = resultsData[searchId];
    
    item = document.createElement('div');
    item.id = 'search-id-' + searchId;
    item.className = 'search-item box';
    item.onclick = function(){showListEntry(searchId)};
    results.appendChild(item);
    
    /*
    thumb = document.createElement('img');
    thumb.className = 'search-thumbnail';
    thumb.src = 'https://cdn-icons-png.flaticon.com/512/235/235861.png';
    item.appendChild(thumb);
    */
    
    info = document.createElement('div');
    info.className = 'search-info';
    item.appendChild(info);

    infoQuery = document.createElement('h4');
    infoQuery.className = 'search-info-query';
    infoQuery.innerHTML = `#${searchId}: "${searchData.search}"`;
    infoQuery.innerHTML += `<span class="search-info-ambiguity">${searchData.count}</span>`;
    info.appendChild(infoQuery);

    // below here will be filled later only
    
    infoName = document.createElement('span');
    infoName.className = 'search-info-name';
    infoName.innerText = 'Match: ...';
    info.appendChild(infoName);

    infoSource = document.createElement('span');
    infoSource.className = 'search-info-source';
    infoSource.innerText = 'Source: ' + 'Test Source';
    info.appendChild(infoSource);
    
    infoTime = document.createElement('span');
    infoTime.className = 'search-info-time';
    infoTime.innerText = 'Validity: ' + '...';
    info.appendChild(infoTime);

    // buttons
    buttons = document.createElement('div');
    buttons.className = 'search-item-buttons';
    item.appendChild(buttons);
    buttons.innerHTML = `
        <button type="button" class="small" onclick="openDisambiguationPopup(${searchId})">Edit</button>
    `;

    // remove
    drop = document.createElement('span');
    drop.innerHTML = '&times;';
    drop.className = 'search-item-dropbut';
    drop.onclick = function(){removeGeocode(searchId)};
    item.appendChild(drop);

    //scroll into view
    results.scrollTop = results.scrollHeight;
}

function removeGeocode(searchId) {
    removeMatchFromList(searchId);
    removeResultFromMap(searchId);
    removeFromData(searchId);
}

function removeMatchFromList(searchId) {
    item = document.getElementById('search-id-' + searchId);
    item.remove();
}

function removeFromData(searchId) {
    delete resultsData[searchId];
    updateResultCounts();
}

function getDisplayName(adminData) {
    // construct the display name
    names = [];
    for (parent of adminData.hierarchy) {
        firstName = parent.names[0];
        names.push(firstName);
    };
    displayName = names.join(', ');
    return displayName;
}

function updateListEntry(searchId2) {
    // get the chosen data
    searchResult = resultsData[searchId2];
    chosenMatch = lookupChosenGeomData(searchId2);

    // get the list entry
    item = document.getElementById('search-id-' + searchId2);

    // calc display name and percent match
    chosenMatchDisplayName = getDisplayName(chosenMatch);
    chosenMatchPercent = chosenMatch.simil * 100;

    // set the match name
    infoName = item.querySelector('.search-info-name');
    infoName.innerText = 'Match: ' + chosenMatchDisplayName + ` (${chosenMatchPercent.toFixed(0)}%)`;

    // set the source
    infoSource = item.querySelector('.search-info-source');
    infoSource.innerText = 'Source: ' + chosenMatch.source.name;

    // set temporal validity
    infoSource = item.querySelector('.search-info-time');
    if (chosenMatch.valid_from === null) {
        validity = "Unknown";
    } else {
        validity = chosenMatch.valid_from + ' - ' + chosenMatch.valid_to;
    }
    infoSource.innerText = 'Validity: ' + validity;

    //scroll into view
    //item.scrollIntoView({block:'start', inline:'nearest'});
}

function showListEntry(searchId) {
    // clicking to remove entry also triggers this
    if (document.getElementById('search-id-' + searchId) == null) {
        return;
    };
    // temporarily change to highlight color
    item = document.getElementById('search-id-' + searchId);
    item.className = 'box search-item clicked';
    // switch back to normal (should fade)
    setTimeout(function(){
        item.className = 'box search-item';
    }, 300);
    // zoom map
    zoomMapToSearchId(searchId);
}

function lookupChosenGeomData(searchId2) {
    // get results data for the search id
    data = resultsData[searchId2];

    // loop search results until find chosen
    chosenId = data['chosen_geom_id'];
    for (entry of data.results) {
        if (entry.id == chosenId) {
            return entry;
        };
    };
}

function autoDisambiguateNames(id) {
    // user will likely manually disambiguate the names
    // but this method tries to do this automatically as a first guess

    // get results data for the search id
    data = resultsData[id];

    // the search results are already sorted by text similiraty
    // so for now just choose the first one (most similar)
    chosen = data.results[0];

    // update the results data with the chosen id
    //data['chosen_name_simil'] = chosen.simil;
}

function autoDisambiguateGeoms(id) {
    // user will likely manually disambiguate the geoms
    // but this method tries to do this automatically as a first guess
    // this method is also affected by the chosen name matches which ranks the geoms

    // get results data for the search id
    data = resultsData[id];

    // the search results are already sorted by text similiraty
    // so for now just choose the first geom of the first name (most similar)
    chosen = data.results[0];
    chosenGeomId = chosen.id;

    // update the results data with the chosen id
    data['chosen_geom_id'] = chosenGeomId;
}

function requestChosenGeomMatch(searchId2, adminId) {
    // fetch full details of chosen geom match
    url = '/api/get_admin/' + adminId;
    fetch(url).then(result=>result.json()).then(data=>receiveChosenGeomMatch(searchId2, data));
}

function receiveChosenGeomMatch(searchId2, geomData) {
    console.log(geomData);

    // store received geom data
    searchData = resultsData[searchId2];
    searchData['chosen_geom_data'] = geomData;

    // update table
    updateListEntry(searchId2);

    // add to map
    addResultToMap(searchId2, geomData);
}

function openOptionsPopup() {
    elem = document.getElementById('options-popup').className = 'popup';
}

function exportResults() {
    // create geojson of results
    feats = [];
    for (key of Object.keys(resultsData)) {
        props = resultsData[key].chosen_geom_data;
        featObj = resultLayer.getSource().getFeatureById(key);
        geomObj = featObj.getGeometry();
        geom = {type: geomObj.getType(), coordinates: geomObj.getCoordinates()};
        feat = {type:'Feature', properties:props, geometry:geom};
        feats.push(feat);
    };
    geoj = {type: 'FeatureCollection', features:feats};
    // encode data to link href
    downloadBut = document.getElementById('export-button');
    var dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(geoj));
    downloadBut.href = dataStr;
}

// close popups on clickout

document.onclick = function(event) {
    if (event.target.className == 'popup') {
        event.target.className = 'popup is-hidden';
    };
}
