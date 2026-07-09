import ipaddress

TRUSTED_PROXY_NETWORKS = (
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
)

SESSION_CLIENT_IP_KEY = 'client_public_ip'


def is_trusted_proxy(ip):
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in network for network in TRUSTED_PROXY_NETWORKS)


def parse_public_ip(value):
    if not value:
        return None
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if ip.is_global:
        return str(ip)
    return None


def _pick_client_ip(candidates):
    for candidate in candidates:
        ip = parse_public_ip(candidate)
        if ip:
            return ip
    return None


def _client_ip_from_proxy_headers(request):
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        client_ip = _pick_client_ip([cf_ip])
        if client_ip:
            return client_ip

    real_ip = request.META.get('HTTP_X_REAL_IP')
    if real_ip:
        client_ip = _pick_client_ip([real_ip])
        if client_ip:
            return client_ip

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        parts = [part.strip() for part in x_forwarded_for.split(',') if part.strip()]
        client_ip = _pick_client_ip(parts)
        if client_ip:
            return client_ip

    return None


def _client_ip_from_session(request):
    if not hasattr(request, 'session'):
        return None
    return parse_public_ip(request.session.get(SESSION_CLIENT_IP_KEY))


def store_client_ip_in_session(request, ip_value):
    client_ip = parse_public_ip(ip_value)
    if not client_ip:
        return False
    request.session[SESSION_CLIENT_IP_KEY] = client_ip
    return True


def get_client_ip(request):
    """Resolve the visitor IP for audit logs and captcha checks."""
    remote_addr = request.META.get('REMOTE_ADDR')

    if is_trusted_proxy(remote_addr):
        proxy_ip = _client_ip_from_proxy_headers(request)
        if proxy_ip:
            return proxy_ip

        session_ip = _client_ip_from_session(request)
        if session_ip:
            return session_ip

    return remote_addr
