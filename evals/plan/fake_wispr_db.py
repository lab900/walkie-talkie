#!/usr/bin/env python3
"""**A fake Wispr Flow `flow.sqlite`** for desk runs of Engine = Wispr (2026-09-28, the
reviews' H1 / B §4.1). The app reads it instead of Wispr's own file while `WT_WISPR_DB=<path>`
is in its environment or in `~/.walkie-talkie/elevenlabs.env` (re-read once a second, no
relaunch — `WisprFlowDB.overridePath`). Schema only, never data: `History` (+ `Notes`,
`NoteVersions`, which `WisprNotes` reads) copied from the real file with
`sqlite3 -readonly …/flow.sqlite .schema History` on 2026-09-28; `create(from_real=True)` takes
the live schema instead when the real file is there (a Wispr update that renames a column
then shows up in the fake too — W-B4).

Rows are written the way Wispr writes them (B §1): created at the gesture with `status` NULL,
`timestamp` text `YYYY-MM-DD HH:MM:SS.mmm +00:00` (UTC), then rewritten in place — `processing`,
then a terminal status with `asrText`/`formattedText`/`pastedText`/`e2eLatency` in the same
write. Rollback journal by default: the app's `mode=ro` reader cannot create a `-shm`.
`create(wal=True)` (batch 3, 2026-09-28) is Wispr's own journal mode: a holder connection stays
open for the file's life (so the `-wal`/`-shm` persist, as under a running Wispr, and the
read-only reader can use them) until `close()` — the only way a desk case reaches the relay's
`flow.sqlite-wal` watch.

    fake_wispr_db.py create PATH [--from-real]
    fake_wispr_db.py insert PATH [--status S] [--asr T] [--formatted T] [--pasted T]
                                 [--at EPOCH|now|+SECONDS] [--speech S] [--e2e MS] [--mic NAME]
    fake_wispr_db.py update PATH ROWID [same fields]
    fake_wispr_db.py show PATH [N]
    fake_wispr_db.py --selftest
"""
import datetime, os, sqlite3, sys, time, uuid

REAL = os.path.expanduser("~/Library/Application Support/Wispr Flow/flow.sqlite")

SCHEMA = """CREATE TABLE `History` (`transcriptEntityId` VARCHAR(36) NOT NULL UNIQUE PRIMARY KEY, `asrText` TEXT, `formattedText` TEXT, `editedText` TEXT, `timestamp` DATETIME, `audio` BLOB, `screenshot` BLOB, `additionalContext` JSON, `status` VARCHAR(255), `app` VARCHAR(255), `url` VARCHAR(255), `e2eLatency` FLOAT, `needsUploading` TINYINT(1) NOT NULL DEFAULT 0, `duration` FLOAT, `numWords` INTEGER, `shareType` TEXT NOT NULL DEFAULT 'no', `textboxContents` TEXT, `appVersion` VARCHAR(255) NOT NULL DEFAULT '0.0.0', `editedTextStatus` TEXT NOT NULL DEFAULT 'NOT_EXTRACTED', `editedTextAttempts` INTEGER NOT NULL DEFAULT 0, `toneMatchedText` TEXT, `toneMatchPairs` JSONB, `feedback` TEXT, `language` TEXT, `isArchived` TINYINT(1) NOT NULL DEFAULT 0, `micDevice` TEXT, `conversationId` VARCHAR(255), `builtInAudio` BLOB, `formattingDivergenceScore` FLOAT, `pastedText` TEXT, `defaultAsrText` TEXT, `fallbackAsrText` TEXT, `defaultFormattedText` TEXT, `fallbackFormattedText` TEXT, `fallbackAsrDivergenceScore` FLOAT, `fallbackFormattingDivergenceScore` FLOAT, `detectedLanguage` TEXT, `averageLogProb` FLOAT, `hasRevertedAI` TINYINT(1), `axText` TEXT, `userEditMetaData` JSON, `axHTML` TEXT, `opusChunks` JSON, `usedFallbackAsr` TINYINT(1), `usedFallbackFormatting` TINYINT(1), `desiredAsr` TEXT, `desiredFormatted` TEXT, `calledExternalAsr` TINYINT(1), `transcriptOrigin` TEXT, `platform` VARCHAR(255), `transcriptCommand` TEXT, `personalizationStyleSettings` JSON, `clientNetworkLatency` FLOAT, `fallbackLevel` INTEGER, `speechDuration` FLOAT, `timezoneOffsetMinutes` INTEGER, `numWordsCorrected` INTEGER, `numDictionaryReplacements` INTEGER, `serverFinalizedText` TEXT, `contentObservationEndReason` VARCHAR(255) DEFAULT NULL, `contentObservationEndLastKeystroke` VARCHAR(255) DEFAULT NULL, `editDistanceToDictated` FLOAT DEFAULT NULL, `editedTextUnbounded` TEXT DEFAULT NULL);
CREATE INDEX `idx_formattedText` ON `History` (`formattedText`);
CREATE INDEX `idx_timestamp_archived` ON `History` (`timestamp`, `isArchived`);
CREATE INDEX `idx_duration_numWords` ON `History` (`numWords`, `duration`);
CREATE INDEX `idx_editedtextstatus_conversationid_timestamp_app_url` ON `History` (`editedTextStatus`, `conversationId`, `timestamp`, `app`, `url`);
CREATE INDEX `idx_history_timestamp_archived_status` ON `History` (`timestamp`, `isArchived`, `status`);
CREATE INDEX `idx_history_timestamp_needs_uploading` ON `History` (`timestamp`, `needsUploading`);
CREATE INDEX `idx_history_status_app_url` ON `History` (`status`, `app`, `url`);
CREATE INDEX idx_history_per_app_stats ON "History" ("app", "url", "numWords", "timestamp") WHERE "status" != 'no_audio' AND "numWords" > 0;
CREATE INDEX idx_history_needs_uploading ON "History" ("needsUploading") WHERE "needsUploading" = 1;"""

NOTES_SCHEMA = """CREATE TABLE `Notes` (`id` VARCHAR(36) NOT NULL PRIMARY KEY, `title` VARCHAR(255) NOT NULL, `contentPreview` TEXT NOT NULL, `content` TEXT NOT NULL, `createdAt` DATETIME NOT NULL, `modifiedAt` DATETIME NOT NULL, `synced` TINYINT(1) NOT NULL DEFAULT 1, `isDeleted` TINYINT(1) NOT NULL DEFAULT 0, `finalized` TINYINT(1) NOT NULL DEFAULT 0, `pinned` TINYINT(1) NOT NULL DEFAULT 0, `searchableContent` TEXT);
CREATE TABLE `NoteVersions` (`id` VARCHAR(36) NOT NULL PRIMARY KEY, `noteId` VARCHAR(36) NOT NULL REFERENCES `Notes` (`id`) ON DELETE CASCADE, `content` TEXT NOT NULL, `source` VARCHAR(30) NOT NULL, `transformId` VARCHAR(255), `transformPrompt` TEXT, `createdAt` DATETIME NOT NULL);"""

# Python keyword → History column
FIELDS = {"status": "status", "asr": "asrText", "formatted": "formattedText", "pasted": "pastedText",
          "timestamp": "timestamp", "speech": "speechDuration", "e2e": "e2eLatency", "mic": "micDevice",
          "app": "app", "duration": "duration", "language": "detectedLanguage", "words": "numWords"}


def stamp(at=None):
    """Wispr's `timestamp` text for an epoch (float), `now`, `+s`/`-s` from now, or a string as is."""
    if isinstance(at, str):
        if at == "now":
            at = time.time()
        elif at[:1] in "+-":
            at = time.time() + float(at)
        else:
            return at
    t = datetime.datetime.fromtimestamp(time.time() if at is None else float(at), datetime.timezone.utc)
    return t.strftime("%Y-%m-%d %H:%M:%S.") + "%03d +00:00" % (t.microsecond // 1000)


def real_schema():
    """The live `History` + `Notes` + `NoteVersions` DDL of Wispr's own file (read-only), or None."""
    if not os.path.exists(REAL):
        return None
    uri = "file:" + REAL.replace(" ", "%20") + "?mode=ro"
    try:
        c = sqlite3.connect(uri, uri=True, timeout=1)
        rows = c.execute("select sql from sqlite_master where tbl_name in ('History','Notes','NoteVersions') "
                         "and sql is not null order by type desc").fetchall()
        c.close()
        return ";\n".join(r[0] for r in rows) + ";" if rows else None
    except sqlite3.Error:
        return None


class FakeWisprDB:
    def __init__(self, path):
        self.path = path

    holder = None

    def create(self, from_real=False, wal=False):
        """A fresh file (any old one and its journal removed): the schema, no rows. `wal`: WAL
        mode, held open by `self.holder` until `close()`."""
        self.close()
        for p in (self.path, self.path + "-journal", self.path + "-wal", self.path + "-shm"):
            if os.path.exists(p):
                os.remove(p)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        ddl = (real_schema() if from_real else None) or (SCHEMA + "\n" + NOTES_SCHEMA)
        c = self._c()
        c.execute("pragma journal_mode=%s" % ("wal" if wal else "delete"))
        c.executescript(ddl)
        c.commit()
        if wal:
            self.holder = c
        else:
            c.close()
        return self

    def close(self):
        """Let go of the WAL holder (the `-wal` is checkpointed and removed, as at Wispr's quit)."""
        if self.holder is not None:
            try:
                self.holder.close()
            except Exception:
                pass
            self.holder = None

    def _c(self):
        return sqlite3.connect(self.path, timeout=2)

    def insert(self, status=None, at=None, **fields):
        """A row as Wispr creates it at the gesture (`status` NULL unless given); returns its rowid.
        `at` is the gesture's time (epoch, `now`, `+s`) — the relay adopts a row only if it is at or
        after its own gesture − 2 s."""
        cols = {"transcriptEntityId": str(uuid.uuid4()), "timestamp": stamp(at), "status": status}
        for k, v in fields.items():
            cols[FIELDS.get(k, k)] = v
        c = self._c()
        cur = c.execute("insert into History (%s) values (%s)" % (",".join("`%s`" % k for k in cols),
                                                                   ",".join("?" * len(cols))), list(cols.values()))
        c.commit(); rid = cur.lastrowid; c.close()
        return rid

    def update(self, rowid, **fields):
        """Rewrite a row in place, all given columns in one write (Wispr's terminal write is one tick)."""
        if "at" in fields:
            fields["timestamp"] = stamp(fields.pop("at"))
        cols = {FIELDS.get(k, k): v for k, v in fields.items()}
        c = self._c()
        c.execute("update History set %s where rowid = ?" % ",".join("`%s` = ?" % k for k in cols),
                  list(cols.values()) + [rowid])
        c.commit(); c.close()

    def finish(self, rowid, text, status="formatted", e2e=850.0, speech=None):
        """The terminal write of a successful sentence: every text column at once."""
        self.update(rowid, status=status, asr=text, formatted=text, pasted=text, e2e=e2e,
                    speech=speech if speech is not None else max(0.5, len(text.split()) / 2.5),
                    mic="Built-in mic (recommended)", app="com.apple.Terminal")

    def rows(self, n=5):
        c = self._c()
        out = c.execute("select rowid, coalesce(status,''), coalesce(asrText,''), coalesce(formattedText,''), "
                        "coalesce(pastedText,''), timestamp, strftime('%s', timestamp), speechDuration, e2eLatency "
                        "from History order by rowid desc limit ?", (n,)).fetchall()
        c.close()
        return out

    def newest(self):
        r = self.rows(1)
        return r[0] if r else None


def _selftest():
    import tempfile
    d = tempfile.mkdtemp()
    db = FakeWisprDB(os.path.join(d, "flow.sqlite")).create()
    t0 = time.time()
    r1 = db.insert(at=t0)
    assert db.newest()[1] == "", db.newest()
    db.update(r1, status="processing", speech=2.0)
    db.finish(r1, "hello from the fake")
    r = db.newest()
    assert r[0] == r1 and r[1] == "formatted" and r[4] == "hello from the fake", r
    assert abs(int(r[6]) - int(t0)) <= 1, (r[6], t0)          # the app's strftime('%s', timestamp)
    r2 = db.insert(status="raw_transcript", asr="", at="+1")
    assert db.newest()[0] == r2 == r1 + 1
    # The app's own read, byte for byte (WisprHistory.read), through a mode=ro URI.
    uri = "file:" + db.path.replace(" ", "%20") + "?mode=ro"
    c = sqlite3.connect(uri, uri=True)
    row = c.execute("select rowid, coalesce(status, ''), coalesce(pastedText, ''), coalesce(formattedText, ''), "
                    "coalesce(e2eLatency, 0), coalesce(app, ''), coalesce(micDevice, ''), coalesce(language, ''), "
                    "coalesce(strftime('%s', timestamp), '0'), coalesce(asrText, '') from History where rowid = ?",
                    (r1,)).fetchone()
    c.close()
    assert row[1] == "formatted" and row[2] == "hello from the fake" and row[6].startswith("Built-in"), row
    live = real_schema()
    if live:
        a = sqlite3.connect(":memory:"); a.executescript(live)
        b = sqlite3.connect(":memory:"); b.executescript(SCHEMA)
        ca = [x[1] for x in a.execute("pragma table_info(History)")]
        cb = [x[1] for x in b.execute("pragma table_info(History)")]
        print("schema vs the real file:", "identical" if ca == cb else "DIFFERS: %s" % sorted(set(ca) ^ set(cb)))
    w = FakeWisprDB(os.path.join(d, "wal.sqlite")).create(wal=True)
    rw = w.insert(at="now")
    assert os.path.exists(w.path + "-wal"), "the holder keeps the WAL"
    c = sqlite3.connect("file:" + w.path.replace(" ", "%20") + "?mode=ro", uri=True)
    v0 = c.execute("pragma data_version").fetchone()[0]
    w.update(rw, status="processing")
    assert c.execute("select status from History where rowid = ?", (rw,)).fetchone()[0] == "processing"
    assert c.execute("pragma data_version").fetchone()[0] != v0
    c.close(); w.close()
    print("selftest ok —", db.path)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    if argv[0] == "--selftest":
        _selftest(); return 0
    cmd, path, rest = argv[0], argv[1], argv[2:]
    db = FakeWisprDB(path)
    if cmd == "create":
        db.create(from_real="--from-real" in rest); print(path); return 0
    if cmd == "show":
        for r in db.rows(int(rest[0]) if rest else 5):
            print(r)
        return 0
    rowid = None
    if cmd == "update":
        rowid, rest = int(rest[0]), rest[1:]
    fields, i = {}, 0
    while i < len(rest):
        k, v = rest[i].lstrip("-"), rest[i + 1]
        fields[k] = float(v) if k in ("speech", "e2e", "duration") else v
        i += 2
    if cmd == "insert":
        print(db.insert(**fields))
    elif cmd == "update":
        db.update(rowid, **fields)
    else:
        raise SystemExit("unknown command %r" % cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
