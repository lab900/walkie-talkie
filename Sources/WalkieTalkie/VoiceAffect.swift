import Foundation

/// **What the transcript loses: where he hesitated, and whether the whole
/// sentence was hesitant** (2026-09-27).
///
/// Victor's rules (spec: `~/workspace/voice-distill/docs/voice-affect.md`,
/// *Design propus*, decided 2026-09-26 — *"de acord"*):
///
/// - **exactly two global tags**, `[voice: hesitant]` and `[voice: tense]`, and
///   otherwise **nothing** — fluent is his assertive mode and carries no tag;
/// - **the tag says only what is lost in transcription** — no statistics, no
///   z-scores, nothing concluded from the words (*"nu știu"* is already in the
///   text; the model reads it there);
/// - **more important than the tag: WHERE he hesitated** — `[?]` in the words,
///   between the two words around a pause that was unusually long *for him*, so
///   the agent asks about *that* and not about everything;
/// - **what the agent does with it lives in CLAUDE.md**, not in the tag.
///
/// Everything here is pure: tokens with timings in, a `Report` out. It runs per
/// **sentence**, on that sentence's own words and its own take's meter series
/// (the sentence queue, Q12, means two sentences can be in flight — nothing here
/// may read a recorder that has moved on). → `.claude/rules/dictation-source.md`,
/// *Voice affect*
enum VoiceAffect {

    // MARK: - The switch

    /// **`WT_VOICE_AFFECT`** — environment, then `elevenlabs.env`, then the
    /// `voiceAffect` user default. **On** unless one of them says `0`/`false`/`off`.
    /// Covers the `[?]` marks and the hesitant tag together.
    static var isEnabled: Bool { flag("WT_VOICE_AFFECT", defaults: "voiceAffect", fallback: true) }

    /// **`WT_VOICE_TENSE`** — same chain (`voiceTense`), **off** by default. On,
    /// the energy-spread half of *tense* may raise `[voice: tense]`; off, the
    /// spread is still measured and filed in the outbox, never tagged.
    static var tenseEnabled: Bool { flag("WT_VOICE_TENSE", defaults: "voiceTense", fallback: false) }

    private static func flag(_ key: String, defaults: String, fallback: Bool) -> Bool {
        let raw = ProcessInfo.processInfo.environment[key] ?? ElevenLabsSource.fileValue(key)
        if let raw {
            switch raw.lowercased() {
            case "0", "false", "off", "no": return false
            case "1", "true", "on", "yes": return true
            default: break
            }
        }
        if UserDefaults.standard.object(forKey: defaults) != nil {
            return UserDefaults.standard.bool(forKey: defaults)
        }
        return fallback
    }

    // MARK: - Thresholds

    /// **Every number the verdict turns on, and none of them measured yet.**
    ///
    /// The defaults are placeholders (the orchestrator's brief, 2026-09-27) until
    /// the voice-distill session delivers his RO/EN distributions
    /// (`python affect/timing.py --report` over the corpus) as
    /// `~/.walkie-talkie/voice-affect.json` — see `load(from:)` for the shape.
    /// **Precision before recall** (the spec): a false *hesitant* costs more than
    /// a missed one, so every signal also has a minimum count.
    struct Thresholds: Equatable {
        /// A gap between two words this long is *unusually long for him* and
        /// gets a `[?]`. TODO: his p97 of inter-word gaps, per language (`gaps.p97`).
        var longPause: TimeInterval = 1.2
        /// The same after a `.`/`?`/`!` — a breath between two sentences is not a
        /// hesitation inside one. TODO: from his data. (`…` is not a boundary:
        /// trailing off *is* the hesitation.)
        var boundaryPause: TimeInterval = 2.0
        /// Hesitant signal 1: long pauses per minute of speech span… TODO.
        var longPausesPerMinute: Double = 3
        /// …and at least this many of them, so one pause in a ten-second
        /// sentence (6/min) is a `[?]` and not a verdict.
        var minLongPauses: Int = 2
        /// Hesitant signal 2: (fillers + restarts) / words. TODO: his p90/p97 of `fillers`.
        var disfluencyShare: Double = 0.08
        var minDisfluencies: Int = 2
        /// Hesitant signal 3: `rate` under this fraction of his median…
        var slowRateFactor: Double = 0.6
        /// …his median `rate` (words per second of span, timing.py's definition,
        /// so the two are comparable). **nil = signal 3 is off** — there is no
        /// honest default for *his* median. TODO: `rate.p50` per language.
        var medianRate: Double? = nil
        /// A rate over less span than this is noise.
        var minSpanForRate: TimeInterval = 4
        /// No verdict on fewer words than this (the `[?]` marks still apply).
        var minWords: Int = 5
        /// How many of the three signals it takes. 1 = the brief's OR; the spec's
        /// *≥ 2 independent signals* is `2`, once the data says 1 is too eager.
        var requiredSignals: Int = 1
        /// A word said again within this long is a restart (`the the`, `vreau vreau`).
        var restartWindow: TimeInterval = 1.5
        /// A gap within this of a shutter/selection press is the gesture's, not a
        /// hesitation: an area drag is seconds of silence he did not hesitate in.
        var gestureGuard: TimeInterval = 0.3
        /// Tense (behind `WT_VOICE_TENSE`): standard deviation of the voiced
        /// hops' level, in dB. TODO: a placeholder — needs his per-microphone
        /// baseline; the pitch half needs F0, which nothing here measures.
        var tenseEnergySpreadDb: Double = 9
        var minVoicedHopsForTense: Int = 20
        /// Where these came from: `defaults`, or the file (and which language block).
        var source: String = "defaults"

        /// The keys `voice-affect.json` may set, by the same name as the fields.
        mutating func apply(_ o: [String: Any]) {
            func d(_ k: String) -> Double? { (o[k] as? NSNumber)?.doubleValue }
            func i(_ k: String) -> Int? { (o[k] as? NSNumber)?.intValue }
            if let v = d("longPause") { longPause = v }
            if let v = d("boundaryPause") { boundaryPause = v }
            if let v = d("longPausesPerMinute") { longPausesPerMinute = v }
            if let v = i("minLongPauses") { minLongPauses = v }
            if let v = d("disfluencyShare") { disfluencyShare = v }
            if let v = i("minDisfluencies") { minDisfluencies = v }
            if let v = d("slowRateFactor") { slowRateFactor = v }
            if let v = d("medianRate") { medianRate = v }
            if let v = d("minSpanForRate") { minSpanForRate = v }
            if let v = i("minWords") { minWords = v }
            if let v = i("requiredSignals") { requiredSignals = v }
            if let v = d("restartWindow") { restartWindow = v }
            if let v = d("gestureGuard") { gestureGuard = v }
            if let v = d("tenseEnergySpreadDb") { tenseEnergySpreadDb = v }
            if let v = i("minVoicedHopsForTense") { minVoicedHopsForTense = v }
        }

        var json: [String: Any] {
            var o: [String: Any] = [
                "longPause": longPause, "boundaryPause": boundaryPause,
                "longPausesPerMinute": longPausesPerMinute, "minLongPauses": minLongPauses,
                "disfluencyShare": disfluencyShare, "minDisfluencies": minDisfluencies,
                "slowRateFactor": slowRateFactor, "minSpanForRate": minSpanForRate,
                "minWords": minWords, "requiredSignals": requiredSignals,
                "restartWindow": restartWindow, "gestureGuard": gestureGuard,
                "tenseEnergySpreadDb": tenseEnergySpreadDb, "source": source,
            ]
            o["medianRate"] = medianRate ?? NSNull()
            return o
        }
    }

    /// `~/.walkie-talkie/voice-affect.json` (follows `--home`).
    static var fileURL: URL { Outbox.home.appendingPathComponent("voice-affect.json") }

    /// **The file's shape**, matched to `affect/timing.py --report` in
    /// voice-distill — per language, per measure, the percentiles it prints:
    ///
    /// ```json
    /// {
    ///   "thresholds": { "longPause": 1.2, "requiredSignals": 1 },
    ///   "ro": { "gaps": {"p50": 0.12, "p90": 0.55, "p97": 1.05},
    ///           "rate": {"p10": 1.6, "p50": 2.4, "p90": 3.1, "p97": 3.5},
    ///           "longest": {…}, "pause_ratio": {…}, "pauses_gt1": {…},
    ///           "fillers": {…}, "restarts": {…}, "lead": {…},
    ///           "thresholds": { "boundaryPause": 2.4 } },
    ///   "en": { … }
    /// }
    /// ```
    ///
    /// Layered, later wins: the defaults → top-level `thresholds` (hand
    /// overrides) → the language's percentiles (`gaps.p97` → `longPause`,
    /// `rate.p50` → `medianRate`) → the language's own `thresholds`.
    /// **`gaps` is not in today's `--report`** — it prints `longest` (the
    /// longest gap *per clip*), whose p50 would mark half his sentences; the
    /// pooled inter-word gaps are in `runs/timing.jsonl` (`gaps`) and need one
    /// more line in the report. Until then `longPause` stays at its default or a
    /// hand-set `thresholds.longPause`.
    static func load(from obj: [String: Any], language: String?) -> Thresholds {
        var t = Thresholds()
        var from: [String] = []
        if let o = obj["thresholds"] as? [String: Any] { t.apply(o); from.append("file") }
        if let lang = language.map(normalizedLanguage), let block = obj[lang] as? [String: Any] {
            func pct(_ measure: String, _ p: String) -> Double? {
                ((block[measure] as? [String: Any])?[p] as? NSNumber)?.doubleValue
            }
            if let v = pct("gaps", "p97") { t.longPause = v; from.append("\(lang).gaps.p97") }
            if let v = pct("rate", "p50") { t.medianRate = v; from.append("\(lang).rate.p50") }
            if let o = block["thresholds"] as? [String: Any] { t.apply(o); from.append("\(lang).thresholds") }
        }
        t.source = from.isEmpty ? "defaults" : from.joined(separator: " + ")
        return t
    }

    private static var cached: (mtime: Date, obj: [String: Any])?
    private static let cacheLock = NSLock()

    /// The thresholds for one sentence: the file if it is there (re-read when
    /// it changes — one `stat` per sentence), else the defaults.
    static func thresholds(language: String?) -> Thresholds {
        let url = fileURL
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: url.path),
              let mtime = attrs[.modificationDate] as? Date else { return Thresholds() }
        cacheLock.lock(); defer { cacheLock.unlock() }
        if cached?.mtime != mtime {
            guard let data = try? Data(contentsOf: url),
                  let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                Log.error("voice affect: \(url.path) is not a JSON object — defaults")
                cached = nil
                return Thresholds()
            }
            cached = (mtime, obj)
        }
        return load(from: cached!.obj, language: language)
    }

    /// `ro`, `ron`, `ro-RO` → `ro`; `en`, `eng` → `en`; anything else as given.
    static func normalizedLanguage(_ code: String) -> String {
        let c = code.lowercased()
        if c.hasPrefix("ro") { return "ro" }
        if c.hasPrefix("en") { return "en" }
        return c
    }

    // MARK: - Tokens

    /// **Non-lexical fillers only** — sounds, not words, in either language (he
    /// mixes them in one sentence). Kept close to `timing.py`'s `FILLER` so the
    /// count here is the count his distribution was read off: `ăăă`, `ââ`,
    /// `îî`, `mmm`, `hm`, `ăhm`, `um`, `uh`, `er`/`erm`, `eh`, `aa`, `ee`.
    /// Deliberately **not** `deci`, `adică`, `like`, `so`, `you know` — those are
    /// words, the transcript keeps them and the model reads them. Single `a` and
    /// `e` are Romanian words; only a doubled one is a filler.
    static let fillerPattern = #"^(ă+|â+|î+|ă+h?m+|mm+|hm+|uh+|uhm+|um+|er+m?|eh+|aa+|ee+)$"#
    private static let fillerRegex = try! NSRegularExpression(pattern: fillerPattern)

    /// Said twice on purpose: emphasis and answers, not restarts.
    static let repeatable: Set<String> = [
        "foarte", "mult", "tare", "da", "nu", "hai", "gata", "bine", "ok", "okay",
        "very", "really", "so", "much", "no", "yes", "yeah", "bye",
    ]

    /// Lower-case, letters and digits only — `Clienți,` → `clienți`.
    static func normalize(_ s: String) -> String {
        String(s.lowercased().unicodeScalars.filter { CharacterSet.alphanumerics.contains($0) }.map(Character.init))
    }

    static func isFiller(_ s: String) -> Bool {
        let n = normalize(s)
        return !n.isEmpty && fillerRegex.firstMatch(in: n, range: NSRange(n.startIndex..., in: n)) != nil
    }

    /// A token that is a word: not a `spacing` entry and not punctuation alone.
    private static func isContent(_ w: TimedWord) -> Bool {
        !w.isSpacing && !normalize(w.text).isEmpty
    }

    private static func endsSentence(_ s: String) -> Bool {
        guard let last = s.trimmingCharacters(in: .whitespaces).last else { return false }
        return last == "." || last == "?" || last == "!"
    }

    // MARK: - The report

    struct Pause: Equatable {
        /// Index in the **full** token list of the word after the gap — where a
        /// `[?]` goes.
        let beforeToken: Int
        let start: TimeInterval
        let length: TimeInterval
        let atBoundary: Bool
        /// A shutter or selection press fell in it — the gesture's silence.
        let gesture: Bool
        /// Long enough, for where it is, to be marked.
        let marked: Bool
    }

    struct Verdict: Equatable {
        var hesitant = false
        var tense = false
        /// For the outbox only — never rendered to the agent.
        var why: [String] = []

        /// **The one footer line, or nothing** — the only thing an agent ever
        /// sees of all this besides the `[?]` marks.
        var tag: String? {
            switch (hesitant, tense) {
            case (true, true): return "[voice: hesitant, tense]"
            case (true, false): return "[voice: hesitant]"
            case (false, true): return "[voice: tense]"
            default: return nil
            }
        }
    }

    struct Report {
        let words: Int
        let span: TimeInterval
        let pauses: [Pause]
        let fillers: Int
        let restarts: Int
        /// Words per second of span — `timing.py`'s `rate`, compared with his median.
        let rate: Double?
        /// Words per **voiced** second, when the meter series (or a voiced total)
        /// was there — filed for study, not judged on yet.
        let voicedRate: Double?
        /// Level spread of the voiced hops, dB — tense's energy half.
        let energySpreadDb: Double?
        let verdict: Verdict
        let thresholds: Thresholds
        let language: String?

        var marked: [Pause] { pauses.filter(\.marked) }

        /// The outbox's `affect` (study only; the corpus row gets nothing).
        var json: [String: Any] {
            var o: [String: Any] = [
                // Every gap a listener hears as a pause (≥ 0.4 s), with whether it was marked.
                "pauses": pauses.filter { $0.length >= 0.4 }.map { p -> [String: Any] in
                    var e: [String: Any] = ["at": round2(p.start), "s": round2(p.length), "marked": p.marked]
                    if p.gesture { e["gesture"] = true }
                    if p.atBoundary { e["boundary"] = true }
                    return e
                },
                "words": words, "span": round2(span),
                "fillers": fillers, "restarts": restarts,
                "verdict": verdict.tag.map { $0 as Any } ?? "none",
                "why": verdict.why,
                "thresholds": thresholds.source,
            ]
            o["rate"] = rate.map(round2) ?? NSNull()
            if let v = voicedRate { o["voicedRate"] = round2(v) }
            if let e = energySpreadDb { o["energySpreadDb"] = round2(e) }
            if let l = language { o["language"] = l }
            return o
        }
    }

    private static func round2(_ x: Double) -> Double { (x * 100).rounded() / 100 }

    /// **One sentence, measured.**
    ///
    /// - Parameter words: the recogniser's tokens, `spacing` included (they are
    ///   skipped here and kept in the marked copy).
    /// - Parameter hops: this take's meter series (`MicRecorder.meterHops`), or nil.
    /// - Parameter voicedSeconds: a voiced total to use when there is no series
    ///   (the test route's `"voiced": 12.3`).
    /// - Parameter gestures: seconds from the top of the WAV of every shutter /
    ///   selection press (`ShotMarker.Cue.at`) — same ruler as the words.
    static func analyse(words all: [TimedWord], hops: [MeterHop]? = nil,
                        voicedSeconds: TimeInterval? = nil,
                        language: String? = nil, gestures: [TimeInterval] = [],
                        thresholds given: Thresholds? = nil,
                        tense tenseOn: Bool = VoiceAffect.tenseEnabled) -> Report {
        let t = given ?? thresholds(language: language)
        let lang = language.map(normalizedLanguage)
        let idx = all.indices.filter { isContent(all[$0]) }
        guard let firstI = idx.first, let lastI = idx.last else {
            return Report(words: 0, span: 0, pauses: [], fillers: 0, restarts: 0, rate: nil,
                          voicedRate: nil, energySpreadDb: nil, verdict: Verdict(), thresholds: t,
                          language: lang)
        }
        let span = max(0, all[lastI].end - all[firstI].start)

        // Gaps between consecutive words.
        var pauses: [Pause] = []
        for k in idx.indices.dropFirst() {
            let a = all[idx[k - 1]], b = all[idx[k]]
            let gap = max(0, b.start - a.end)
            let gesture = gestures.contains { $0 >= a.end - t.gestureGuard && $0 <= b.start + t.gestureGuard }
            let boundary = endsSentence(a.text)
            let limit = boundary ? t.boundaryPause : t.longPause
            pauses.append(Pause(beforeToken: idx[k], start: a.end, length: gap, atBoundary: boundary,
                                gesture: gesture, marked: !gesture && gap >= limit))
        }

        // Fillers and restarts.
        let norms = idx.map { normalize(all[$0].text) }
        let fillerFlags = norms.map { !$0.isEmpty && fillerRegex.firstMatch(in: $0, range: NSRange($0.startIndex..., in: $0)) != nil }
        let fillers = fillerFlags.filter { $0 }.count
        var restarts = 0
        if idx.count > 1 {
            for k in 1..<idx.count where !fillerFlags[k] && norms[k] == norms[k - 1]
                && !repeatable.contains(norms[k])
                && all[idx[k]].start - all[idx[k - 1]].start <= t.restartWindow {
                restarts += 1
            }
        }

        let rate: Double? = span > 0 ? Double(idx.count) / span : nil

        // The meter series, clipped to the sentence's speech.
        var voiced = voicedSeconds
        var spread: Double?
        if let hops, !hops.isEmpty {
            let lo = Float(all[firstI].start), hi = Float(all[lastI].end)
            let inSpan = hops.filter { $0.voiced && $0.t >= lo && $0.t <= hi }
            voiced = Double(inSpan.count) * MeterHop.seconds
            if inSpan.count >= t.minVoicedHopsForTense {
                let db = inSpan.map { 20 * log10(Double(max($0.rms, 1e-3))) }
                let mean = db.reduce(0, +) / Double(db.count)
                spread = (db.map { ($0 - mean) * ($0 - mean) }.reduce(0, +) / Double(db.count)).squareRoot()
            }
        }
        let voicedRate: Double? = voiced.flatMap { $0 > 0.5 ? Double(idx.count) / $0 : nil }

        // The verdict.
        var v = Verdict()
        if idx.count >= t.minWords {
            var signals = 0
            let long = pauses.filter(\.marked).count
            let perMinute = span > 0 ? Double(long) / (span / 60) : 0
            if long >= t.minLongPauses && perMinute >= t.longPausesPerMinute {
                signals += 1
                v.why.append(String(format: "%d long pauses in %.0f s", long, span))
            }
            let disfluent = fillers + restarts
            let share = Double(disfluent) / Double(idx.count)
            if disfluent >= t.minDisfluencies && share >= t.disfluencyShare {
                signals += 1
                v.why.append(String(format: "%d fillers + %d restarts in %d words", fillers, restarts, idx.count))
            }
            if let median = t.medianRate, let rate, span >= t.minSpanForRate, rate < t.slowRateFactor * median {
                signals += 1
                v.why.append(String(format: "rate %.2f w/s under %.0f%% of %.2f", rate, t.slowRateFactor * 100, median))
            }
            v.hesitant = signals >= max(1, t.requiredSignals)
        }
        // Tense: the energy half only, behind its flag. Nothing from the words.
        if tenseOn, let spread, spread >= t.tenseEnergySpreadDb {
            v.tense = true
            v.why.append(String(format: "level spread %.1f dB", spread))
        }
        return Report(words: idx.count, span: span, pauses: pauses, fillers: fillers, restarts: restarts,
                      rate: rate, voicedRate: voicedRate, energySpreadDb: spread, verdict: v,
                      thresholds: t, language: lang)
    }

    // MARK: - The marks

    static let mark = "[?]"

    /// **The tokens with a `[?]` in front of the word after every marked pause.**
    ///
    /// Inserted as tokens, not into a string, so `ShotMarker.place` sees them as
    /// words and can never put one inside a marker; timed at the gap's start, so
    /// a press in that gap would still land after it — and a gap with a press in
    /// it is never marked anyway (`gestureGuard`). The spacing is taken from the
    /// neighbours: Scribe's `spacing` tokens (`pentru`, ` `, `[?] `, `clienți`)
    /// and Whisper-style leading spaces (`pentru`, ` [?]`, ` clienți`) both come
    /// out as `pentru [?] clienți`.
    static func marked(words all: [TimedWord], report: Report) -> [TimedWord] {
        // Word index after the gap → the gap's start (the word before's end).
        let at = Dictionary(report.marked.map { ($0.beforeToken, $0.start) }, uniquingKeysWith: { a, _ in a })
        guard !at.isEmpty else { return all }
        var out: [TimedWord] = []
        out.reserveCapacity(all.count + at.count)
        var sofar = ""
        for (i, w) in all.enumerated() {
            if let t = at[i] {
                let lead = (sofar.last?.isWhitespace ?? true) ? "" : " "
                let trail = (w.text.first?.isWhitespace ?? false) ? "" : " "
                out.append(TimedWord(text: lead + mark + trail, start: t, end: t, isSpacing: false))
                sofar += lead + mark + trail
            }
            out.append(w)
            sofar += w.text
        }
        return out
    }

    /// **The delivered text with the marks in**, or nil when the words do not
    /// spell the text (whitespace aside) — a partial `words[]` must not replace
    /// the transcript, so that sentence goes unmarked and says so in the log.
    static func markedText(text: String, words all: [TimedWord], marked: [TimedWord]) -> String? {
        func squash(_ s: String) -> String {
            s.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
        }
        guard squash(all.map(\.text).joined()) == squash(text) else { return nil }
        return marked.map(\.text).joined().trimmingCharacters(in: .whitespacesAndNewlines)
    }

    // MARK: - The desk

    /// `POST /test/affect` — `{"words": [{text, start, end, type?}], "voiced"?:
    /// seconds | [{t, rms, voiced}], "language"?, "gestures"?: [s],
    /// "thresholds"?: {…}, "tense"?: bool}` → the verdict, the marked text and
    /// the report, with nothing recorded, dictated or delivered.
    static func test(_ body: [String: Any]) -> [String: Any] {
        let words: [TimedWord] = ((body["words"] as? [[String: Any]]) ?? []).compactMap {
            guard let text = $0["text"] as? String,
                  let start = ($0["start"] as? NSNumber)?.doubleValue,
                  let end = ($0["end"] as? NSNumber)?.doubleValue else { return nil }
            return TimedWord(text: text, start: start, end: end,
                             isSpacing: ($0["type"] as? String) == "spacing")
        }
        var hops: [MeterHop]?
        var voiced: TimeInterval?
        if let n = body["voiced"] as? NSNumber { voiced = n.doubleValue }
        if let list = body["voiced"] as? [[String: Any]] {
            hops = list.compactMap {
                guard let t = ($0["t"] as? NSNumber)?.floatValue else { return nil }
                return MeterHop(t: t, rms: ($0["rms"] as? NSNumber)?.floatValue ?? 0,
                                voiced: ($0["voiced"] as? Bool) ?? true)
            }
        }
        let language = body["language"] as? String
        var t = thresholds(language: language)
        if let o = body["thresholds"] as? [String: Any] { t.apply(o); t.source += " + request" }
        let gestures = ((body["gestures"] as? [NSNumber]) ?? []).map(\.doubleValue)
        let report = analyse(words: words, hops: hops, voicedSeconds: voiced, language: language,
                             gestures: gestures, thresholds: t,
                             tense: (body["tense"] as? Bool) ?? tenseEnabled)
        let markedWords = marked(words: words, report: report)
        let text = markedWords.map(\.text).joined().trimmingCharacters(in: .whitespacesAndNewlines)
        return ["enabled": isEnabled, "tenseEnabled": tenseEnabled,
                "hesitant": report.verdict.hesitant, "tense": report.verdict.tense,
                "tag": report.verdict.tag ?? NSNull(), "text": text,
                "marks": report.marked.count, "affect": report.json, "thresholds": t.json,
                "file": fileURL.path]
    }
}
