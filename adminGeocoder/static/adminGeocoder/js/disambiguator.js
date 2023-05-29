
// TODO: probably no longer needed... 
disambiguationSearchId = null;
disambiguationSearchData = null;
disambiguationSearchTime = null;
currentSelectedGeomId = null;
currentSelectedGeomData = null;
currentExpandedGeomId = null;

function requestUpdateDisambiguator() {
    // set search time stamp
    disambiguationSearchTime = Date.now();

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
    fetch(apiSearchUrl).then(result=>result.json()).then(data=>receiveDisambiguationData(data))
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
    initDisambiguator(data);
}

function resetDisambiguator() {
    // need to set searchid? 
    //disambiguationSearchId = searchId2;
    // clear map
    selectedLayer.getSource().clear();
    disambiguationLayer.getSource().clear();
    similarLayer.getSource().clear();
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

function initDisambiguator(data) {
    // clear map
    selectedLayer.getSource().clear();
    disambiguationLayer.getSource().clear();
    // fix bug where map that's initially hidden won't show
    disambiguationMap.updateSize(); // otherwise will remain hidden until window resize
    // clear geoms table
    document.querySelector('#disambiguation-geom-table tbody').innerHTML = '';
    // set search input value
    document.getElementById('disambiguation-search-input').value = data.search;
    // init status
    disambiguatorCandidatesLoaded = 0;
    disambiguatorTotalCandidates = data.count;
    // set currently selected geom from stored data
    currentSelectedGeomId = data.chosen_geom_id;
    currentSelectedGeomData = data.chosen_geom_data;
    // show table
    document.querySelector('#disambiguation-geom-table').style.display = '';
    // add all possible geom candidates to table
    for (result of data.results) {
        // add to table
        addGeomToDisambiguationTable(result.id, result);
        // add bbox to map
        addResultBboxToMap(result);
        // increment load counter and status
        disambiguatorCandidatesLoaded += 1;
        updateLoadStatus();
    };
    // update all table row basket buttons
    updateBasketButtons();
    // zoom to layer
    zoomToDisambiguationLayer();
    // begin requesting similar geoms
    //requestAllSimilarGeoms();
}

function addResultBboxToMap(entry) {
    // copy the attr data
    entry = JSON.parse(JSON.stringify(entry));
    // add bbox as geom attr
    [xmin,ymin,xmax,ymax] = entry.bbox;
    poly = [[[xmin,ymin],[xmax,ymin],[xmax,ymax],[xmin,ymax],[xmin,ymin]]];
    geom = {'type':'Polygon', 'coordinates':poly};
    entry['geom'] = geom;
    // add to map
    addGeomToDisambiguationMap(entry);
}

function addGeomToDisambiguationTable(adminId, result) {
    //console.log(result)
    tbody = document.querySelector('#disambiguation-geom-table tbody');
    let tr = document.createElement('tr');
    tr.id = 'admin-candidate-id-' + adminId;
    tr.dataset.adminId = adminId;
    tr.className = 'admin-candidate-row';
    tr.onclick = function(){selectGeom(adminId)};
    tr.innerHTML = `
    <td class="admin-name-div">
        <span class="admin-name"><div class="symbol"></div>${getDisplayName(result)}</span>
        <div class="admin-source">(${result.source.name})</div>
    </td>
    <td class="admin-level" title="Administrative level"><div><img src="static/images/hierarchy-structure.png">ADM${getAdminLevel(result)}</div></td>
    <td class="admin-time" title="Representative of year(s)"><div><img src="static/images/time.png">${getAdminYears(result)}</div></td>
    <td class="admin-name-match-percent" title="Boundary name match"><div><img src="static/images/text-icon.png"><span>${(result.simil * 100).toFixed(1)}%</span></div></td>
    <!--
    <td class="similar-geom-match-percent" title="Cross-source boundary agreement/certainty"><div><img src="static/images/square.png"><span>...</span></div></td>
    <td class="admin-geom-lineres" title="Average distance between line vertices"><div><img src="static/images/shape.png"><span>${result.lineres.toFixed(1)}m</span></div></td>
    -->
    <div class="row-buttons">
        <button type="button" class="button small add-to-cart" onclick="event.stopPropagation(); addToBasket(getAdminById(${adminId}))">
            <span>Add</span><img src="static/images/basket.png">
        </button>
        <button type="button" class="button small remove-from-cart" onclick="event.stopPropagation(); removeFromBasket(${adminId})">
            <span>Added</span><img src="static/images/basket.png">
        </button>
    </div>
    `;
    tbody.appendChild(tr);
    // mark as selected
    if (result.id == currentSelectedGeomId) {
        tr.classList.add("selected-geom-row");
        tr.scrollIntoView({block:'nearest', inline:'nearest'});
    };
}

function updateLoadStatus() {
    // update status text
    if (disambiguatorTotalCandidates == null) {
        loadStatus = 'Searching...';
    } else if (disambiguatorCandidatesLoaded == disambiguatorTotalCandidates) {
        timeDelta = (Date.now() - disambiguationSearchTime);
        loadStatus = `Found ${disambiguatorCandidatesLoaded} matches in ${(timeDelta/1000.0).toFixed(2)} seconds`;
    } else {
        loadStatus = `Loading: ${disambiguatorCandidatesLoaded} of ${disambiguatorTotalCandidates} matches loaded`
    };
    document.getElementById('disambiguation-status').innerText = loadStatus;
    // also show/hide buttons
    if (!disambiguatorTotalCandidates) {
        document.getElementById('disambiguation-buttons').style.display = 'none';
    } else {
        document.getElementById('disambiguation-buttons').style.display = 'block';
    };
}

function selectGeom(adminId) {
    // unmark any selected admin candidate
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .admin-candidate-row');
    for (tr of rows) {
        tr.classList.remove("selected-geom-row");
    };
    // unmark any selected similar geom rows
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .similar-geom-admin');
    for (tr of rows) {
        tr.classList.remove("selected-geom-row");
    };
    // mark the admin candidate table entry as selected
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .admin-candidate-row');
    for (tr of rows) {
        if (tr.id == `admin-candidate-id-${adminId}`) {
            tr.classList.add("selected-geom-row");
            tr.scrollIntoView({block:'nearest', inline:'nearest'});
            break;
        };
    };
    // zoom if already selected (2nd click)
    if (adminId == currentSelectedGeomId) {
        zoomToDisambiguationId(adminId);
    };
    // remember
    currentSelectedGeomId = adminId;
    // select and zoom to map geom
    selectMapGeom(currentSelectedGeomId);
    // also get all similar geoms (if not already expanded)
    if (currentSelectedGeomId != currentExpandedGeomId) {
        requestSimilarGeoms(currentSelectedGeomId);
        currentExpandedGeomId = adminId;
    };
}

function selectSimilarGeom(adminId) {
    // unmark any selected admin candidate
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .admin-candidate-row');
    for (tr of rows) {
        tr.classList.remove("selected-geom-row");
    };
    // unmark any selected similar geom rows
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .similar-geom-admin');
    for (tr of rows) {
        tr.classList.remove("selected-geom-row");
    };
    // mark the similar geom table entry as selected
    rows = document.querySelectorAll('#disambiguation-geom-table tbody .similar-geom-admin');
    for (tr of rows) {
        if (tr.id == `similar-geom-id-${adminId}`) {
            tr.classList.add("selected-geom-row");
            tr.scrollIntoView({block:'nearest', inline:'nearest'});
            break;
        };
    };
    // zoom if already selected (2nd click)
    if (adminId == currentSelectedGeomId) {
        zoomToDisambiguationId(adminId);
    };
    // remember
    currentSelectedGeomId = adminId;
    // mark the map geom as selected
    selectMapGeom(adminId);
}



///////////////////
// similar geoms

/*
function requestAllSimilarGeoms() {
    let cur, nxt;
    cur = 0;
    nxt = 1;
    requestSimilarGeoms(disambiguationSearchData.results[cur].id, nxt);
}
*/

function requestSimilarGeoms(adminId, nxt=null) {
    console.log(`requesting similar for ${adminId}`)
    // clear any old similar geoms info
    clearSimilarGeomsFromTable();
    clearSimilarGeomsFromMap();
    // clear any previous loading text
    for (elem of document.querySelectorAll('.similar-geoms-loading')) {
        elem.remove();
    };
    // indicate loading to the user
    showSimilarGeomsLoading(adminId);
    // fetch full details of geom
    url = '/api/get_similar_admins/' + adminId;
    if ((nxt != null) & (nxt < disambiguationSearchData.results.length)) {    
        let nxtnxt = nxt + 1;
        fetch(url).then(result=>result.json()).then(data=>receiveSimilarGeoms(adminId, data)).then(function(){requestSimilarGeoms(disambiguationSearchData.results[nxt].id, nxtnxt)})
    } else {
        fetch(url).then(result=>result.json()).then(data=>receiveSimilarGeoms(adminId, data));
    };
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

function receiveSimilarGeoms(adminId, data) {
    // remove loading text
    span = document.querySelector('.similar-geoms-loading');
    span.remove();
    // ignore if not the latest
    if (adminId != currentExpandedGeomId) {
        return;
    };
    // update total source agreement
    //updateSelectedTableEntryAgreement(data);
    // add similar geoms to table
    addSimilarGeomsToTable(adminId, data.results);
    // add similar geoms to map
    addSimilarGeomsToMap(data.results);
}

function updateSelectedTableEntryAgreement(data) {
    span = document.querySelector('.selected-geom-row .similar-geom-match-percent div span');
    span.innerText = `${(data.agreement * 100).toFixed(1)}%`;
}

function addSimilarGeomsToTable(adminId, entries) {
    admin_tr = document.querySelector(`#admin-candidate-id-${adminId}`);
    insertBefore = admin_tr.nextSibling;
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
            <span class="admin-name"><div class="symbol"></div>${getDisplayName(entry)}</span>
            <div class="admin-source">(${entry.source.name})</div>
        </td>
        <td class="admin-level" title="Administrative level"><div><img src="static/images/hierarchy-structure.png">ADM${getAdminLevel(entry)}</div></td>
        <td class="admin-time" title="Representative of year(s)"><div><img src="static/images/time.png">${getAdminYears(entry)}</div></td>
        <td class="admin-name-match-percent"></td>
        <!--
        <td class="similar-geom-match-percent" title="Boundary similarity"><div><img src="static/images/square.png"><span>${(entry.simil * 100).toFixed(1)}%</span></div></td>
        <td class="admin-geom-lineres" title="Average distance between line vertices"><div><img src="static/images/shape.png"><span>${entry.lineres.toFixed(1)}m</span></div></td>
        -->
        <div class="row-buttons">
            <button type="button" class="button small add-to-cart" onclick="event.stopPropagation(); addToBasket(getAdminById(${entry.id}))">
                <span>Add</span><img src="static/images/basket.png">
            </button>
            <button type="button" class="button small remove-from-cart" onclick="event.stopPropagation(); removeFromBasket(${entry.id})">
                <span>Added</span><img src="static/images/basket.png">
            </button>
        </div>
        `;
        admin_tr.parentNode.insertBefore(tr, insertBefore);
    };
    // update basket buttons
    updateBasketButtons();
}
