#!/usr/bin/env python3
"""GHOSTWIRE WAN relay — opaque byte bridge for two-party GW1 sessions.

Run this on any host both devices can reach (VPS, home server):

    python3 relay_server.py --host 0.0.0.0 --port 9999

Each device then dials this host:port from the app's connect screen
with the WAN RELAY transport selected.  The relay pairs dialers two at
a time, tells the first "you are the server seat" (b"S") and the
second "you are the client seat" (b"C"), then pipes bytes between
them until either side hangs up.

BLIND BY CONSTRUCTION: the relay performs no GW1 parsing and holds no
keys — hellos, confirmations and every message frame cross it as
opaque ciphertext, so it can neither read nor forge traffic.  It
observes only metadata (addresses, pairing times, byte counts).
Reconnaissance probes (GW1PROBE) are closed silently: the relay has
no identity to reveal.
"""
from __future__ import annotations

import argparse
import socket
import threading
import time

MAGIC_PROBE = b"GW1PROBE"


class Relay:
    def __init__(self, host: str, port: int, max_pairs: int = 16,
                 quiet: bool = False):
        self.host = host
        self.port = port
        self.max_pairs = max_pairs
        self.quiet = quiet
        self._waiter: socket.socket | None = None
        self._lock = threading.Lock()
        self._pairs = 0
        self.sock = None

    def log(self, *a) -> None:
        if not self.quiet:
            print("[relay]", *a, flush=True)

    def start(self) -> None:
        self._bind()
        self._accept_loop()

    def _bind(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self.log(f"listening on {self.host}:{self.port} "
                 f"(max {self.max_pairs} concurrent pairs)")

    def _accept_loop(self) -> None:
        while True:
            try:
                conn, addr = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._on_conn, args=(conn, addr),
                             daemon=True).start()

    def start_background(self) -> threading.Thread:
        self._bind()
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    # -------------------------------------------------------------- #
    def _on_conn(self, conn: socket.socket, addr) -> None:
        label = f"{addr[0]}:{addr[1]}"
        # Recon probes announce themselves immediately; real dialers stay
        # silent until they receive a seat byte.  So a short peek that
        # TIMES OUT simply means "dialer" — keep it, don't drop it.
        conn.settimeout(1.5)
        try:
            head = conn.recv(8, socket.MSG_PEEK)
        except socket.timeout:
            head = b""          # silent dialer -> proceed to pairing
        except OSError:
            conn.close()
            return
        if head.startswith(MAGIC_PROBE):
            # No identity here; probes get silence.
            conn.close()
            return
        if head == b"":
            pass                # timeout path, treat as dialer
        conn.settimeout(None)
        partner = None
        with self._lock:
            if self._waiter is not None and self._pairs < self.max_pairs:
                partner = self._waiter
                self._waiter = None
                self._pairs += 1
            elif self._pairs < self.max_pairs:
                self._waiter = conn
        if partner is None:
            if self._waiter is conn:
                conn.settimeout(300)   # parked seats expire after 5 min
                self.log(f"{label} parked, waiting for peer")
                return  # the next dialer's thread resumes this socket
            self.log(f"{label} refused (pair limit)")
            conn.close()
            return
        self.log(f"pairing {label} with established peer")
        try:
            partner.settimeout(None)
            partner.sendall(b"S")          # first dialer: server seat
            conn.sendall(b"C")            # second dialer: client seat
        except OSError:
            for s in (conn, partner):
                try:
                    s.close()
                except OSError:
                    pass
            with self._lock:
                self._pairs -= 1
            return
        threading.Thread(target=self._pipe, args=(partner, conn, label),
                         daemon=True).start()
        threading.Thread(target=self._pipe, args=(conn, partner, label),
                         daemon=True).start()

    def _pipe(self, src: socket.socket, dst: socket.socket, label) -> None:
        moved = 0
        try:
            while True:
                chunk = src.recv(65536)
                if not chunk:
                    break
                moved += len(chunk)
                dst.sendall(chunk)
        except OSError:
            pass
        finally:
            for s in (src, dst):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    s.close()
                except OSError:
                    pass
            with self._lock:
                self._pairs -= 1
            self.log(f"pair {label} closed after {moved} bytes one-way")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="GHOSTWIRE opaque WAN relay (blind byte bridge)")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9999)
    ap.add_argument("--max-pairs", type=int, default=16)
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()
    try:
        Relay(args.host, args.port, args.max_pairs, args.quiet).start()
    except KeyboardInterrupt:
        print("\n[relay] standing down")


if __name__ == "__main__":
    main()
