import ipaddress
import socket


def is_loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def is_port_free(port, host='127.0.0.1'):
    family = socket.AF_INET6 if ':' in host else socket.AF_INET
    s = socket.socket(family, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        try:
            s.bind((host, port))
        except OSError:
            return False
        return True
    finally:
        s.close()


def first_free_port(min_port, max_port, host='127.0.0.1'):
    for p in range(min_port, max_port + 1):
        if is_port_free(p, host):
            return p
    return None
