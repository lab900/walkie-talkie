#!/usr/bin/env python3
"""A fake ElevenLabs Scribe for the harness (2026-09-27): the realtime socket the live caption
speaks (`ElevenLabsLive.swift`) and the batch upload (`ElevenLabsSource.transcribe`), on one local
port, so the live-caption cases stop spending the month's credits (26 Sep: 4 561 of 10 000 on the
host suite alone). Victor: *"poti emula daca vrei apiul lor de streaming pt testele de live
subtitles"*.

    python3 fake_scribe.py --selftest [--wav PATH] [--fast]   # talks to itself, no app needed
    python3 fake_scribe.py [--port N]                          # serve until ^C

**Standard library only, a hand-rolled RFC 6455 server** — not `websockets`: the host has 16.0,
but the lab guest's `/usr/bin/python3` 3.9 has only numpy/scipy/sounddevice, and the harness runs
there too. Python 3.9 syntax throughout.

The app is pointed at it through `~/.walkie-talkie/elevenlabs.env` (`WT_ELEVEN_LIVE_URL`,
`WT_ELEVEN_BATCH_URL`), which the harness writes and removes (`harness.fake_env`); the app re-reads
that file at every engine pick, so no relaunch is needed.

**Protocol, as `ElevenLabsLive` implements it:**
- `GET /v1/speech-to-text/realtime?model_id&audio_format=pcm_16000&commit_strategy=vad&
  vad_silence_threshold_secs&keyterms…&language_code&secondary_languages…`, header `xi-api-key`
  (missing → HTTP 401, no upgrade).
- down `session_started` (after `handshake` s, default 0.3 — the real one took 0.30–0.45 s from a
  script) with the parsed `config`, keyterms echoed;
- up `{"message_type":"input_audio_chunk","audio_base_64","sample_rate":16000,"commit"?}`;
- down `partial_transcript {text}` for the open segment at every new word, and at a pause of
  `vad_silence_threshold_secs` of low energy (20 ms frames, RMS < `threshold`, default 300)
  `committed_transcript {text}` (`committed_transcript_with_timestamps {text, words}` when the
  query asks `include_timestamps=true`); `commit: true` in a chunk commits at once;
- a fault (`POST /fault {"live": "<type>"}`, one use): `{"message_type": type, "error": …}` after
  `session_started`, and for `auth_error`/`quota_exceeded`/`rate_limited`/`resource_exhausted`/
  `session_time_limit_exceeded` the socket is then closed (1008); `live: "stall"` never sends
  `session_started`; `live: "drop"` closes 1 s after it.

**Batch:** `POST /v1/speech-to-text` multipart (`file`, `model_id`, …) → `scribe_v2`-shaped JSON
(`language_code`, `language_probability`, `text`, `words[{text,start,end,type:word|spacing,
logprob}]`) after `latency` s (default 0.3); `POST /fault {"batch": 429 | "quota"}` fails the next
one.

**The words.** With no script, energy-driven placeholders (`alpha bravo …`), one per 0.4 s of
voiced audio — the caption cases care about timing and the band, not the words. With a script
(`POST /script {"words":[…], "wav"?: path, "seconds"?, "cadence"?, "language"?}`, the harness
sends one per played clip, words from the corpus `.txt`), the live session emits the script's words
at `cadence` s of voiced audio each (default: the clip's voiced time / words, so the last word
lands with the clip's last voiced frame), and a batch upload answers with the share of the words
its voiced time covers, placed on its voiced frames. Several scripts in flight (two queued
sentences): the upload goes to the script whose 100 ms energy envelope correlates best with it.

Control: `GET /up`, `GET /state` (sessions, chunks, commits, batch calls, the last query and
keyterms, every message sent), `POST /script` · `/fault` · `/config` (`{"clear": true}` resets).
"""
import array, base64, hashlib, io, json, math, os, socket, socketserver, struct, sys, threading, time, urllib.parse, uuid

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
REALTIME_PATH = "/v1/speech-to-text/realtime"
BATCH_PATH = "/v1/speech-to-text"
PLACEHOLDERS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliett kilo lima mike november "
                "oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu").split()
CLOSING_ERRORS = {"auth_error", "quota_exceeded", "rate_limited", "resource_exhausted",
                  "session_time_limit_exceeded", "unaccepted_terms"}
CORPUS = os.path.expanduser("~/.walkie-talkie/voice-corpus")
SELFTEST_WAV = CORPUS + "/2026-09-18/21-05-35-11l735.wav"   # harness.CLIP_EN, 3.5 s EN
FRAME = 320            # 20 ms at 16 kHz
ENV_HOP = 1600         # 100 ms: the envelope a batch upload is matched on


# ---------------------------------------------------------------- audio helpers
def pcm_of_wav(blob):
    """(int16 array mono, rate) from a RIFF/WAVE blob — its own chunk walk: AVAudioFile writes
    WAVE_FORMAT_EXTENSIBLE and FLLR chunks the 3.9 `wave` module refuses."""
    if blob[:4] != b"RIFF" or blob[8:12] != b"WAVE":
        a = array.array("h"); a.frombytes(blob[: len(blob) // 2 * 2]); return a, 16000
    pos, rate, ch, bits, data = 12, 16000, 1, 16, b""
    while pos + 8 <= len(blob):
        cid, size = blob[pos:pos + 4], struct.unpack("<I", blob[pos + 4:pos + 8])[0]
        body = blob[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            ch, rate = struct.unpack("<HI", body[2:8]); bits = struct.unpack("<H", body[14:16])[0]
        elif cid == b"data":
            data = body
        pos += 8 + size + (size & 1)
    a = array.array("h")
    if bits == 16:
        a.frombytes(data[: len(data) // 2 * 2])
    elif bits == 32:   # float32
        f = array.array("f"); f.frombytes(data[: len(data) // 4 * 4])
        a = array.array("h", (max(-32768, min(32767, int(x * 32767))) for x in f))
    if ch > 1:
        a = array.array("h", a[::ch])
    return a, rate

def rms(a, i, n):
    seg = a[i:i + n]
    return math.sqrt(sum(x * x for x in seg) / len(seg)) if len(seg) else 0.0

def frames_rms(a, hop):
    return [rms(a, i, hop) for i in range(0, len(a) - hop + 1, hop)] or ([rms(a, 0, len(a))] if len(a) else [])

def voiced_frames(a):
    """20 ms frames above a tenth of the loudest one (floor 150): a whole file's speech."""
    r = frames_rms(a, FRAME)
    thr = max(150.0, 0.1 * max(r or [0]))
    return [k for k, v in enumerate(r) if v > thr], len(r)

def envelope(a, rate=16000):
    hop = max(1, int(rate * ENV_HOP / 16000))
    e = frames_rms(a, hop)
    m = max(e or [0]) or 1.0
    return [v / m for v in e]

def correlate(short, long_):
    """Best Pearson correlation of `short` against every window of `long_` (a 100 ms envelope)."""
    if len(short) > len(long_):
        short, long_ = long_, short
    n = len(short)
    if n < 3:
        return 0.0
    ms = sum(short) / n; ds = [x - ms for x in short]; ss = math.sqrt(sum(x * x for x in ds)) or 1e-9
    best = -1.0
    for lag in range(0, len(long_) - n + 1):
        w = long_[lag:lag + n]; mw = sum(w) / n
        num = sum(d * (x - mw) for d, x in zip(ds, w))
        den = ss * (math.sqrt(sum((x - mw) ** 2 for x in w)) or 1e-9)
        best = max(best, num / den)
    return best


# ---------------------------------------------------------------- shared state
class Scribe:
    def __init__(self):
        self.lock = threading.Lock()
        self.cfg = {"handshake": 0.3, "latency": 0.3, "threshold": 300.0, "placeholder_every": 0.4,
                    "language": "eng", "probability": 0.97}
        self.reset()

    def reset(self):
        with self.lock:
            self.scripts, self.fault, self.version = [], {}, 0
            self.stats = {"sessions": 0, "open": 0, "chunks": 0, "audioSeconds": 0.0, "partials": 0,
                          "commits": 0, "batch": 0, "errorsSent": 0, "lastQuery": None, "lastKeyterms": [],
                          "unauthorized": 0, "messages": []}

    def note(self, sid, msg):
        with self.lock:
            m = self.stats["messages"]
            m.append({"session": sid, "t": round(time.time(), 3), "type": msg.get("message_type"),
                      "text": msg.get("text") or msg.get("error")})
            del m[:-400]

    def set_script(self, body):
        """`{"words":[…] | "text", "wav"?, "seconds"?, "cadence"?, "language"?}` → the script."""
        words = body.get("words")
        if words is None:
            words = (body.get("text") or "").split()
        voiced, env = None, None
        if body.get("wav") and os.path.exists(body["wav"]):
            with open(body["wav"], "rb") as f:
                a, rate = pcm_of_wav(f.read())
            if body.get("seconds"):
                a = a[: int(rate * float(body["seconds"]))]
            vf, _ = voiced_frames(a)
            voiced = len(vf) * FRAME / 16000.0
            env = envelope(a, rate)
        cadence = body.get("cadence") or ((voiced / len(words)) if (voiced and words) else 0.3)
        s = {"id": uuid.uuid4().hex[:8], "words": list(words), "cadence": max(0.05, float(cadence)),
             "voiced": voiced, "envelope": env, "language": body.get("language") or self.cfg["language"],
             "at": time.time()}
        with self.lock:
            self.scripts.append(s)
            del self.scripts[:-8]
            self.version += 1
            s["version"] = self.version
        return {k: v for k, v in s.items() if k != "envelope"}

    def current(self):
        with self.lock:
            return self.scripts[-1] if self.scripts else None

    def take_fault(self, kind):
        with self.lock:
            f = self.fault.pop(kind, None)
            return f

    def describe(self):
        with self.lock:
            return {"cfg": dict(self.cfg), "fault": dict(self.fault), "stats": json.loads(json.dumps(self.stats)),
                    "scripts": [{k: v for k, v in s.items() if k != "envelope"} for s in self.scripts]}

STATE = Scribe()


# ---------------------------------------------------------------- the realtime session
class Session:
    """One socket: 20 ms frames through an energy VAD, words by voiced time, commits at pauses."""

    def __init__(self, conn, query):
        self.conn, self.q = conn, query
        self.sid = uuid.uuid4().hex[:12]
        self.send_lock = threading.Lock()
        self.silence_needed = float((query.get("vad_silence_threshold_secs") or ["1.5"])[0])
        self.stamps = (query.get("include_timestamps") or ["false"])[0].lower() == "true"
        self.carry = array.array("h")
        self.t = 0.0                 # audio seconds received
        self.silence = 0.0
        self.voiced_acc = 0.0
        self.segment = []            # [(word, start, end)]
        self.index = 0               # next script word
        self.placeholder = 0
        self.version = None
        self.started = threading.Event()
        self.closed = False

    # -- framing
    def send(self, msg):
        data = json.dumps(msg).encode()
        head = bytes([0x81])
        n = len(data)
        head += bytes([n]) if n < 126 else (bytes([126]) + struct.pack(">H", n) if n < 65536 else bytes([127]) + struct.pack(">Q", n))
        with self.send_lock:
            if self.closed:
                return
            try:
                self.conn.sendall(head + data)
            except OSError:
                self.closed = True
                return
        STATE.note(self.sid, msg)

    def close(self, code=1000, reason=""):
        with self.send_lock:
            if self.closed:
                return
            self.closed = True
            try:
                body = struct.pack(">H", code) + reason.encode()[:120]
                self.conn.sendall(bytes([0x88, len(body)]) + body)
            except OSError:
                pass

    # -- the words
    def next_word(self):
        s = STATE.current()
        if s and s["words"]:
            if s["version"] != self.version:          # a new clip: its words from the first
                self.version, self.index = s["version"], 0
            if self.index >= len(s["words"]):
                return None, s["cadence"]
            w = s["words"][self.index]; self.index += 1
            return w, s["cadence"]
        w = PLACEHOLDERS[self.placeholder % len(PLACEHOLDERS)]; self.placeholder += 1
        return w, STATE.cfg["placeholder_every"]

    def cadence(self):
        s = STATE.current()
        return s["cadence"] if (s and s["words"]) else STATE.cfg["placeholder_every"]

    def text(self):
        return " ".join(w for w, _, _ in self.segment)

    def commit(self):
        if not self.segment:
            return
        if self.stamps:
            words = []
            for i, (w, a, b) in enumerate(self.segment):
                if i:
                    words.append({"text": " ", "start": self.segment[i - 1][2], "end": a, "type": "spacing"})
                words.append({"text": w, "start": round(a, 3), "end": round(b, 3), "type": "word", "logprob": 0.0})
            msg = {"message_type": "committed_transcript_with_timestamps", "text": self.text(),
                   "language_code": (STATE.current() or {}).get("language", STATE.cfg["language"]), "words": words}
        else:
            msg = {"message_type": "committed_transcript", "text": self.text()}
        self.send(msg)
        with STATE.lock:
            STATE.stats["commits"] += 1
        self.segment = []

    def audio(self, pcm):
        a = array.array("h"); a.frombytes(pcm[: len(pcm) // 2 * 2])
        self.carry.extend(a)
        thr = STATE.cfg["threshold"]
        while len(self.carry) >= FRAME:
            v = rms(self.carry, 0, FRAME) > thr
            del self.carry[:FRAME]
            self.t += FRAME / 16000.0
            if v:
                self.silence = 0.0
                self.voiced_acc += FRAME / 16000.0
                if self.voiced_acc >= self.cadence():
                    self.voiced_acc = 0.0
                    w, cad = self.next_word()
                    if w:
                        self.segment.append((w, max(0.0, self.t - cad), self.t))
                        self.send({"message_type": "partial_transcript", "text": self.text()})
                        with STATE.lock:
                            STATE.stats["partials"] += 1
            else:
                self.silence += FRAME / 16000.0
                if self.segment and self.silence >= self.silence_needed:
                    self.commit()

    def chunk(self, msg):
        if msg.get("message_type") != "input_audio_chunk":
            return
        pcm = base64.b64decode(msg.get("audio_base_64") or "")
        with STATE.lock:
            STATE.stats["chunks"] += 1
            STATE.stats["audioSeconds"] = round(STATE.stats["audioSeconds"] + len(pcm) / 32000.0, 3)
        self.audio(pcm)
        if msg.get("commit"):
            self.commit()

    def config(self):
        q = self.q
        one = lambda k, d=None: (q.get(k) or [d])[0]
        return {"sample_rate": 16000, "audio_format": one("audio_format", "pcm_16000"),
                "language_code": one("language_code"), "secondary_languages": q.get("secondary_languages", []),
                "model_id": one("model_id"), "commit_strategy": one("commit_strategy", "manual"),
                "vad_silence_threshold_secs": self.silence_needed, "include_timestamps": self.stamps,
                "keyterms": q.get("keyterms", [])}

    def run(self):
        fault = STATE.take_fault("live")

        def open_session():
            time.sleep(STATE.cfg["handshake"])
            if fault == "stall" or self.closed:
                return
            self.send({"message_type": "session_started", "session_id": self.sid, "config": self.config()})
            self.started.set()
            with STATE.lock:
                STATE.stats["open"] += 1
            if fault == "drop":
                time.sleep(1.0); self.close(1011, "dropped by the fake")
                try: self.conn.shutdown(socket.SHUT_RDWR)
                except OSError: pass
            elif fault:
                self.send({"message_type": fault, "error": "injected by fake_scribe"})
                with STATE.lock:
                    STATE.stats["errorsSent"] += 1
                if fault in CLOSING_ERRORS:
                    self.close(1008, fault)
                    try: self.conn.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
        threading.Thread(target=open_session, daemon=True).start()
        buf = b""
        while not self.closed:
            try:
                op, data = read_frame(self.conn)
            except (ConnectionError, OSError, ValueError):
                break
            if op == 0x8:
                self.close(1000); break
            if op == 0x9:
                with self.send_lock:
                    try: self.conn.sendall(bytes([0x8A, len(data)]) + data)
                    except OSError: break
                continue
            if op in (0x1, 0x0):
                buf += data
                try:
                    msg = json.loads(buf.decode()); buf = b""
                except ValueError:
                    continue
                self.chunk(msg)
        self.closed = True


def recv_exact(conn, n):
    out = b""
    while len(out) < n:
        b = conn.recv(n - len(out))
        if not b:
            raise ConnectionError("eof")
        out += b
    return out

def unmask(data, mask):
    if not data:
        return data
    n = len(data)
    m = (mask * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(m, "big")).to_bytes(n, "big")

def read_frame(conn):
    b1, b2 = recv_exact(conn, 2)
    op, masked, n = b1 & 0x0F, b2 & 0x80, b2 & 0x7F
    if n == 126:
        n = struct.unpack(">H", recv_exact(conn, 2))[0]
    elif n == 127:
        n = struct.unpack(">Q", recv_exact(conn, 8))[0]
    mask = recv_exact(conn, 4) if masked else None
    data = recv_exact(conn, n)
    return op, (unmask(data, mask) if mask else data)


# ---------------------------------------------------------------- batch
def multipart(body, ctype):
    b = ctype.split("boundary=", 1)[-1].strip().strip('"').encode()
    out = {}
    for part in body.split(b"--" + b):
        if b"\r\n\r\n" not in part:
            continue
        head, data = part.split(b"\r\n\r\n", 1)
        if data.endswith(b"\r\n"):
            data = data[:-2]
        h = head.decode("utf-8", "replace")
        if 'name="' in h:
            out[h.split('name="', 1)[1].split('"', 1)[0]] = data
    return out

def batch_answer(wav):
    a, rate = pcm_of_wav(wav)
    vf, nframes = voiced_frames(a)
    voiced = len(vf) * FRAME / 16000.0
    scripts = [s for s in STATE.scripts if s["words"] and time.time() - s["at"] < 900]
    pick = scripts[-1] if scripts else None
    if len(scripts) > 1:
        env = envelope(a, rate)
        scored = [(correlate(s["envelope"], env) if s["envelope"] else -2, i, s) for i, s in enumerate(scripts)]
        pick = max(scored, key=lambda x: (x[0], x[1]))[2]
    if pick:
        n = len(pick["words"])
        share = min(1.0, voiced / pick["voiced"]) if pick["voiced"] else min(1.0, voiced / (n * pick["cadence"]))
        k = n if share >= 0.85 else int(round(n * share))
        words, lang = pick["words"][:k], pick["language"]
    else:
        k = int(voiced / STATE.cfg["placeholder_every"])
        words, lang = [PLACEHOLDERS[i % len(PLACEHOLDERS)] for i in range(k)], STATE.cfg["language"]
    toks = []
    if words:
        per = max(1, len(vf) // len(words))
        for i, w in enumerate(words):
            f0 = vf[min(len(vf) - 1, i * per)]
            f1 = vf[min(len(vf) - 1, (i + 1) * per - 1)]
            st, en = f0 * FRAME / 16000.0, (f1 + 1) * FRAME / 16000.0
            if i:
                toks.append({"text": " ", "start": toks[-1]["end"], "end": round(st, 3), "type": "spacing", "logprob": 0.0})
            toks.append({"text": w, "start": round(st, 3), "end": round(en, 3), "type": "word", "logprob": 0.0})
    return {"language_code": lang, "language_probability": STATE.cfg["probability"] if words else 0.0,
            "text": " ".join(words), "words": toks, "transcription_id": "fake_" + uuid.uuid4().hex[:10],
            "script": pick["id"] if pick else None}


# ---------------------------------------------------------------- HTTP + upgrade
class Handler(socketserver.BaseRequestHandler):
    def respond(self, code, obj, extra=""):
        body = json.dumps(obj).encode()
        reason = {200: "OK", 401: "Unauthorized", 404: "Not Found", 429: "Too Many Requests"}.get(code, "Error")
        self.request.sendall(("HTTP/1.1 %d %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\n%s\r\n"
                              % (code, reason, len(body), extra)).encode() + body)

    def handle(self):
        conn, buf = self.request, b""
        while True:
            while b"\r\n\r\n" not in buf:
                try:
                    b = conn.recv(65536)
                except OSError:
                    return
                if not b:
                    return
                buf += b
            head, buf = buf.split(b"\r\n\r\n", 1)
            lines = head.decode("latin-1").split("\r\n")
            try:
                method, target, _ = lines[0].split(" ", 2)
            except ValueError:
                return
            hdr = {}
            for l in lines[1:]:
                if ":" in l:
                    k, v = l.split(":", 1); hdr[k.strip().lower()] = v.strip()
            n = int(hdr.get("content-length") or 0)
            while len(buf) < n:
                b = conn.recv(max(65536, n - len(buf)))
                if not b:
                    return
                buf += b
            body, buf = buf[:n], buf[n:]
            url = urllib.parse.urlsplit(target)
            query = urllib.parse.parse_qs(url.query, keep_blank_values=True)
            if url.path == REALTIME_PATH and "websocket" in hdr.get("upgrade", "").lower():
                return self.upgrade(hdr, query)
            self.route(method, url.path, hdr, body)
            if hdr.get("connection", "").lower() == "close":
                return

    def upgrade(self, hdr, query):
        with STATE.lock:
            STATE.stats["sessions"] += 1
            STATE.stats["lastQuery"] = {k: v for k, v in query.items()}
            STATE.stats["lastKeyterms"] = query.get("keyterms", [])
        if not (hdr.get("xi-api-key") or query.get("token")):
            with STATE.lock:
                STATE.stats["unauthorized"] += 1
            return self.respond(401, {"detail": {"status": "invalid_api_key", "message": "fake_scribe: no xi-api-key"}},
                                "Connection: close\r\n")
        accept = base64.b64encode(hashlib.sha1((hdr.get("sec-websocket-key", "") + GUID).encode()).digest()).decode()
        self.request.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                              "Sec-WebSocket-Accept: %s\r\n\r\n" % accept).encode())
        Session(self.request, query).run()

    def route(self, method, path, hdr, body):
        try:
            data = json.loads(body.decode() or "{}") if hdr.get("content-type", "").startswith("application/json") else {}
        except ValueError:
            data = {}
        if path == "/up":
            return self.respond(200, {"ok": True, "fake": "scribe"})
        if path == "/state":
            return self.respond(200, STATE.describe())
        if path == "/script" and method == "POST":
            if data.get("clear"):
                with STATE.lock:
                    STATE.scripts = []; STATE.version += 1
                return self.respond(200, {"ok": True})
            return self.respond(200, STATE.set_script(data))
        if path == "/fault" and method == "POST":
            with STATE.lock:
                STATE.fault = {} if data.get("clear") else dict(STATE.fault, **{k: v for k, v in data.items() if k in ("live", "batch")})
                return self.respond(200, {"fault": dict(STATE.fault)})
        if path == "/config" and method == "POST":
            if data.get("clear"):
                STATE.reset(); return self.respond(200, {"ok": True})
            with STATE.lock:
                STATE.cfg.update({k: v for k, v in data.items() if k in STATE.cfg})
                return self.respond(200, dict(STATE.cfg))
        if path == BATCH_PATH and method == "POST":
            with STATE.lock:
                STATE.stats["batch"] += 1
            if not hdr.get("xi-api-key"):
                return self.respond(401, {"detail": {"status": "invalid_api_key", "message": "fake_scribe: no xi-api-key"}})
            f = STATE.take_fault("batch")
            time.sleep(STATE.cfg["latency"])
            if f == "quota":
                return self.respond(401, {"detail": {"status": "quota_exceeded",
                                                     "message": "This request exceeds your quota of 10000. You have 0 credits remaining (fake_scribe)."}})
            if f:
                return self.respond(int(f), {"detail": {"message": "injected by fake_scribe"}})
            parts = multipart(body, hdr.get("content-type", ""))
            if "file" not in parts:
                return self.respond(422, {"detail": {"message": "fake_scribe: no file part"}})
            return self.respond(200, batch_answer(parts["file"]))
        return self.respond(404, {"detail": "fake_scribe: no route %s %s" % (method, path)})


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(port=0, host="127.0.0.1"):
    """Start in a daemon thread; returns (server, port)."""
    srv = Server((host, port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]

def urls(port):
    return ("ws://127.0.0.1:%d%s" % (port, REALTIME_PATH), "http://127.0.0.1:%d%s" % (port, BATCH_PATH))


# ---------------------------------------------------------------- self-test (a client, no app)
def _http(port, method, path, obj=None, raw=None, ctype="application/json", key="selftest"):
    body = raw if raw is not None else json.dumps(obj or {}).encode()
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(("%s %s HTTP/1.1\r\nHost: x\r\nxi-api-key: %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
               "Connection: close\r\n\r\n" % (method, path, key, ctype, len(body))).encode() + body)
    out = b""
    while True:
        b = s.recv(65536)
        if not b:
            break
        out += b
    s.close()
    head, _, rest = out.partition(b"\r\n\r\n")
    return int(head.split()[1]), json.loads(rest.decode() or "{}")

def _client_session(port, pcm, speed, label, keyterms=("commit", "branch")):
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    q = [("model_id", "scribe_v2_realtime"), ("audio_format", "pcm_16000"), ("commit_strategy", "vad"),
         ("vad_silence_threshold_secs", "1.5")] + [("keyterms", k) for k in keyterms] + \
        [("language_code", "ro"), ("secondary_languages", "en")]
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall(("GET %s?%s HTTP/1.1\r\nHost: 127.0.0.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\nxi-api-key: selftest\r\n\r\n"
               % (REALTIME_PATH, urllib.parse.urlencode(q), key)).encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        resp += s.recv(4096)
    head = resp.split(b"\r\n\r\n", 1)[0].decode()
    want = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
    ok = " 101 " in head.split("\r\n")[0] and want in head
    t0 = time.time()
    print("  [%s] upgrade %s" % (label, "101, accept OK" if ok else "FAILED: " + head.split("\r\n")[0]))
    got = []

    def reader():
        while True:
            try:
                op, data = read_frame(s)
            except (ConnectionError, OSError, ValueError):
                return
            if op == 0x8:
                code = struct.unpack(">H", data[:2])[0] if len(data) >= 2 else None
                print("  [%s] %5.2f s  close %s %s" % (label, time.time() - t0, code, data[2:].decode(errors="replace")))
                return
            m = json.loads(data.decode()); got.append(m)
            extra = m.get("text") if "text" in m else (m.get("error") or ("keyterms %s" % m.get("config", {}).get("keyterms")))
            print("  [%s] %5.2f s  %-22s %s" % (label, time.time() - t0, m.get("message_type"), extra))
    th = threading.Thread(target=reader, daemon=True); th.start()
    step = 1360     # the app's ~85 ms Loopback buffer
    for i in range(0, len(pcm), step):
        chunk = pcm[i:i + step].tobytes()
        payload = json.dumps({"message_type": "input_audio_chunk", "audio_base_64": base64.b64encode(chunk).decode(),
                              "sample_rate": 16000}).encode()
        mask = os.urandom(4)
        n = len(payload)
        head = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n)
                                if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n))
        try:
            s.sendall(head + mask + unmask(payload, mask))
        except OSError:
            break
        time.sleep(step / 16000.0 / speed)
    time.sleep(0.3)
    try:
        s.sendall(bytes([0x88, 0x82]) + b"\0\0\0\0" + struct.pack(">H", 1000))
    except OSError:
        pass
    th.join(2); s.close()
    return got

def selftest(wav, speed):
    srv, port = serve(0)
    live, batch = urls(port)
    print("fake Scribe on %s (live %s, batch %s)" % (port, live, batch))
    with open(wav, "rb") as f:
        a, rate = pcm_of_wav(f.read())
    clip = a[: rate * 3]
    pcm = array.array("h", clip) + array.array("h", bytes(2 * 16000 * 2))    # 3 s of the clip + 2 s of silence
    print("clip: %s — 3 s + 2 s silence, streamed at %.1f× real time in 85 ms chunks" % (os.path.basename(wav), speed))
    print("\n1. no script — energy-driven placeholders, a commit at the 1.5 s pause:")
    m1 = _client_session(port, pcm, speed, "energy")
    txt = os.path.splitext(wav)[0] + ".txt"
    words = open(txt).read().split() if os.path.exists(txt) else []
    print("\n2. scripted from %s (3 s of the clip):" % os.path.basename(txt))
    code, sc = _http(port, "POST", "/script", {"words": words, "wav": wav, "seconds": 3})
    print("  POST /script → %d: %d words, voiced %.2f s, cadence %.2f s/word" % (code, len(sc["words"]), sc["voiced"] or 0, sc["cadence"]))
    m2 = _client_session(port, pcm, speed, "script")
    print("\n3. batch upload of the same 3 s (multipart, like transcribe()):")
    bnd = "walkie-selftest"
    buf = io.BytesIO()
    import wave as _wave
    w = _wave.open(buf, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(clip.tobytes()); w.close()
    body = b""
    for k, v in (("model_id", "scribe_v2"), ("timestamps_granularity", "word")):
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (bnd, k, v)).encode()
    body += ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"t.wav\"\r\nContent-Type: audio/wav\r\n\r\n" % bnd).encode()
    body += buf.getvalue() + ("\r\n--%s--\r\n" % bnd).encode()
    t = time.time()
    code, r = _http(port, "POST", BATCH_PATH, raw=body, ctype="multipart/form-data; boundary=" + bnd)
    print("  HTTP %d in %.2f s: %s (%.2f) %r, %d tokens, first %s" % (code, time.time() - t, r.get("language_code"),
          r.get("language_probability", 0), r.get("text"), len(r.get("words", [])), (r.get("words") or [None])[0]))
    print("\n4. fault: quota_exceeded on the next session:")
    _http(port, "POST", "/fault", {"live": "quota_exceeded"})
    m4 = _client_session(port, pcm[: 16000], speed, "quota")
    st = STATE.describe()["stats"]
    print("\nstate: sessions %d, opened %d, chunks %d (%.1f s audio), partials %d, commits %d, batch %d, errors %d, keyterms %s"
          % (st["sessions"], st["open"], st["chunks"], st["audioSeconds"], st["partials"], st["commits"], st["batch"],
             st["errorsSent"], st["lastKeyterms"]))
    ok = (any(m["message_type"] == "committed_transcript" for m in m1)
          and any(m["message_type"] == "partial_transcript" for m in m1)
          and any(m["message_type"] == "committed_transcript" and m["text"].split()[:2] == words[:2] for m in m2)
          and code == 200 and r.get("text", "").split()[:2] == words[:2]
          and any(m["message_type"] == "quota_exceeded" for m in m4)
          and any(m["message_type"] == "session_started" and m["config"]["keyterms"] == ["commit", "branch"] for m in m1))
    print("SELFTEST", "PASS" if ok else "FAIL")
    srv.shutdown()
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    port = int(args[args.index("--port") + 1]) if "--port" in args else 0
    if "--selftest" in args:
        wav = args[args.index("--wav") + 1] if "--wav" in args else SELFTEST_WAV
        sys.exit(selftest(wav, 4.0 if "--fast" in args else 1.0))
    srv, port = serve(port)
    live, batch = urls(port)
    print("fake Scribe on %d\n  WT_ELEVEN_LIVE_URL=%s\n  WT_ELEVEN_BATCH_URL=%s" % (port, live, batch), flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()

if __name__ == "__main__":
    main()
