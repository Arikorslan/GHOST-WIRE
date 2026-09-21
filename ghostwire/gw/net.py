"""GHOSTWIRE transport layer.

* TCP framing + secure link (WiFi / wired — anything with IP)
* Node discovery sweep (TCP connect scan + GW1 probe handshake)
* Node server (listens for uplinks and reconnaissance probes)
* Bluetooth RFCOMM transport (same secure link over a raw RFCOMM socket)
"""

from __future__ import annotations

import ipaddress
import json
import socket
import struct
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from .crypto import (
    MAX_FRAME,
    PROTOCOL,
    CipherState,
    Handshake,
    Identity,
    SecurityError,
    b64d,
    b64e,
)

MAGIC_PROBE = b"GW1PROBE"
MAGIC_PONG = b"GW1PONG"


class LinkClosed(Exception):
    pass


class SecureLink:
    """A single encrypted channel over a connected stream socket."""

    def __init__(self, sock, identity: Identity, role: str, status=None):
        self.sock = sock
        self.identity = identity
        self.role = role
        self.status = status or (lambda s: None)
        self.hs = Handshake(identity, role)
        self.tx: CipherState | None = None
        self.rx: CipherState | None = None
        self.session_id = ""
        self.peer_fingerprint = ""
        self.alive = False
        self.on_message = None
        self.on_close = None
        self._buf = b""
        self._wlock = threading.Lock()

    # ------------------------------------------------ framed I/O
    def _recv_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            try:
                chunk = self.sock.recv(4096)
            except OSError as exc:
                raise LinkClosed() from exc
            if not chunk:
                raise LinkClosed()
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _read_frame(self) -> bytes:
        (length,) = struct.unpack(">I", self._recv_exact(4))
        if length > MAX_FRAME:
            raise SecurityError("oversized frame")
        return self._recv_exact(length)

    def _write_frame(self, data: bytes) -> None:
        with self._wlock:
            self.sock.sendall(struct.pack(">I", len(data)) + data)

    def _send_json(self, obj: dict) -> None:
        self._write_frame(json.dumps(obj).encode())

    def _recv_json(self) -> dict:
        return json.loads(self._read_frame().decode())

    def _send_enc(self, obj: dict) -> None:
        self._write_frame(self.tx.seal(json.dumps(obj).encode()))

    def _recv_enc(self) -> dict:
        return json.loads(self.rx.open(self._read_frame()).decode())

    # ------------------------------------------------ handshake
    def _setup_chains(self) -> None:
        root = self.hs.root
        if self.role == "client":
            self.tx, self.rx = CipherState(root, b"c2s"), CipherState(root, b"s2c")
        else:
            self.tx, self.rx = CipherState(root, b"s2c"), CipherState(root, b"c2s")
        self.session_id = self.hs.session_id.hex().upper()
        self.peer_fingerprint = Identity.fingerprint_of(self.hs.peer_id)

    def _confirm_obj(self) -> dict:
        return {"t": "confirm", "role": self.role,
                "mac": b64e(self.hs.confirm_mac(self.role))}

    def handshake_client(self) -> None:
        self.status("GENERATING EPHEMERAL X25519 KEYPAIR")
        mine = self.hs.hello()
        self._send_json(mine)
        self.status("HELLO DISPATCHED - AWAITING REMOTE NODE")
        peer = self._recv_json()
        self.status("PEER HELLO RECEIVED - VERIFYING ED25519 SIGNATURE")
        # The responder's signature binds our canonical hello (transcript).
        self.hs.consume_hello(peer, bind=json.dumps(mine, sort_keys=True))
        self.hs.derive()
        self._setup_chains()
        self.status("SIGNATURE VALID - ECDH SECRET DERIVED - RATCHET ONLINE")
        self._send_enc(self._confirm_obj())
        conf = self._recv_enc()
        if conf.get("t") != "confirm":
            raise SecurityError("expected key confirmation")
        self.hs.check_confirm("server", conf["mac"])
        self.status("KEY CONFIRMATION MAC VERIFIED")
        self.status("SECURE LINK ESTABLISHED")
        self.alive = True

    def handshake_server(self) -> None:
        self.status("INBOUND HELLO - VERIFYING ED25519 SIGNATURE")
        peer = self._recv_json()
        # The initiator signed with an empty bind.
        self.hs.consume_hello(peer, bind="")
        self.status("SIGNATURE VALID - RESPONDING WITH BOUND HELLO")
        # Our hello cryptographically binds the initiator's hello.
        self._send_json(self.hs.hello(bind=json.dumps(peer, sort_keys=True)))
        self.hs.derive()
        self._setup_chains()
        self.status("ECDH SECRET DERIVED - RATCHET ONLINE")
        conf = self._recv_enc()
        if conf.get("t") != "confirm":
            raise SecurityError("expected key confirmation")
        self.hs.check_confirm("client", conf["mac"])
        self._send_enc(self._confirm_obj())
        self.status("KEY CONFIRMATION MAC VERIFIED")
        self.status("SECURE LINK ESTABLISHED")
        self.alive = True

    # ------------------------------------------------ traffic
    def start(self) -> None:
        threading.Thread(target=self._reader, daemon=True,
                         name="gw-reader").start()

    def _reader(self) -> None:
        try:
            while self.alive:
                obj = self._recv_enc()
                t = obj.get("t")
                if t == "ping":
                    self._send_enc({"t": "pong"})
                    continue
                if t == "pong":
                    continue
                if self.on_message:
                    self.on_message(obj)
        except Exception:
            pass
        finally:
            was_alive = self.alive
            self.alive = False
            if was_alive and self.on_close:
                try:
                    self.on_close()
                except Exception:
                    pass

    def send_chat(self, text: str, ttl: int) -> str:
        mid = uuid.uuid4().hex[:12]
        self._send_enc({"t": "msg", "id": mid, "text": text,
                        "ttl": ttl, "ts": time.time()})
        return mid

    def send_control(self, kind: str, mid: str) -> None:
        self._send_enc({"t": kind, "id": mid})

    def close(self) -> None:
        self.alive = False
        # shutdown() BEFORE close(): on Linux a close() while another
        # thread is blocked in recv() does not tear the connection down
        # (the blocked call holds the file description, so no FIN is sent
        # and a displaced peer would never see EOF).  shutdown wakes the
        # blocked reader and emits the FIN to the peer.
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


# ----------------------------------------------------------------------
# Node server (TCP)
# ----------------------------------------------------------------------

class NodeServer:
    """GW1 listener with OPERATOR-GATED, strictly peer-to-peer access.

    The node hosts ONE secure link at a time (two parties, no more).
    Every inbound connection that is not a reconnaissance probe is
    parked at a request gate: the operator is shown
    "<ip:port> REQUESTS A CHAT" and must ACKNOWLEDGE before the GW1
    handshake may even begin; REJECT (or a 60 s timeout) closes the
    socket.  Acknowledging while a peer is connected drops that peer
    first — a third device can therefore never silently displace an
    active client."""

    REQUEST_TIMEOUT = 60.0   # operator decision window (seconds)

    def __init__(self, identity: Identity, on_link=None, on_request=None,
                 status=None):
        self.identity = identity
        self.on_link = on_link
        self.on_request = on_request
        self.status = status or (lambda s: None)
        self.stealth = False
        self.listening = False
        self.bound = None
        self.sock = None
        self._thread = None
        self.link: SecureLink | None = None
        self._lock = threading.Lock()
        self._gates: dict[int, dict] = {}
        self._gate_seq = 0

    # -- operator gate -------------------------------------------------
    def respond(self, gate_id: int, ok: bool) -> None:
        """Resolve a pending connection request (UI ACKNOWLEDGE/REJECT)."""
        gate = self._gates.get(gate_id)
        if gate:
            gate["ok"] = bool(ok)
            gate["event"].set()

    def _hold_for_decision(self, label: str) -> bool:
        with self._lock:
            self._gate_seq += 1
            gid = self._gate_seq
            gate = {"event": threading.Event(), "ok": False}
            self._gates[gid] = gate
        try:
            if self.on_request:
                self.on_request(label, gid)
            decided = gate["event"].wait(self.REQUEST_TIMEOUT)
        finally:
            self._gates.pop(gid, None)
        if not decided:
            self.status(f"REQUEST EXPIRED ({label})")
        elif not gate["ok"]:
            self.status(f"CONNECTION REJECTED ({label})")
        return bool(decided and gate["ok"])

    # -- listener -------------------------------------------------------
    def start(self, host: str, port: int) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(8)
        self.bound = (host, port)
        self.listening = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True,
                                        name="gw-node")
        self._thread.start()

    def _accept_loop(self) -> None:
        while self.listening:
            try:
                conn, addr = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn, addr),
                             daemon=True).start()

    def _handle(self, conn, addr) -> None:
        conn.settimeout(15)
        try:
            head = conn.recv(8, socket.MSG_PEEK)
        except OSError:
            conn.close()
            return
        if head.startswith(MAGIC_PROBE):
            # Reconnaissance probe.  Stealth nodes stay silent.
            try:
                conn.recv(64)
                if not self.stealth:
                    fp = self.identity.fingerprint.replace(" ", "")
                    conn.sendall(MAGIC_PONG + b" " + fp.encode())
            except OSError:
                pass
            conn.close()
            return
        # -- everything else must pass the operator gate first
        label = f"{addr[0]}:{addr[1]}"
        self.status(f"INBOUND REQUEST ({label})")
        if not self._hold_for_decision(label):
            conn.close()
            return
        # Acknowledged: peer-to-peer means one live peer — drop the old.
        with self._lock:
            old = self.link
            self.link = None
        if old is not None and old.alive:
            old.close()
        link = SecureLink(conn, self.identity, "server", status=self.status)
        try:
            link.handshake_server()
        except (SecurityError, LinkClosed, OSError, ValueError) as exc:
            self.status(f"HANDSHAKE REJECTED ({exc.__class__.__name__})")
            conn.close()
            return
        conn.settimeout(None)
        with self._lock:
            self.link = link
        if self.on_link:
            self.on_link(link, addr)
        ui_close = link.on_close

        def _closed():
            with self._lock:
                if self.link is link:
                    self.link = None
            if ui_close:
                ui_close()

        link.on_close = _closed
        link.start()

    def stop(self) -> None:
        self.listening = False
        with self._lock:
            for gate in self._gates.values():
                gate["event"].set()      # fail parked requests fast
            link = self.link
            self.link = None
        if link:
            try:
                link.close()
            except Exception:
                pass
        try:
            self.sock.close()
        except OSError:
            pass


# ----------------------------------------------------------------------
# Discovery sweep
# ----------------------------------------------------------------------

def probe_host(ip: str, port: int, connect_timeout: float = 0.35,
               probe_timeout: float = 1.0):
    """Returns ("node", fingerprint) | ("open", None) | None."""
    try:
        s = socket.create_connection((ip, port), timeout=connect_timeout)
    except OSError:
        return None
    try:
        s.settimeout(probe_timeout)
        s.sendall(MAGIC_PROBE)
        data = s.recv(256)
        if data.startswith(MAGIC_PONG):
            fp = data[len(MAGIC_PONG):].strip().decode(errors="ignore")
            fp = " ".join(fp[i:i + 4] for i in range(0, len(fp), 4))
            return ("node", fp)
    except OSError:
        pass
    finally:
        try:
            s.close()
        except OSError:
            pass
    return ("open", None)


def expand_targets(spec: str) -> list[str]:
    """Accepts CIDR ('192.168.1.0/24'), single IP, or comma list."""
    hosts = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "/" in part:
            net = ipaddress.ip_network(part, strict=False)
            if net.num_addresses > 1024:
                raise ValueError("sweep limited to 1024 hosts")
            hosts += [str(h) for h in net.hosts()] or [str(net.network_address)]
        else:
            hosts.append(str(ipaddress.ip_address(part)))
    return hosts


def sweep(targets, port: int, on_result, on_progress, stop_flag,
          workers: int = 64) -> None:
    total = len(targets)
    done = 0
    lock = threading.Lock()

    def work(ip: str) -> None:
        nonlocal done
        if stop_flag():
            return
        res = probe_host(ip, port)
        with lock:
            done += 1
            cur = done
        on_progress(cur, total)
        if res:
            on_result(ip, res[0], res[1])

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, targets))


def local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


# ----------------------------------------------------------------------
# Bluetooth RFCOMM transport
# ----------------------------------------------------------------------

def bluetooth_available() -> bool:
    if not hasattr(socket, "AF_BLUETOOTH") or \
            not hasattr(socket, "BTPROTO_RFCOMM"):
        return False
    try:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                          socket.BTPROTO_RFCOMM)
        s.close()
        return True
    except OSError:
        return False


class BluetoothNode:
    """RFCOMM listener running the identical GW1 secure-link protocol,
    with the same single-peer, operator-gated policy as NodeServer."""

    REQUEST_TIMEOUT = 60.0

    def __init__(self, identity: Identity, on_link=None, on_request=None,
                 status=None):
        self.identity = identity
        self.on_link = on_link
        self.on_request = on_request
        self.status = status or (lambda s: None)
        self.listening = False
        self.sock = None
        self.link: SecureLink | None = None
        self._lock = threading.Lock()
        self._gates: dict[int, dict] = {}
        self._gate_seq = 0

    def respond(self, gate_id: int, ok: bool) -> None:
        gate = self._gates.get(gate_id)
        if gate:
            gate["ok"] = bool(ok)
            gate["event"].set()

    def _hold_for_decision(self, label: str) -> bool:
        with self._lock:
            self._gate_seq += 1
            gid = self._gate_seq
            gate = {"event": threading.Event(), "ok": False}
            self._gates[gid] = gate
        try:
            if self.on_request:
                self.on_request(label, gid)
            decided = gate["event"].wait(self.REQUEST_TIMEOUT)
        finally:
            self._gates.pop(gid, None)
        return bool(decided and gate["ok"])

    def start(self, bdaddr: str = "00:00:00:00:00:00", channel: int = 7):
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                                  socket.BTPROTO_RFCOMM)
        self.sock.bind((bdaddr, channel))
        self.sock.listen(4)
        self.listening = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while self.listening:
            try:
                conn, addr = self.sock.accept()
            except OSError:
                break
            label = str(addr[0]) if isinstance(addr, tuple) else str(addr)
            if not self._hold_for_decision(label):
                conn.close()
                continue
            with self._lock:
                old = self.link
                self.link = None
            if old is not None and old.alive:
                old.close()
            link = SecureLink(conn, self.identity, "server",
                              status=self.status)
            try:
                link.handshake_server()
            except Exception:
                conn.close()
                continue
            with self._lock:
                self.link = link
            if self.on_link:
                self.on_link(link, addr)
            ui_close = link.on_close

            def _closed(l=link, c=ui_close):
                with self._lock:
                    if self.link is l:
                        self.link = None
                if c:
                    c()

            link.on_close = _closed
            link.start()

    def stop(self):
        self.listening = False
        with self._lock:
            for gate in self._gates.values():
                gate["event"].set()
            link = self.link
            self.link = None
        if link:
            try:
                link.close()
            except Exception:
                pass
        try:
            self.sock.close()
        except (OSError, AttributeError):
            pass


def bluetooth_connect(identity: Identity, bdaddr: str, channel: int = 7,
                      status=None, timeout: float = 10.0) -> SecureLink:
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                          socket.BTPROTO_RFCOMM)
    sock.settimeout(timeout)
    sock.connect((bdaddr, channel))
    link = SecureLink(sock, identity, "client", status=status)
    link.handshake_client()
    sock.settimeout(None)
    return link


# ----------------------------------------------------------------------
# WAN relay client (pairs with relay_server.py)
# ----------------------------------------------------------------------

def relay_connect(identity: Identity, host: str, port: int, status=None,
                  timeout: float = 120.0) -> SecureLink:
    """Dial a GHOSTWIRE WAN relay and complete the GW1 handshake through
    it.  The relay assigns seats once two devices are paired: the first
    dialer receives b"S" and takes the server role, the second b"C" and
    initiates.  The relay only ever sees ciphertext — keys are derived
    end-to-end by the GW1 handshake itself."""
    st = status or (lambda s: None)
    sock = socket.create_connection((host, port), timeout=10)
    sock.settimeout(timeout)
    st("RELAY DIALED - WAITING FOR PEER (SEAT ASSIGNMENT)")
    seat = sock.recv(1)
    if seat not in (b"S", b"C"):
        sock.close()
        raise SecurityError("relay seat assignment invalid")
    role = "server" if seat == b"S" else "client"
    st(f"RELAY SEAT {role.upper()} - HANDSHAKE THROUGH RELAY")
    link = SecureLink(sock, identity, role, status=st)
    if role == "server":
        link.handshake_server()
    else:
        link.handshake_client()
    sock.settimeout(None)
    return link
