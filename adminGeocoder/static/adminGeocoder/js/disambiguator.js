
function openDisambiguationPopup(searchId2) {
    document.getElementById('disambiguation-popup').className = 'popup';
    initDisambiguator(searchId2);
}

function initDisambiguator(searchId2) {
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
    // add possible geoms
    for (result of data.results) {
        for (adminId of result.admins) {
            addGeomToDisambiguationTable(adminId, result);
            requestGeomCandidate(adminId);
        };
    };
}

function addGeomToDisambiguationTable(adminId, result) {
    tbody = document.querySelector('#disambiguation-geom-table tbody');
    tr = document.createElement('tr');
    tr.id = 'admin-candidate-id-' + adminId;
    tr.innerHTML = `
    <td>...</td>
    <td>${(result.perc_diff * 100).toFixed(1)}%</td>
    <td>...</td>
    <td>...</td>
    `;
    tbody.appendChild(tr);
}

function requestGeomCandidate(adminId) {
    // fetch full details of geom candidate
    url = '/api/get_admin/' + adminId;
    fetch(url).then(result=>result.json()).then(data=>receiveGeomCandidate(data));
}

function receiveGeomCandidate(geomData) {
    console.log(geomData);

    // update geom table entry
    updateDisambiguationTableEntry(geomData);

    // add to map
    addGeomToDisambiguationMap(geomData);

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
}

function updateLoadStatus() {
    disambiguatorCandidatesLoaded += 1;
    if (disambiguatorCandidatesLoaded == disambiguatorTotalCandidates) {
        loadStatus = `All ${disambiguatorCandidatesLoaded} matches loaded`;
    } else {
        loadStatus = `Loading: ${disambiguatorCandidatesLoaded} of ${disambiguatorTotalCandidates} matches loaded`
    };
    document.getElementById('disambiguation-status').innerText = loadStatus;
}
