
basketData = [];

function toggleBasket() {
    basket = document.getElementById('basket-div');
    if (basket.classList.contains('show')) {
        basket.classList.remove('show');
    } else {
        basket.classList.add('show');
    };
}

function showBasketMessage(msg) {
    console.log('should show msg '+msg)
    msgElem = document.getElementById('basket-message');
    msgElem.innerText = msg;
    // show msg
    msgElem.classList.remove('fadeout');
    // then trigger fadeout (after small delay)
    setTimeout(function(){
        msgElem.classList.add('fadeout');
    }, 10)
}

function addToBasket(data) {
    addToBasketData(data);
    addToBasketGeoms(data.id);
    updateBasketList();
    updateBasketCounts();
    updateBasketButtons();
    showBasketMessage('Added to Basket');
}

function addToBasketData(data) {
    basketData.push(data);
}

function updateBasketCounts() {
    // get count
    count = basketData.length;
    // update count elements
    for (elem of document.querySelectorAll('.basket-count')) {
        elem.innerText = count;
        elem.dataset.count = count;
    };
}

function updateBasketButtons() {
    //console.log('should update basket buttons')
    // collect admin ids from basket
    adminIds = [];
    for (data of basketData) {
        adminIds.push(data.id.toString());
    };
    // loop all admin rows
    rows = document.querySelectorAll('#disambiguation-geom-table tbody tr');
    for (let tr of rows) {
        // set in-basket class if adminid in basket
        let adminId = tr.dataset.adminId;
        if (adminIds.includes(adminId)) {
            tr.classList.add('in-basket');
        } else {
            tr.classList.remove('in-basket');
        };
    };
}

function updateBasketList() {
    // clear basket list
    results = document.getElementById('basket-results');
    results.innerHTML = '';
    // rebuild basket list
    let basketId = 0;
    for (let data of basketData) {
        addToBasketList(basketId, data);
        basketId += 1;
    };
}

function addToBasketList(basketId, data) {
    console.log('adding to basket')
    console.log(data)
    results = document.getElementById('basket-results');
    let adminId = data.id;
    
    item = document.createElement('div');
    item.id = 'basket-id-' + basketId;
    item.className = 'basket-item box';
    //item.onclick = function(){showListEntry(resultId)};
    results.appendChild(item);
    
    /*
    thumb = document.createElement('img');
    thumb.className = 'search-thumbnail';
    thumb.src = 'https://cdn-icons-png.flaticon.com/512/235/235861.png';
    item.appendChild(thumb);
    */
    
    info = document.createElement('div');
    info.className = 'basket-info';
    item.appendChild(info);

    infoName = document.createElement('h4');
    infoName.className = 'basket-info-name';
    infoName.innerHTML = `<span class="basket-item-id">${basketId+1}</span>"${getDisplayName(data)}"`;
    info.appendChild(infoName);

    infoSource = document.createElement('div');
    infoSource.className = 'basket-info-source';
    infoSource.innerHTML = `${data.source.name}`;
    info.appendChild(infoSource);

    // buttons
    buttons = document.createElement('div');
    buttons.className = 'basket-item-buttons';
    item.appendChild(buttons);
    buttons.innerHTML = `
        <div class="basket-info-level" title="Administrative level"><div><img src="static/images/hierarchy-structure.png"><span>${getAdminLevel(data)}</span></div></div>
        <div class="basket-info-name-match" title="Boundary name match"><div><img src="static/images/text-icon.png"><span>...</span></div></div>
        <div class="basket-info-geom-match" title="Cross-source boundary agreement/certainty"><div><img src="static/images/square.png"><span>...</span></div></div>
    `;

    // remove
    drop = document.createElement('span');
    drop.innerHTML = '&times;';
    drop.className = 'basket-item-dropbut';
    drop.onclick = function(){removeFromBasket(adminId)};
    item.appendChild(drop);

    //scroll into view
    results.scrollTop = results.scrollHeight;
}

function getDisplayName(adminData) {
    // construct the display name
    names = [];
    for (parent of adminData.hierarchy) {
        firstName = parent.names[0];
        names.push(firstName);
    };
    displayName = names.join(' - ');
    return displayName;
}

function getAdminLevel(adminData) {
    // get the admin level
    // assume hierarchy has lowest level first
    level = adminData.hierarchy[0].level;
    return level;
}

function getAdminYears(adminData) {
    // get the admin year(s) of validity as text
    if (adminData.valid_from != null & adminData.valid_to != null) {
        fromYear = adminData.valid_from.slice(0,4);
        toYear = adminData.valid_to.slice(0,4);
        if (fromYear == toYear) {
            return `${fromYear}`;
        } else {
            return `${fromYear}&rarr;${toYear}`;
        };
    } else {
        return 'Unk.'
    }
}

function removeFromBasket(adminId) {
    // remove from data
    removeFromBasketData(adminId);
    removeFromBasketGeoms(adminId);
    // update visuals
    updateBasketList();
    updateBasketCounts();
    updateBasketButtons();
    showBasketMessage('Removed from Basket');
}

/*
function removeFromBasketList(basketId) {
    item = document.getElementById('basket-id-' + basketId);
    item.remove();
}
*/

function removeFromBasketData(adminId) {
    // rebuild the global basketData variable
    // by filtering out those basketData entries that match adminId (should only be one)
    function keep(data) {
        return data.id != adminId;
    };
    filtered = basketData.filter(keep); 
    basketData = filtered;
}
