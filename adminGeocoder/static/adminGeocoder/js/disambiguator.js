
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
    // add possible geoms
    data = resultsData[searchId2];
    for (result of data.results) {
        for (adminId of result.admins) {
            addGeomToDisambiguationTable(adminId);
            requestGeomCandidate(adminId);
        };
    };
}

function addGeomToDisambiguationTable(adminId) {
    tbody = document.querySelector('#disambiguation-geom-table tbody');
    tr = document.createElement('tr');
    tr.id = 'admin-candidate-id-' + adminId;
    tr.innerHTML = `
    <td>...</td>
    <td>...</td>
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
}

function updateDisambiguationTableEntry(geomData) {
    tr = document.getElementById('admin-candidate-id-' + geomData.id);
    if (geomData.valid_from === null) {
        validity = 'Unknown';
    } else {
        validity = `${geomData.valid_from} - ${geomData.valid_to}`;
    };
    tr.innerHTML = `
    <td>${getDisplayName(geomData)}</td>
    <td>${geomData.source.name}</td>
    <td>${validity}</td>
    <td>...</td>
    `;
}
