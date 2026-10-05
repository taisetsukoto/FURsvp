(function () {
    'use strict';

    var BASE_STYLES = {
        light: 'https://tiles.openfreemap.org/styles/positron',
        dark: 'https://tiles.openfreemap.org/styles/dark'
    };

    var PALETTES = {
        light: {
            land: '#f7f9fc',
            landWash: '#e7edff',
            park: '#d7eee2',
            wood: '#c5e4d2',
            water: '#b3d1f7',
            waterway: '#7eaae6',
            building: '#ffffff',
            buildingLine: '#b4c6de',
            road: '#ffffff',
            roadMinor: '#c5d4ea',
            roadCasing: '#8fa6c4',
            motorway: '#d6e6fb',
            motorwayCasing: '#2a3faa',
            path: '#c5d4ea',
            rail: '#9aafc9',
            railDash: '#f7f9fc',
            boundary: '#64748b',
            label: '#334155',
            labelStrong: '#1e293b',
            labelMuted: '#64748b',
            waterLabel: '#2a3faa',
            halo: '#ffffff'
        },
        dark: {
            land: '#1a1d24',
            landWash: '#222833',
            park: '#1a2a22',
            wood: '#15241c',
            water: '#1e3a5f',
            waterway: '#2a5588',
            building: '#14171d',
            buildingLine: '#323842',
            road: '#2c3444',
            roadMinor: '#252b38',
            roadCasing: '#3d4a62',
            motorway: '#3a4e72',
            motorwayCasing: '#1e3a5f',
            path: '#2a3140',
            rail: '#3c4454',
            railDash: '#1a1d24',
            boundary: '#64748b',
            label: '#cbd5e1',
            labelStrong: '#e8eaed',
            labelMuted: '#9aa0a6',
            waterLabel: '#93c5fd',
            halo: 'rgba(26, 29, 36, 0.92)'
        }
    };

    var mapInstance = null;
    var activeTheme = null;
    var themeToken = 0;
    var styleSources = {};

    function isDarkMode() {
        return document.body.classList.contains('dark-mode');
    }

    function themeKey() {
        return isDarkMode() ? 'dark' : 'light';
    }

    function setPaint(layer, props) {
        if (!layer.paint) layer.paint = {};
        Object.keys(props).forEach(function (key) {
            layer.paint[key] = props[key];
        });
    }

    function themeStyle(style, dark) {
        var colors = dark ? PALETTES.dark : PALETTES.light;
        var layers = {};
        style.layers.forEach(function (layer) {
            layers[layer.id] = layer;
        });

        function paint(id, props) {
            if (layers[id]) setPaint(layers[id], props);
        }

        function paintEach(ids, props) {
            ids.forEach(function (id) {
                paint(id, props);
            });
        }

        function label(id, color) {
            paint(id, {
                'text-color': color,
                'text-halo-color': colors.halo
            });
        }

        paint('background', { 'background-color': colors.land });
        paint('park', { 'fill-color': colors.park });
        paint('landuse_park', { 'fill-color': colors.park });
        paint('landcover_wood', { 'fill-color': colors.wood });
        paint('landuse_residential', { 'fill-color': colors.landWash });
        paint('landcover_ice_shelf', { 'fill-color': colors.land });
        paint('landcover_glacier', { 'fill-color': colors.land });
        paint('water', { 'fill-color': colors.water });
        paint('waterway', { 'line-color': colors.waterway });
        paint('building', {
            'fill-color': colors.building,
            'fill-outline-color': colors.buildingLine
        });
        paintEach(['aeroway-taxiway', 'aeroway-runway-casing'], { 'line-color': colors.roadCasing });
        paint('aeroway-area', { 'fill-color': colors.road });
        paint('aeroway-runway', { 'line-color': colors.road });
        paint('road_area_pier', { 'fill-color': colors.land });
        paint('road_pier', { 'line-color': colors.land });
        paint('highway_path', { 'line-color': colors.path });
        paint('highway_minor', { 'line-color': colors.roadMinor });
        paintEach(['highway_major_casing', 'highway_major_subtle'], { 'line-color': colors.roadCasing });
        paint('highway_major_inner', { 'line-color': colors.road });
        paintEach([
            'highway_motorway_casing',
            'highway_motorway_subtle',
            'highway_motorway_bridge_casing',
            'tunnel_motorway_casing'
        ], { 'line-color': colors.motorwayCasing });
        paintEach([
            'highway_motorway_inner',
            'highway_motorway_bridge_inner',
            'tunnel_motorway_inner'
        ], { 'line-color': colors.motorway });
        paintEach(['railway_transit', 'railway_service', 'railway', 'railway_minor'], { 'line-color': colors.rail });
        paintEach([
            'railway_transit_dashline',
            'railway_service_dashline',
            'railway_dashline',
            'railway_minor_dashline'
        ], { 'line-color': colors.railDash });
        paintEach([
            'boundary_3',
            'boundary_2',
            'boundary_disputed',
            'boundary_state',
            'boundary_country_z0-4',
            'boundary_country_z5-'
        ], { 'line-color': colors.boundary });
        ['waterway_line_label', 'water_name_point_label', 'water_name_line_label', 'water_name'].forEach(function (id) {
            label(id, colors.waterLabel);
        });
        ['highway-name-path', 'highway_name_other'].forEach(function (id) {
            label(id, colors.labelMuted);
        });
        ['highway-name-minor', 'highway-name-major', 'highway_name_motorway', 'airport'].forEach(function (id) {
            label(id, colors.label);
        });
        [
            'label_other', 'label_village', 'label_town', 'label_state',
            'label_city', 'label_city_capital', 'label_country_3', 'label_country_2', 'label_country_1',
            'place_other', 'place_suburb', 'place_village', 'place_town', 'place_city',
            'place_city_large', 'place_state', 'place_country_other', 'place_country_minor', 'place_country_major'
        ].forEach(function (id) {
            label(id, colors.labelStrong);
        });

        return style;
    }

    function loadStyleSource(dark) {
        var key = dark ? 'dark' : 'light';
        if (!styleSources[key]) {
            styleSources[key] = fetch(BASE_STYLES[key]).then(function (response) {
                if (!response.ok) throw new Error('Map style failed');
                return response.json();
            });
        }
        return styleSources[key];
    }

    function loadThemedStyle(dark) {
        return loadStyleSource(dark).then(function (style) {
            return themeStyle(JSON.parse(JSON.stringify(style)), dark);
        });
    }

    function createMarkerElement() {
        var el = document.createElement('div');
        el.className = 'event-map-marker';
        el.innerHTML = '<div class="event-map-marker-pin"></div>';
        return el;
    }

    function applyTileTheme() {
        if (!mapInstance) return;
        var token = ++themeToken;
        var dark = isDarkMode();
        var key = dark ? 'dark' : 'light';
        if (activeTheme === key) return;
        loadThemedStyle(dark).then(function (style) {
            if (!mapInstance || token !== themeToken) return;
            activeTheme = key;
            mapInstance.setStyle(style);
        }).catch(function () {});
    }

    function hideMapWrap(mapEl) {
        var wrap = mapEl.closest('.event-location-map-wrap');
        if (wrap) {
            wrap.style.display = 'none';
        }
    }

    function initEventLocationMap() {
        var mapEl = document.getElementById('eventLocationMap');
        if (!mapEl || typeof maplibregl === 'undefined') return;

        var query = mapEl.dataset.location;
        if (!query) {
            hideMapWrap(mapEl);
            return;
        }

        var dark = isDarkMode();
        Promise.all([
            fetch(
                'https://nominatim.openstreetmap.org/search?format=json&q=' +
                encodeURIComponent(query) + '&limit=1&addressdetails=0',
                { headers: { 'Accept-Language': 'en' } }
            ).then(function (response) {
                if (!response.ok) throw new Error('Geocode failed');
                return response.json();
            }),
            loadThemedStyle(dark).catch(function () {
                return BASE_STYLES[dark ? 'dark' : 'light'];
            })
        ])
            .then(function (results) {
                var places = results[0];
                var style = results[1];
                if (!places.length) {
                    hideMapWrap(mapEl);
                    return;
                }

                var lat = parseFloat(places[0].lat);
                var lon = parseFloat(places[0].lon);
                activeTheme = dark ? 'dark' : 'light';

                mapInstance = new maplibregl.Map({
                    container: mapEl,
                    style: style,
                    center: [lon, lat],
                    zoom: 15,
                    maxZoom: 18,
                    scrollZoom: false,
                    dragRotate: false,
                    pitchWithRotate: false,
                    touchPitch: false,
                    attributionControl: true
                });

                mapInstance.addControl(
                    new maplibregl.NavigationControl({ showCompass: false }),
                    'top-left'
                );
                mapInstance.touchZoomRotate.disableRotation();

                new maplibregl.Marker({
                    element: createMarkerElement(),
                    anchor: 'center'
                })
                    .setLngLat([lon, lat])
                    .setPopup(new maplibregl.Popup({ offset: 12 }).setText(query))
                    .addTo(mapInstance);

                mapInstance.on('load', function () {
                    mapInstance.resize();
                });
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
