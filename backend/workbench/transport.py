"""Explicit IP-only campus deployment, never an implicit HTTPS downgrade."""
from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

NETWORKS = tuple(ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8'))


def lan_url(value, *, loopback=False):
    parsed = urlsplit(value)
    try:
        address = ip_address(parsed.hostname or '')
    except ValueError:
        return False
    return (parsed.scheme == 'http' and not parsed.username and not parsed.password
            and (address.is_loopback if loopback else any(address in n for n in NETWORKS)))
