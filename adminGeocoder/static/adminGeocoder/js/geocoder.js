
searchId = 1;
resultsData = {};

function geocode() {
    // get search input and clear
    input = document.querySelector('input[name="search-input"]');
    search = input.value;
    console.log(search);
    input.value = '';

    // search for name
    apiSearchUrl = 'api/search/name?search='+search;
    fetch(apiSearchUrl).then(result=>result.json()).then(data=>receiveResults(data))
    return false;
}

function receiveResults(data) {
    console.log(data);
    storeResultData(data);
    autoSelectMatch(searchId);
    addMatchToList(searchId); // only adds an empty item, details will be filled later
    geomMatchId = data['chosen_geom_id'];
    console.log(geomMatchId);
    requestChosenGeomMatch(searchId, geomMatchId);
    searchId += 1;
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

function updateListEntry(searchId2, geomMatch) {
    // get the list entry
    item = document.getElementById('search-id-' + searchId2);

    // calc display name and percent match
    geomMatchDisplayName = getDisplayName(geomMatch);
    geomMatchPercent = geomMatch.chosen_name_simil * 100;

    // set the match name
    infoName = item.querySelector('.search-info-name');
    infoName.innerText = 'Match: ' + geomMatchDisplayName + ` (${geomMatchPercent.toFixed(0)}%)`;

    // set the source
    infoSource = item.querySelector('.search-info-source');
    infoSource.innerText = 'Source: ' + geomMatch.source.name;

    // set temporal validity
    infoSource = item.querySelector('.search-info-time');
    if (geomMatch.valid_from === null) {
        validity = "Unknown";
    } else {
        validity = geomMatch.valid_from + ' - ' + geomMatch.valid_to;
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

function autoDisambiguateNames(id) {
    // user will likely manually disambiguate the names
    // but this method tries to do this automatically as a first guess

    // get results data for the search id
    data = resultsData[id];

    // the search results are already sorted by text similiraty
    // so for now just choose the first one (most similar)
    chosen = data.results[0];

    // update the results data with the chosen id
    data['chosen_name_id'] = chosen.id;
    data['chosen_name_simil'] = chosen.simil;
}

function autoDisambiguateGeoms(id) {
    // user will likely manually disambiguate the geoms
    // but this method tries to do this automatically as a first guess
    // this method is also affected by the chosen name matches which ranks the geoms

    // get results data for the search id
    data = resultsData[id];

    // the search results are already sorted by text similiraty
    // so for now just choose the first geom of the first name (most similar)
    chosenName = data.results[0];
    chosenGeomId = chosenName.admins[0];

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

    // update list entry
    updateListEntry(searchId2, geomData);

    // add to map
    addResultToMap(searchId2, geomData);
}

function openOptionsPopup() {
    elem = document.getElementById('options-popup').className = 'popup';
}

// close popups on clickout

document.onclick = function(event) {
    if (event.target.className == 'popup') {
        event.target.className = 'popup is-hidden';
    };
}
