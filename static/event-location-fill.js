(function () {
    'use strict';

    var PHOTON = 'https://photon.komoot.io';
    var cityCenters = {};
    var userLocation = null;
    var locationRequest = null;
    var locationDenied = false;

    var STATE_BY_ABBR = {
        AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
        CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
        HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa', KS: 'Kansas',
        KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts',
        MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri', MT: 'Montana',
        NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico',
        NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma',
        OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
        SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont',
        VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming'
    };

    function cityOf(props) {
        return props.city || props.town || props.village || props.locality || props.district || '';
    }

    var ROAD_TYPES = {
        motorway: 1, trunk: 1, primary: 1, secondary: 1, tertiary: 1,
        unclassified: 1, residential: 1, living_street: 1, service: 1, road: 1
    };

    function streetName(props) {
        if (props.street) return props.street;
        if (ROAD_TYPES[props.osm_value] && props.name) return props.name;
        return '';
    }

    function streetOf(props) {
        var street = streetName(props);
        if (props.housenumber && street) return props.housenumber + ' ' + street;
        return street;
    }

    function stateName(value) {
        if (!value) return '';
        var trimmed = String(value).trim();
        return STATE_BY_ABBR[trimmed.toUpperCase()] || trimmed;
    }

    function setState(select, value) {
        if (!select || !value) return false;
        var wanted = stateName(value).toLowerCase();
        for (var i = 0; i < select.options.length; i++) {
            var option = select.options[i];
            var optionValue = (option.value || '').trim().toLowerCase();
            var optionText = (option.text || '').trim().toLowerCase();
            if (optionValue === wanted || optionText === wanted) {
                select.selectedIndex = i;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
        }
        return false;
    }

    function applyPlace(props, addressEl, cityEl, stateEl) {
        var street = streetOf(props);
        var city = cityOf(props);
        var filled = false;
        if (addressEl && street) {
            addressEl.value = street;
            filled = true;
        }
        if (cityEl && city) {
            cityEl.value = city;
            filled = true;
        }
        if (setState(stateEl, props.state)) {
            filled = true;
        }
        return filled;
    }

    function currentPosition() {
        if (!navigator.geolocation || locationDenied) {
            return Promise.reject(new Error('unsupported'));
        }
        if (userLocation) {
            return Promise.resolve(userLocation);
        }
        if (locationRequest) {
            return locationRequest;
        }
        locationRequest = new Promise(function (resolve, reject) {
            navigator.geolocation.getCurrentPosition(function (position) {
                userLocation = {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude
                };
                locationRequest = null;
                resolve(userLocation);
            }, function (error) {
                locationRequest = null;
                if (error && error.code === 1) locationDenied = true;
                reject(error);
            }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 });
        });
        return locationRequest;
    }

    function reverseLookup(lat, lon) {
        var url = PHOTON + '/reverse?lat=' + encodeURIComponent(lat) +
            '&lon=' + encodeURIComponent(lon) + '&lang=en';
        return fetch(url, { headers: { Accept: 'application/json' } })
            .then(function (response) {
                if (!response.ok) throw new Error('lookup failed');
                return response.json();
            })
            .then(function (data) {
                var features = (data && data.features) || [];
                var streetMatch = null;
                var fallback = null;
                features.forEach(function (feature) {
                    var props = feature.properties || {};
                    if (props.countrycode !== 'US') return;
                    if (!fallback) fallback = props;
                    if (!streetMatch && props.street) streetMatch = props;
                });
                var match = streetMatch || fallback;
                if (!match) throw new Error('no address');
                return match;
            });
    }

    function suggestionLabel(props) {
        var parts = [];
        var street = streetOf(props);
        var city = cityOf(props);
        if (street) parts.push(street);
        if (city) parts.push(city);
        if (props.state) parts.push(stateName(props.state));
        return parts.join(', ');
    }

    function bindUseLocation(button, addressEl, cityEl, stateEl) {
        if (!button || button.dataset.locationBound) return;
        button.dataset.locationBound = '1';
        var idleHtml = button.innerHTML;

        button.addEventListener('click', function (event) {
            event.preventDefault();
            if (!navigator.geolocation) {
                window.alert('Location is not available in this browser.');
                return;
            }
            userLocation = null;
            locationRequest = null;
            locationDenied = false;
            button.disabled = true;
            button.innerHTML = '<i class="material-icons">hourglass_empty</i>';
            if (addressEl._fursvpLocationStatus) addressEl._fursvpLocationStatus.show();
            currentPosition()
                .then(function (coords) {
                    return reverseLookup(coords.lat, coords.lon);
                })
                .then(function (props) {
                    if (!applyPlace(props, addressEl, cityEl, stateEl)) {
                        throw new Error('empty');
                    }
                })
                .catch(function (error) {
                    if (error && error.code) {
                        window.alert('Allow location access, then try again.');
                    } else {
                        window.alert('Could not look up your current location. Try again.');
                    }
                })
                .then(function () {
                    button.disabled = false;
                    button.innerHTML = idleHtml;
                    if (addressEl._fursvpLocationStatus) addressEl._fursvpLocationStatus.hide();
                });
        });
    }

    function bindAutocomplete(addressEl, cityEl, stateEl) {
        if (!addressEl || addressEl.dataset.locationAutocomplete) return;
        addressEl.dataset.locationAutocomplete = '1';

        var container = document.createElement('div');
        container.className = 'autocomplete-container';
        container.setAttribute('role', 'listbox');
        var anchor = addressEl.closest('.auth-field') || addressEl.parentElement;
        if (anchor) {
            anchor.style.position = 'relative';
            anchor.appendChild(container);
        }

        var searchTimer = null;
        var activeController = null;

        function hide() {
            container.style.display = 'none';
            container.innerHTML = '';
            if (anchor) anchor.style.zIndex = '';
        }

        function show() {
            if (anchor) anchor.style.zIndex = '20';
            container.style.display = 'block';
        }

        function showStatus() {
            container.innerHTML = '';
            var status = document.createElement('div');
            status.className = 'autocomplete-status';
            status.setAttribute('role', 'status');
            var icon = document.createElement('i');
            icon.className = 'material-icons spin';
            icon.setAttribute('aria-hidden', 'true');
            icon.textContent = 'autorenew';
            status.appendChild(icon);
            status.appendChild(document.createTextNode('Finding the best match\u2026'));
            container.appendChild(status);
            show();
        }

        addressEl._fursvpLocationStatus = {
            show: showStatus,
            hide: hide
        };

        function activeItem() {
            return container.querySelector('.autocomplete-suggestion.active');
        }

        function moveActive(delta) {
            var items = container.querySelectorAll('.autocomplete-suggestion');
            if (!items.length) return;
            var current = activeItem();
            var index = Array.prototype.indexOf.call(items, current);
            var next = Math.max(0, Math.min(items.length - 1, index + delta));
            if (current) current.classList.remove('active');
            items[next].classList.add('active');
            items[next].scrollIntoView({ block: 'nearest' });
        }

        function lookupCityCenter(city, state) {
            var key = (city + '|' + state).toLowerCase();
            if (Object.prototype.hasOwnProperty.call(cityCenters, key)) {
                return Promise.resolve(cityCenters[key]);
            }
            var url = PHOTON + '/api/?q=' + encodeURIComponent((city + ' ' + state).trim()) +
                '&limit=5&lang=en';
            return fetch(url, { headers: { Accept: 'application/json' } })
                .then(function (response) {
                    if (!response.ok) throw new Error('city lookup failed');
                    return response.json();
                })
                .then(function (data) {
                    var features = (data && data.features) || [];
                    var match = null;
                    features.forEach(function (feature) {
                        if (match) return;
                        var props = feature.properties || {};
                        var name = (props.name || props.city || '').toLowerCase();
                        var sameState = !state || (props.state || '').toLowerCase() === state.toLowerCase();
                        if (name === city.toLowerCase() && sameState && feature.geometry) {
                            match = feature;
                        }
                    });
                    if (!match) return null;
                    var coords = match.geometry.coordinates || [];
                    cityCenters[key] = { lon: coords[0], lat: coords[1] };
                    return cityCenters[key];
                })
                .catch(function () {
                    return null;
                });
        }

        function search(query) {
            showStatus();
            if (activeController) activeController.abort();
            activeController = new AbortController();
            var controller = activeController;
            var city = cityEl && cityEl.value ? cityEl.value.trim() : '';
            var state = stateEl && stateEl.value ? stateEl.value.trim() : '';
            var typedStreet = query.replace(/^\d+\s*/, '').split(',')[0].trim();
            var centerPromise = city ? lookupCityCenter(city, state) : Promise.resolve(userLocation);

            centerPromise.then(function (center) {
                if (addressEl.value.trim() !== query) return null;
                var q = typedStreet || query;
                var url = PHOTON + '/api/?q=' + encodeURIComponent(q) + '&limit=8&lang=en';
                if (center && center.lat != null && center.lon != null) {
                    var span = city ? 0.08 : 0.3;
                    url += '&lat=' + encodeURIComponent(center.lat) +
                        '&lon=' + encodeURIComponent(center.lon) +
                        '&bbox=' + (center.lon - span) + ',' + (center.lat - span) + ',' +
                        (center.lon + span) + ',' + (center.lat + span);
                }
                return fetch(url, {
                    headers: { Accept: 'application/json' },
                    signal: controller.signal
                });
            })
                .then(function (response) {
                    if (!response) return null;
                    if (!response.ok) throw new Error('search failed');
                    return response.json();
                })
                .then(function (data) {
                    if (!data || addressEl.value.trim() !== query) return;
                    container.innerHTML = '';
                    var city = cityEl && cityEl.value ? cityEl.value.trim().toLowerCase() : '';
                    var typedNumber = (query.match(/^(\d+)\b/) || [])[1] || '';
                    var typedStreet = query.replace(/^\d+\s*/, '').split(',')[0].trim().toLowerCase();
                    var features = ((data && data.features) || []).filter(function (feature) {
                        var props = feature.properties || {};
                        return props.countrycode === 'US' && streetOf(props);
                    });
                    features.sort(function (a, b) {
                        function rank(feature) {
                            var props = feature.properties || {};
                            var score = 0;
                            if (city && cityOf(props).toLowerCase() === city) score += 4;
                            if (typedStreet && streetName(props).toLowerCase().indexOf(typedStreet) !== -1) score += 2;
                            if (typedNumber && props.housenumber === typedNumber) score += 1;
                            return score;
                        }
                        return rank(b) - rank(a);
                    });
                    var places = features.map(function (feature) {
                        return feature.properties || {};
                    });
                    if (typedNumber && typedStreet) {
                        var streetMatch = null;
                        places.forEach(function (props) {
                            if (streetMatch) return;
                            var sameCity = !city || cityOf(props).toLowerCase() === city;
                            if (sameCity && streetName(props).toLowerCase().indexOf(typedStreet) !== -1) {
                                streetMatch = props;
                            }
                        });
                        if (streetMatch && streetMatch.housenumber !== typedNumber) {
                            places.unshift(Object.assign({}, streetMatch, { housenumber: typedNumber }));
                        }
                    }
                    var seen = {};
                    places = places.filter(function (props) {
                        var label = suggestionLabel(props);
                        if (!label || seen[label]) return false;
                        seen[label] = true;
                        return true;
                    }).slice(0, 6);
                    if (!places.length) {
                        hide();
                        return;
                    }
                    places.forEach(function (props, index) {
                        var item = document.createElement('div');
                        item.className = 'autocomplete-suggestion' + (index === 0 ? ' active' : '');
                        item.setAttribute('role', 'option');
                        item.textContent = suggestionLabel(props);
                        item.addEventListener('mousedown', function (event) {
                            event.preventDefault();
                            applyPlace(props, addressEl, cityEl, stateEl);
                            hide();
                        });
                        container.appendChild(item);
                    });
                    show();
                })
                .catch(function (error) {
                    if (error && error.name === 'AbortError') return;
                    hide();
                });
        }

        addressEl.addEventListener('input', function () {
            clearTimeout(searchTimer);
            var query = addressEl.value.trim();
            if (query.length < 3) {
                if (activeController) activeController.abort();
                hide();
                return;
            }
            showStatus();
            searchTimer = setTimeout(function () {
                if (addressEl.value.trim() === query) search(query);
            }, 350);
        });

        addressEl.addEventListener('focus', function () {
            currentPosition().catch(function () {});
        });

        addressEl.addEventListener('keydown', function (event) {
            var open = container.style.display === 'block';
            if (event.key === 'Enter' && open) {
                event.preventDefault();
                var current = activeItem();
                if (current) current.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
                return;
            }
            if (!open) {
                if (event.key === 'Enter') event.preventDefault();
                return;
            }
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                moveActive(1);
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                moveActive(-1);
            } else if (event.key === 'Escape') {
                event.preventDefault();
                hide();
            }
        });

        document.addEventListener('click', function (event) {
            if (event.target === addressEl || container.contains(event.target)) return;
            hide();
        });
    }

    function init() {
        var addressEl = document.getElementById('id_address');
        var cityEl = document.getElementById('id_city');
        var stateEl = document.getElementById('id_state');
        if (!addressEl) return;

        bindAutocomplete(addressEl, cityEl, stateEl);
        ['locationButton', 'useLocationBtn'].forEach(function (id) {
            bindUseLocation(document.getElementById(id), addressEl, cityEl, stateEl);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
