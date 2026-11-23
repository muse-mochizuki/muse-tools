#!/usr/bin/env python3
"""HTTP CONNECT relay for SSH ProxyCommand over the tailnet tunnel proxy.
Usage: tsconnect.py <host> <port>  (proxy taken from HTTPS_PROXY, port forced to 3130)"""
import base64
import os
import select
import socket
import sys
import urllib.parse


def main():
    host, port = sys.argv[1], int(sys.argv[2])
    proxy = urllib.parse.urlparse(os.environ["HTTPS_PROXY"])
    s = socket.create_connection((proxy.hostname, 3130), timeout=30)
    auth = base64.b64encode(f"{proxy.username}:{proxy.password}".encode()).decode()
    req = (
        f"CONNECT {host}:{port} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Proxy-Authorization: Basic {auth}\r\n\r\n"
    )
    s.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = s.recv(4096)
        if not chunk:
            sys.exit(1)
        resp += chunk
    if b" 200" not in resp.split(b"\r\n")[0]:
        sys.stderr.write("CONNECT failed: " + resp.decode(errors="replace")[:300])
        sys.exit(1)
    s.setblocking(False)
    stdin = sys.stdin.buffer
    while True:
        r, _, _ = select.select([s, stdin], [], [], 120)
        if not r:
            break
        for f in r:
            if f is s:
                data = s.recv(65536)
                if not data:
                    return
                os.write(1, data)
            else:
                data = os.read(0, 65536)
                if not data:
                    try:
                        s.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass
                    return
                s.sendall(data)


if __name__ == "__main__":
    main()
