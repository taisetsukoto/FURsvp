// This is used to store the client's IP address in the audit logs. Blocking this script could lead to a lack of audit trail and potential abuse.
    if (window.sessionStorage.getItem('fursvpClientIpStored') === '1') {
        return;
    }

    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? decodeURIComponent(match[2]) : '';
    }

    fetch('https://api.ipify.org?format=json', { cache: 'no-store' })
        .then(function (response) { return response.json(); })
        .then(function (data) {
            if (!data || !data.ip) {
                return null;
            }

            var body = new URLSearchParams();
            body.set('ip', data.ip);

            var csrfToken = getCookie('csrftoken');
            if (csrfToken) {
                body.set('csrfmiddlewaretoken', csrfToken);
            }

            return fetch('/users/client-ip/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken || ''
                },
                body: body.toString(),
                credentials: 'same-origin'
            });
        })
        .then(function (response) {
            if (response && response.ok) {
                window.sessionStorage.setItem('fursvpClientIpStored', '1');
            }
        })
        .catch(function () {});
})();
