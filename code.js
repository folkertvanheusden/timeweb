function mode_to_str(mode) {
    if (mode == "0")
        return "-";
    if (mode == "1")
        return "no fix";
    if (mode == "2")
        return "2D fix";
    if (mode == "3")
        return "3D fix";
    return "?";
}

function refresh_x_graph(target, table) {
    var element = document.getElementById(table);
    var positionInfo = element.getBoundingClientRect();
    var width = positionInfo.width;

    var url = '/graph-data-' + target + '?table=' + table + "&width=" + width;
    console.log('refreshing ' + url)

    var xhr = typeof XMLHttpRequest != 'undefined' ? new XMLHttpRequest() : new ActiveXObject('Microsoft.XMLHTTP');
    xhr.open('get', url, true);
    xhr.onreadystatechange = function() {
        console.log(target + '|' + table + ': ' + xhr.readyState + ' ' + xhr.status);
        if (xhr.readyState == 4 && xhr.status == 200) {
            element.innerHTML = xhr.responseText;
        }
    }
    xhr.send();
}

var interval = ___REPLACE_ME___;

function f_ntp_offset    () { refresh_x_graph('ntp', 'ntp_offset'); }
function f_dop           () { refresh_x_graph('gps', 'dop'); }
function f_pps_clk_offset() { refresh_x_graph('gps', 'pps_clk_offset'); }
function f_polar         () { refresh_x_graph('gps', 'polar'); }

f_ntp_offset();
setInterval(f_ntp_offset, interval);

f_dop();
setInterval(f_dop, interval);

f_pps_clk_offset();
setInterval(f_pps_clk_offset, interval);

f_polar();
setInterval(f_polar, interval);

var eventSourceNTP = new EventSource("/ntp");
eventSourceNTP.onmessage = function(e) {
    const obj = JSON.parse(e.data);

    // sysvars

    let ngtable = '<table>';
    ngtable += '<caption>NTP general</caption>';
    ngtable += '<thead><th>name</th><th>value</th><th>description</th></thead>';
    var poll_ts = new Date(obj['poll_ts'] * 1000);
    ngtable += `<tr><th>poll ts</th><td>${poll_ts}</td><td>when were these values retrieved</td></tr>`;
    for (const [key, value] of Object.entries(obj['sysvars'])) {
        ngtable += `<tr><th>${key}</th><td>${value}</td></tr>`;
    };
    ngtable += '</table>';

    const ngtable_container = document.getElementById('ntp-general-container');
    ngtable_container.innerHTML = ngtable;

    // peers

    let peerstable = '<table>';
    peerstable += '<caption>NTP peers</caption>';
    peerstable += '<thead><th>host</th><th>refid</th><th>stratum</th><th>offset</th><th>jitter</th></thead>';
    for (const [key, value] of Object.entries(obj['peers'])) {
        var host = value.srchost;
        if (host === undefined)
            host = value.srcadr;
        peerstable += `<tr><td>${host}</td><td>${value.refid}</td><td>${value.stratum}</td><td>${value.offset}</td><td>${value.jitter}</td></tr>`;
    };

    peerstable += '</table>';

    const peerstable_container = document.getElementById('ntp-peers-container');
    peerstable_container.innerHTML = peerstable;

    // details for selected peer

    var associd = obj['sysvars']['assoc']

    if (associd !== undefined) {
        let aptable = '<table>';
        aptable += '<caption>details for selected peer</caption>';
        aptable += '<thead><th>name</th><th>value</th></thead>';
        for (const [key, value] of Object.entries(obj['peers'][associd])) {
            aptable += `<tr><th>${key}</th><td>${value}</td></tr>`;
        };
        aptable += '</table>';

        const aptable_container = document.getElementById('ntp-selected-peer-container');
        aptable_container.innerHTML = aptable;
    }

    // MRU list

    var mrulist = obj['mrulist'];
    console.log(mrulist);

    let mrutable = '<table>';
    mrutable += '<caption>NTP network peers (' + new Date(mrulist['ts'] * 1000) + ')</caption>';
    mrutable += '<thead><th>address</th><th colspan=2>first</th><th colspan=2>last</th></thead>';
    mrutable += '<thead><th></th><th>mode/version</th><th>packet count</th><th>score</th><th>dropped</th></thead>';
    for (const [key, value] of Object.entries(mrulist['entries'])) {
        mrutable += `<tr><td>${value.addr}</td><td colspan=2>${value.first}</td><td colspan=2>${value.last}</td></tr>`;
        mrutable += `<tr><td></td><td>${value.mode_version}</td><td>${value.packet_count}</td><td>${value.score}</td><td>${value.dropped}</td></tr>`;
    };
    mrutable += '</table>';

    const mrutable_container = document.getElementById('ntp-mru-list-container');
    mrutable_container.innerHTML = mrutable;
};

var eventSourceGPS = new EventSource("/gps");
eventSourceGPS.onmessage = function(e) {
    const obj = JSON.parse(e.data);
    if (obj['class'] == 'TPV') {
        document.getElementById('status'   ).innerHTML = obj['status'];
        document.getElementById('time'     ).innerHTML = obj['time'  ];
        document.getElementById('mode'     ).innerHTML = mode_to_str(obj['mode'  ]);
        document.getElementById('latitude' ).innerHTML = obj['lat'   ];
        document.getElementById('longitude').innerHTML = obj['lon'   ];
        document.getElementById('altitude' ).innerHTML = obj['alt'   ];
        document.getElementById('epx'      ).innerHTML = obj['epx'   ];
        document.getElementById('epy'      ).innerHTML = obj['epy'   ];
        document.getElementById('epv'      ).innerHTML = obj['epv'   ];
        document.getElementById('ept'      ).innerHTML = obj['ept'   ];
        document.getElementById('eps'      ).innerHTML = obj['eps'   ];
        document.getElementById('eph'      ).innerHTML = obj['eph'   ];
        document.getElementById('epc'      ).innerHTML = obj['epc'   ];
        document.getElementById('magvar'   ).innerHTML = obj['magvar'];
        document.getElementById('speed'    ).innerHTML = obj['speed' ];
        document.getElementById('geoidSep' ).innerHTML = obj['geoidSep'];
        document.getElementById('sep'      ).innerHTML = obj['sep'   ];
        document.getElementById('track'    ).innerHTML = obj['track' ];
    }
    else if (obj['class'] == 'PPS') {
        let ppstable = '<table>';
        ppstable += '<caption>PPS</caption>';
        ppstable += '<thead><th>name</th><th>value</th></thead>';
        for (const [key, value] of Object.entries(obj)) {
            ppstable += `<tr><th>${key}</th><td>${value}</td></tr>`;
        };
        ppstable += '</table>';

        const ppstable_container = document.getElementById('pps-container');
        ppstable_container.innerHTML = ppstable;
    }
    else if (obj['class'] == 'SKY') {
        // general data
        document.getElementById('hdop').innerHTML = obj['hdop'];
        document.getElementById('pdop').innerHTML = obj['pdop'];
        document.getElementById('vdop').innerHTML = obj['vdop'];
        document.getElementById('nsat').innerHTML = obj['nSat'];
        document.getElementById('usat').innerHTML = obj['uSat'];

        // list of satellites
        let stable = '<table>';
        stable += '<caption>satellite details</caption>';
        stable += '<thead><th>PRN ID</th><th>azimuth</th><th>elevation</th><th>gnssid</th><th>signal strength</th><th>svid</th><th>in use</th></thead>';
        obj['satellites'].forEach(item => {
            stable += `<tr><td>${item.PRN}</td><td>${item.az}</td><td>${item.el}</td><td>${item.gnssid}</td><td>${item.ss}</td><td>${item.svid}</td><td>${item.used}</td></tr>`;
        });
        stable += '</table>';

        const stable_container = document.getElementById('sats-container');
        stable_container.innerHTML = stable;
    }
    else if (obj['class'] == 'DEVICES') {
        let dtable = '<table>';
        dtable += '<caption>gpsd devices</caption>';
        dtable += '<thead><th>driver</th><th>path</th><th>activated at</th></thead>';
        obj['devices'].forEach(item => {
            dtable += `<tr><td>${item.driver}</td><td>${item.path}</td><td>${item.activated}</td></tr>`;
        });
        dtable += '</table>';

        const dtable_container = document.getElementById('devices-container');
        dtable_container.innerHTML = dtable;
    }
    else {
        console.log(obj);
    }
};
