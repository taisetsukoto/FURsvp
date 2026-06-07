(function () {
    'use strict';

    var TILES = {
        light: {
            url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        },
        dark: {
            url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
        }
    };

    var mapInstance = null;
    var tileLayer = null;
    var marker = null;

    function isDarkMode() {
        return document.body.classList.contains('dark-mode');
    }

    function createMarkerIcon() {
        return L.divIcon({
            className: 'event-map-marker',
            html: '<div class="event-map-marker-pin"></div>',
            iconSize: [14, 14],
            iconAnchor: [7, 7],
            popupAnchor: [0, -9]
        });
    }

    function applyTileTheme() {
        if (!mapInstance) return;
        var theme = isDarkMode() ? TILES.dark : TILES.light;
        if (tileLayer) {
            mapInstance.removeLayer(tileLayer);
        }
        tileLayer = L.tileLayer(theme.url, {
            attribution: theme.attribution,
            maxZoom: 19,
            subdomains: 'abcd'
        }).addTo(mapInstance);
    }

    function hideMapWrap(mapEl) {
        var wrap = mapEl.closest('.event-location-map-wrap');
        if (wrap) {
            wrap.style.display = 'none';
        }
    }

    function initEventLocationMap() {
        var mapEl = document.getElementById('eventLocationMap');
        if (!mapEl || typeof L === 'undefined') return;

        var query = mapEl.dataset.location;
        if (!query) {
            hideMapWrap(mapEl);
            return;
        }

        fetch(
            'https://nominatim.openstreetmap.org/search?format=json&q=' +
            encodeURIComponent(query) + '&limit=1&addressdetails=0',
            { headers: { 'Accept-Language': 'en' } }
        )
            .then(function (response) {
                if (!response.ok) throw new Error('Geocode failed');
                return response.json();
            })
            .then(function (results) {
                if (!results.length) {
                    hideMapWrap(mapEl);
                    return;
                }

                var lat = parseFloat(results[0].lat);
                var lon = parseFloat(results[0].lon);

                mapInstance = L.map(mapEl, {
                    scrollWheelZoom: false,
                    zoomControl: true,
                    attributionControl: true
                }).setView([lat, lon], 15);

                applyTileTheme();

                marker = L.marker([lat, lon], { icon: createMarkerIcon() })
                    .addTo(mapInstance)
                    .bindPopup(query);

                setTimeout(function () {
                    mapInstance.invalidateSize();
                }, 150);
            })
            .catch(function () {
                hideMapWrap(mapEl);
            });
    }

    document.addEventListener('DOMContentLoaded', initEventLocationMap);

    document.addEventListener('darkModeChanged', function () {
        applyTileTheme();
    });
})();
