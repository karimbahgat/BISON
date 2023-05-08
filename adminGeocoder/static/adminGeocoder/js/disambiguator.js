
// TODO: probably no longer needed... 
disambiguationSearchId = null;
disambiguationSearchData = null;
currentSelectedGeomId = null;
currentSelectedGeomData = null;

/*
function openDisambiguationPopup(searchId2) {
    document.getElementById('disambiguation-popup').className = 'popup';
    disambiguationSearchData = resultsData[searchId2];
    initDisambiguator(searchId2);
}
*/

function requestUpdateDisambiguationPopup() {
    // get search input and clear
    input = document.querySelector('#disambiguation-search-input');
    search = input.value;
    console.log(search);

    // reset disambiguator
    resetDisambiguator();

    // disable search button and indicate loading
    but = document.querySelector('#disambiguation-search-bar > button');
    but.disabled = true;
    but.querySelector('span').style.visibility = 'hidden';
    but.querySelector('img').style.visibility = 'visible';

    // search for name
    apiSearchUrl = 'api/search/name_hierarchy?search='+search;
    fetch(apiSearchUrl).then(result=>result.json()).then(data=>updateDisambiguationResults(data))
    return false;
}

function receiveDisambiguationData(data) {
    disambiguationSearchData = data;
    updateDisambiguationResults(data);
}

function getAdminById(id) {
    for (res of disambiguationSearchData.results) {
        if (res.id == id) {
            return res;
        }
    }
}

function updateDisambiguationResults(data) {
    // reenable search button and stop loading icon
    but = document.querySelector('#disambiguation-search-bar > button');
    but.disabled = false;
    but.querySelector('span').style.visibility = 'visible';
    but.querySelector('img').style.visibility = 'hidden';

    // handle no results
    if (data.count == 0) {
        // init status
        disambiguatorCandidatesLoaded = 0;
        disambiguatorTotalCandidates = 0;
        // update load status
        updateLoadStatus();
        return;
    };

    // process results
    disambiguationSearchData = data;
    autoSelectMatch(disambiguationSearchId, data); // still needed? 
    initDisambiguator(disambiguationSearchId, data);
}

function resetDisambiguator() {
    // need to set searchid? 
    //disambiguationSearchId = searchId2;
    // clear map
    selectedLayer.getSource().clear();
    disambiguationLayer.getSource().clear();
    // fix bug where map that's initially hidden won't show
    disambiguationMap.updateSize(); // otherwise will remain hidden until window resize
    // clear and hide geoms table
    document.querySelector('#disambiguation-geom-table').style.display = 'none';
    document.querySelector('#disambiguation-geom-table tbody').innerHTML = '';
    // init status
    disambiguatorCandidatesLoaded = null;
    disambiguatorTotalCandidates = null;
    // update load status
    updateLoadStatus();
}

function initDisambiguator(searchId2, data=null) {
    // read data from the provided 'data' arg
    // otherwise read from the stored data in searchid
    disambiguationSearchId = searchId2;
    // clear map
    selectedLayer.getSource().clear();
    disambiguationLayer.getSource().clear();
    // fix bug where map that's initially hidden won't show
    disambiguationMap.updateSize(); // otherwise will remain hidden until window resize
    // clear geoms table
    document.querySelector('#disambiguation-geom-table tbody').innerHTML = '';
    // set search input value
    if (data == null) {
        data = resultsData[searchId2];
    };
    document.getElementById('disambiguation-search-input').value = data.search;
    // init status
    disambiguatorCandidatesLoaded = 0;
    disambiguatorTotalCandidates = data.count;
    // set currently selected geom from stored data
    currentSelectedGeomId = data.chosen_geom_id;
    currentSelectedGeomData = data.chosen_geom_data;
    // show currently selected geom on map
    requestGeomForMap(currentSelectedGeomId);
    // show table
    document.querySelector('#disambiguation-geom-table').style.display = '';
    // add all possible geom candidates to table
    for (result of data.results) {
        disambiguatorCandidatesLoaded += 1;
        addGeomToDisambiguationTable(result.id, result);
        updateLoadStatus();
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
    console.log(result)
    tbody = document.querySelector('#disambiguation-geom-table tbody');
    let tr = document.createElement('tr');
    tr.id = 'admin-candidate-id-' + adminId;
    tr.dataset.adminId = adminId;
    tr.className = 'admin-candidate-row';
    tr.onclick = function(){selectGeom(adminId)};
    tr.innerHTML = `
    <td class="admin-name-div">
        <span class="admin-name">&#9654; ${getDisplayName(result)}</span>
        <div class="admin-source"><a href="/datasets/${result.source.id}" target="_blank">${result.source.name}</a></div>
    </td>
    <td class="admin-level" title="Administrative level"><div><img src="static/images/hierarchy-structure.png">ADM${getAdminLevel(result)}</div></td>
    <td class="admin-time" title="Representative of year(s)"><div><img src="static/images/time.png">${getAdminYears(result)}</div></td>
    <td class="admin-name-match-percent" title="Boundary name match"><div><img src="static/images/text-icon.png"><span>${(result.simil * 100).toFixed(1)}%</span></div></td>
    <td class="similar-geom-match-percent" title="Cross-source boundary agreement/certainty"><div><img src="static/images/square.png"><span>...</span></div></td>
    <td class="admin-geom-lineres" title="Average distance between line vertices"><div><img src="static/images/shape.png"><span>${result.lineres.toFixed(1)}m</span></div></td>
    <div class="row-buttons">
        <button type="button" class="button small add-to-cart" onclick="event.stopPropagation(); addToBasket(getAdminById(${adminId}))">
            <span>Add</span><img src="static/images/basket.png">
        </button>
        <button type="button" class="button small remove-from-cart" onclick="event.stopPropagation(); removeFromBasket(${adminId})">
            <span>Remove</span><img src="static/images/basket.png">
        </button>
    </div>
    `;
    tbody.appendChild(tr);
    // mark as selected
    if (result.id == currentSelectedGeomId) {
        tr.classList.add("selected-geom-row");
        tr.scrollIntoView({block:'nearest', inline:'nearest'});
    };
    // update basket buttons
    updateBasketButtons();
}

/*
function requestGeomCandidates(adminIds) {
    // fetch full details of geom candidate
    adminIds = adminIds.join(',');
    url = '/api/get_admin/' + adminIds + '?geom=0';
    console.log(url)
    fetch(url).then(result=>result.json()).then(data=>receiveGeomCandidates(data));
}

function receiveGeomCandidates(geomDatas) {
    console.log(geomDatas);

    // update geom table entry
    for (geomData of geomDatas) {
        updateDisambiguationTableEntry(geomData);
    };

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
    tr.querySelector('.admin-name').innerHTML = `&#9654; ${getDisplayName(geomData)}`;
    tr.querySelector('.admin-source').innerText = geomData.source.name;
    tr.querySelector('.admin-level').innerHTML = `<img src="static/images/hierarchy-structure.png">ADM${getAdminLevel(geomData)}`;
    //tr.querySelector('admin-validity').innerText = validity;
    // mark as selected
    if (geomData.id == currentSelectedGeomId) {
        tr.className = "admin-candidate-row selected-geom-row";
        tr.scrollIntoView({block:'nearest', inline:'nearest'});
    };
}
*/

function updateLoadStatus() {
    if (disambiguatorTotalCandidates == null) {
        loadStatus = 'Searching...';
    } else if (disambiguatorCandidatesLoaded == disambiguatorTotalCandidates) {
        loadStatus = `Found ${disambiguatorCandidatesLoaded} matches`;
    } else {
        loadStatus = `Loading: ${disambiguatorCandidatesLoaded} of ${disambiguatorTotalCandidates} matches loaded`
    };
    document.getElementById('disambiguation-status').innerText = loadStatus;
}

function selectGeom(adminId) {
    // unmark any selected similar geom rows
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .similar-geom-admin');
    for (tr of rows) {
        tr.classList.remove("similar-geom-admin");
    };
    // mark the admin candidate table entry as selected
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .admin-candidate-row');
    for (tr of rows) {
        if (tr.id == `admin-candidate-id-${adminId}`) {
            tr.classList.add("selected-geom-row");
            tr.scrollIntoView({block:'nearest', inline:'nearest'});
        } else {
            tr.classList.remove("selected-geom-row");
        };
    };
    // remember
    currentSelectedGeomId = adminId;
    // clear map
    disambiguationLayer.getSource().clear();
    // show currently selected geom on map
    requestGeomForMap(currentSelectedGeomId);
    // also show all similar geoms to map
    requestSimilarGeomsForMap(currentSelectedGeomId);
}

function selectSimilarGeom(adminId) {
    // unmark any selected admin candidate
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .admin-candidate-row');
    for (tr of rows) {
        tr.classList.remove("selected-geom-row");
    };
    // mark the similar geom table entry as selected
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .similar-geom-admin');
    for (tr of rows) {
        if (tr.id == `similar-geom-id-${adminId}`) {
            tr.classList.add("selected-geom-row");
            tr.scrollIntoView({block:'nearest', inline:'nearest'});
        } else {
            tr.classList.remove("selected-geom-row");
        };
    };
    // remember
    currentSelectedGeomId = adminId;
    // mark the map geom as selected
    selectMapGeom(adminId);
}

/*
function saveDisambiguator() {
    saveSearchInput();
    saveGeomSelection();
}

function saveSearchInput() {
    resultsData[disambiguationSearchId] = disambiguationSearchData;
}

function saveGeomSelection() {
    // change the stored geom selection
    searchData = resultsData[disambiguationSearchId];
    searchData.chosen_geom_id = currentSelectedGeomId;
    searchData.chosen_geom_data = currentSelectedGeomData;
    // set geom match
    requestChosenGeomMatch(disambiguationSearchId, currentSelectedGeomId);
    // set geom agreement
    requestChosenGeomAgreement(disambiguationSearchId);
    // close popup
    document.getElementById('disambiguation-popup').className = 'popup is-hidden';
}

function cancelDisambiguator() {
    // reset the temporary geom selection variable
    // maybe not necessary
    searchData = resultsData[disambiguationSearchId];
    currentSelectedGeomId = searchData.chosen_geom_id;
    currentSelectedGeomData = searchData.chosen_geom_data;
    // close popup
    document.getElementById('disambiguation-popup').className = 'popup is-hidden';
}
*/



///////////////////
// similar geoms

function requestSimilarGeomsForMap(adminId) {
    // clear any old similar geoms info
    clearSimilarGeomsFromTable();
    // indicate loading to the user
    showSimilarGeomsLoading(adminId);
    // fetch full details of geom
    url = '/api/get_best_source_matches/' + adminId;
    fetch(url).then(result=>result.json()).then(data=>receiveSimilarGeomsForMap(data));
}

function clearSimilarGeomsFromTable() {
    elems = document.querySelectorAll('.similar-geom-admin');
    for (elem of elems) {
        elem.remove();
    };
}

function showSimilarGeomsLoading(adminId) {
    // indicate loading by adding a row with loading text
    // right below the table row of this adminId
    tr = document.getElementById('admin-candidate-id-' + adminId);
    loading_tr = document.createElement('tr');
    loading_tr.className = 'similar-geoms-loading';
    tr.parentNode.insertBefore(loading_tr, tr.nextSibling);
    loading_td = document.createElement('td');
    loading_td.colSpan = "5";
    span = document.createElement('span');
    span.innerHTML = '<img src="static/images/Spinner-1s-200px.gif"> Looking for similar geometries';
    loading_td.appendChild(span);
    loading_tr.appendChild(loading_td);
}

function receiveSimilarGeomsForMap(data) {
    // remove loading text
    span = document.querySelector('.similar-geoms-loading');
    span.remove();
    // update total source agreement
    updateSelectedTableEntryAgreement(data);
    // add similar geoms to table
    addSimilarGeomsToTable(data.results);
    // add similar geoms to map
    for (entry of data.results) {
        requestGeomForMap(entry.id);
    };
}

function updateSelectedTableEntryAgreement(data) {
    span = document.querySelector('.selected-geom-row .similar-geom-match-percent div span');
    span.innerText = `${(data.agreement * 100).toFixed(1)}%`;
}

function addSimilarGeomsToTable(entries) {
    selected_tr = document.querySelector('.selected-geom-row');
    insertBefore = selected_tr.nextSibling;
    for (let entry of entries) {
        console.log(entry)
        tr = document.createElement('tr');
        tr.id = 'similar-geom-id-' + entry.id;
        tr.dataset.adminId = entry.id;
        tr.className = 'similar-geom-admin';
        tr.onclick = function(){selectSimilarGeom(entry.id)};
        if (entry.valid_from === null) {
            validity = 'Unknown';
        } else {
            validity = `${entry.valid_from} - ${entry.valid_to}`;
        };
        tr.innerHTML = `
        <td class="admin-name-div">
            <span class="admin-name">${getDisplayName(entry)}</span>
            <div class="admin-source"><a href="/datasets/${entry.source.id}" target="_blank">(${entry.source.name})</a></div>
        </td>
        <td class="admin-level" title="Administrative level"><div><img src="static/images/hierarchy-structure.png">ADM${getAdminLevel(entry)}</div></td>
        <td class="admin-time" title="Representative of year(s)"><div><img src="static/images/time.png">${getAdminYears(entry)}</div></td>
        <td class="admin-name-match-percent"></td>
        <td class="similar-geom-match-percent" title="Boundary similarity"><div><img src="static/images/square.png"><span>${(entry.simil * 100).toFixed(1)}%</span></div></td>
        <td class="admin-geom-lineres" title="Average distance between line vertices"><div><img src="static/images/shape.png"><span>${entry.lineres.toFixed(1)}m</span></div></td>
        <div class="row-buttons">
            <button type="button" class="button small add-to-cart" onclick="event.stopPropagation(); addToBasket(getAdminById(${entry.id}))">
                <span>Add</span><img src="static/images/basket.png">
            </button>
            <button type="button" class="button small remove-from-cart" onclick="event.stopPropagation(); removeFromBasket(${entry.id})">
                <span>Remove</span><img src="static/images/basket.png">
            </button>
        </div>
        `;
        selected_tr.parentNode.insertBefore(tr, insertBefore);
    };
    // update basket buttons
    updateBasketButtons();
}
