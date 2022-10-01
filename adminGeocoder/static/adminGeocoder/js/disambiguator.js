
disambiguationSearchId = null;
currentSelectedGeomId = null;

function openDisambiguationPopup(searchId2) {
    document.getElementById('disambiguation-popup').className = 'popup';
    initDisambiguator(searchId2);
}

function initDisambiguator(searchId2) {
    disambiguationSearchId = searchId2;
    // clear map
    disambiguationLayer.getSource().clear();
    // fix bug where map that's initially hidden won't show
    disambiguationMap.updateSize(); // otherwise will remain hidden until window resize
    // clear geoms table
    document.querySelector('#disambiguation-geom-table tbody').innerHTML = '';
    // set search input value
    data = resultsData[searchId2];
    document.getElementById('disambiguation-search-input').value = data.search;
    // init status
    disambiguatorCandidatesLoaded = 0;
    disambiguatorTotalCandidates = 0;
    for (result of data.results) {
        disambiguatorTotalCandidates += result.admins.length;
    };
    // set currently selected geom from stored data
    currentSelectedGeomId = data.chosen_geom_id
    // show currently selected geom on map
    requestGeomForMap(currentSelectedGeomId);
    // add all possible geom candidates to table
    for (result of data.results) {
        for (adminId of result.admins) {
            addGeomToDisambiguationTable(adminId, result);
            requestGeomCandidate(adminId);
        };
    };
    // also show all similar geoms to map
    requestSimilarGeomsForMap(currentSelectedGeomId);
}

function requestGeomForMap(adminId) {
    // fetch full details of geom
    url = '/api/get_admin/' + adminId;
    fetch(url).then(result=>result.json()).then(data=>receiveGeomForMap(data));
}

function receiveGeomForMap(data) {
    // add to map
    addGeomToDisambiguationMap(data);
}

function addGeomToDisambiguationTable(adminId, result) {
    tbody = document.querySelector('#disambiguation-geom-table tbody');
    tr = document.createElement('tr');
    tr.id = 'admin-candidate-id-' + adminId;
    tr.className = 'admin-candidate-row';
    tr.onclick = function(){selectGeom(adminId)};
    tr.innerHTML = `
    <td style="width:30%">...</td>
    <td class="admin-name-match-percent"><img src="static/images/text-icon.png"><span>${(result.simil * 100).toFixed(1)}%</span></td>
    <td>...</td>
    <td>...</td>
    `;
    tbody.appendChild(tr);
}

function requestGeomCandidate(adminId) {
    // fetch full details of geom candidate
    url = '/api/get_admin/' + adminId + '?geom=0';
    fetch(url).then(result=>result.json()).then(data=>receiveGeomCandidate(data));
}

function receiveGeomCandidate(geomData) {
    console.log(geomData);

    // update geom table entry
    updateDisambiguationTableEntry(geomData);

    // update status
    updateLoadStatus();
}

function updateDisambiguationTableEntry(geomData) {
    tr = document.getElementById('admin-candidate-id-' + geomData.id);
    if (geomData.valid_from === null) {
        validity = 'Unknown';
    } else {
        validity = `${geomData.valid_from} - ${geomData.valid_to}`;
    };
    tdList = tr.querySelectorAll('td');
    tdList[0].innerText = getDisplayName(geomData);
    tdList[2].innerText = geomData.source.name;
    tdList[3].innerText = validity;
    // mark as selected
    if (geomData.id == currentSelectedGeomId) {
        tr.className = "admin-candidate-row selected-geom-row";
        tr.scrollIntoView({block:'nearest', inline:'nearest'});
    };
}

function updateLoadStatus() {
    disambiguatorCandidatesLoaded += 1;
    if (disambiguatorCandidatesLoaded == disambiguatorTotalCandidates) {
        loadStatus = `Found ${disambiguatorCandidatesLoaded} matches`;
    } else {
        loadStatus = `Loading: ${disambiguatorCandidatesLoaded} of ${disambiguatorTotalCandidates} matches loaded`
    };
    document.getElementById('disambiguation-status').innerText = loadStatus;
}

function selectGeom(adminId) {
    // mark the table entry as selected
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .admin-candidate-row');
    for (tr of rows) {
        if (tr.id == `admin-candidate-id-${adminId}`) {
            tr.className = "admin-candidate-row selected-geom-row";
            tr.scrollIntoView({block:'nearest', inline:'nearest'});
        } else {
            tr.className = "admin-candidate-row";
        };
    };
    // clear map
    disambiguationLayer.getSource().clear();
    // mark the map geom as selected
    //selectMapGeom(adminId);
    // remember
    currentSelectedGeomId = adminId;
    // show currently selected geom on map
    requestGeomForMap(currentSelectedGeomId);
    // also show all similar geoms to map
    requestSimilarGeomsForMap(currentSelectedGeomId);
}

function saveDisambiguator() {
    saveGeomSelection();
}

function saveGeomSelection() {
    // change the stored geom selection
    searchData = resultsData[disambiguationSearchId];
    searchData.chosen_geom_id = currentSelectedGeomId;
    // set geom match
    requestChosenGeomMatch(disambiguationSearchId, currentSelectedGeomId);
    // close popup
    document.getElementById('disambiguation-popup').className = 'popup is-hidden';
}

function cancelDisambiguator() {
    // reset the temporary geom selection variable
    // maybe not necessary
    searchData = resultsData[disambiguationSearchId];
    currentSelectedGeomId = searchData.chosen_geom_id;
    // close popup
    document.getElementById('disambiguation-popup').className = 'popup is-hidden';
}



///////////////////
// similar geoms

function requestSimilarGeomsForMap(adminId) {
    // clear any old similar geoms info
    clearSimilarGeomsFromTable();
    // indicate loading to the user
    showSimilarGeomsLoading(adminId);
    // fetch full details of geom
    url = '/api/get_similar_admins/' + adminId;
    fetch(url).then(result=>result.json()).then(data=>receiveSimilarGeomsForMap(data));
}

function clearSimilarGeomsFromTable() {
    elem = document.querySelector('.similar-geoms-tr');
    if (elem) {elem.remove()};
}

function showSimilarGeomsLoading(adminId) {
    // indicate loading by adding a row with loading text
    // right below the table row of this adminId
    tr = document.getElementById('admin-candidate-id-' + adminId);
    similar_tr = document.createElement('tr');
    similar_tr.className = 'similar-geoms-tr';
    similar_td = document.createElement('td');
    similar_td.className = 'similar-geoms-td';
    similar_td.colSpan = "4";
    similar_tr.appendChild(similar_td);
    tr.parentNode.insertBefore(similar_tr, tr.nextSibling);

    // create a text to indicate loading
    span = document.createElement('span');
    span.className = 'similar-geoms-loading';
    span.innerHTML = '<img src="static/images/Spinner-1s-200px.gif"> Looking for similar geometries';
    similar_td.appendChild(span);

    // create a table inside this tr
    table = document.createElement('table');
    table.className = 'similar-geoms-table';
    similar_td.appendChild(table);
}

function receiveSimilarGeomsForMap(data) {
    // remove loading text
    span = document.querySelector('.similar-geoms-loading');
    span.remove();
    // add similar geoms
    for (entry of data.results) {
        addSimilarGeomToTable(entry);
        requestGeomForMap(entry.id);
    };
}

function addSimilarGeomToTable(entry) {
    console.log(entry)
    table = document.querySelector('.similar-geoms-table');
    tr = document.createElement('tr');
    tr.id = 'similar-geom-id-' + entry.id;
    tr.className = 'similar-geom-admin';
    if (entry.valid_from === null) {
        validity = 'Unknown';
    } else {
        validity = `${entry.valid_from} - ${entry.valid_to}`;
    };
    tr.innerHTML = `
    <td style="width:30%">&#9654; ${getDisplayName(entry)}</td>
    <td class="similar-geom-match-percent"><img src="static/images/square.png"><span>${(entry.simil * 100).toFixed(1)}%</span></td>
    <td>${entry.source.name}</td>
    <td>${validity}</td>
    `;
    table.appendChild(tr);
}
