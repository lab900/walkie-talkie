import XCTest
@testable import WalkieTalkie

/// `VoiceAffect`, the pure half (2026-09-27): where a `[?]` goes, when a
/// sentence is `[voice: hesitant]`, and that a fluent one carries nothing.
/// Thresholds are always passed explicitly, so a `~/.walkie-talkie/voice-affect.json`
/// on this Mac cannot change a verdict here.
final class VoiceAffectTests: XCTestCase {

    /// Scribe's shape: a word, then a `spacing` token spanning the gap to the next.
    private func scribe(_ said: [(String, Double, Double)]) -> [TimedWord] {
        var out: [TimedWord] = []
        for (i, w) in said.enumerated() {
            out.append(TimedWord(text: w.0, start: w.1, end: w.2, isSpacing: false))
            if i + 1 < said.count {
                out.append(TimedWord(text: " ", start: w.2, end: said[i + 1].1, isSpacing: true))
            }
        }
        return out
    }

    /// Evenly spoken words, `gap` apart, starting at 0.2 s.
    private func even(_ text: String, word: Double = 0.3, gap: Double = 0.12) -> [(String, Double, Double)] {
        var t = 0.2
        return text.split(separator: " ").map { w in
            defer { t += word + gap }
            return (String(w), t, t + word)
        }
    }

    private let defaults = VoiceAffect.Thresholds()

    private func text(_ words: [TimedWord]) -> String {
        words.map(\.text).joined().trimmingCharacters(in: .whitespaces)
    }

    // MARK: - Fixture 1: fluent

    func testFluentSentenceHasNoTagAndNoMarks() {
        let words = scribe(even("fă un endpoint pentru clienți care întoarce lista paginată după nume"))
        let r = VoiceAffect.analyse(words: words, thresholds: defaults, tense: false)
        XCTAssertFalse(r.verdict.hesitant)
        XCTAssertNil(r.verdict.tag)
        XCTAssertTrue(r.marked.isEmpty)
        XCTAssertEqual(r.fillers, 0)
        XCTAssertEqual(r.restarts, 0)
        XCTAssertEqual(text(VoiceAffect.marked(words: words, report: r)), text(words))
        XCTAssertEqual(r.verdict.why, [])
    }

    // MARK: - Fixture 2: hesitant, with fillers and long pauses

    func testHesitantWithFillersAndPauses() {
        let said: [(String, Double, Double)] = [
            ("fă", 0.2, 0.4), ("un", 0.5, 0.6), ("endpoint", 0.7, 1.2), ("pentru…", 1.3, 1.8),
            ("ăăă", 3.4, 3.9),                          // 1.6 s pause before the filler
            ("clienți,", 4.0, 4.5), ("cred,", 4.6, 4.9),
            ("sau", 6.5, 6.7),                          // 1.6 s pause
            ("mmm", 6.8, 7.2), ("poate", 7.3, 7.6), ("comenzi.", 7.7, 8.2),
        ]
        let words = scribe(said)
        let r = VoiceAffect.analyse(words: words, thresholds: defaults, tense: false)
        XCTAssertEqual(r.fillers, 2)
        XCTAssertEqual(r.marked.count, 2)
        XCTAssertTrue(r.verdict.hesitant)
        XCTAssertEqual(r.verdict.tag, "[voice: hesitant]")
        // The marks sit between the two words around each pause, and nowhere else.
        let marked = VoiceAffect.marked(words: words, report: r)
        XCTAssertEqual(text(marked), "fă un endpoint pentru… [?] ăăă clienți, cred, [?] sau mmm poate comenzi.")
        // The tag is the only thing the agent sees — never a number.
        XCTAssertFalse(r.verdict.tag!.contains(where: \.isNumber))
    }

    // MARK: - Fixture 3: restarts

    func testRestartsAreCountedButEmphasisIsNot() {
        let said: [(String, Double, Double)] = [
            ("vreau", 0.2, 0.5), ("vreau", 0.7, 1.0), ("să", 1.1, 1.2), ("să", 1.3, 1.4),
            ("mut", 1.5, 1.8), ("the", 1.9, 2.0), ("the", 2.1, 2.2), ("butonul", 2.3, 2.8),
            ("foarte", 2.9, 3.2), ("foarte", 3.3, 3.6), ("sus", 3.7, 4.0),
        ]
        let r = VoiceAffect.analyse(words: scribe(said), thresholds: defaults, tense: false)
        XCTAssertEqual(r.restarts, 3)            // vreau vreau, să să, the the — not foarte foarte
        XCTAssertEqual(r.fillers, 0)
        XCTAssertTrue(r.marked.isEmpty)          // no pause long enough to mark
        // 3 disfluencies in 11 words ≥ 8 % is one signal: not a verdict by default (2 needed)…
        XCTAssertFalse(r.verdict.hesitant)
        XCTAssertEqual(r.verdict.why.count, 1)
        // …and the verdict with one required.
        var one = defaults
        one.requiredSignals = 1
        XCTAssertTrue(VoiceAffect.analyse(words: scribe(said), thresholds: one, tense: false).verdict.hesitant)
    }

    func testAWordRepeatedAfterTheWindowIsNotARestart() {
        let said: [(String, Double, Double)] = [("merge", 0.2, 0.5), ("merge", 2.2, 2.5)]
        let r = VoiceAffect.analyse(words: scribe(said), thresholds: defaults, tense: false)
        XCTAssertEqual(r.restarts, 0)
    }

    // MARK: - Where a `[?]` may and may not go

    func testOnePauseMarksButDoesNotMakeAVerdict() {
        var said = even("fă un endpoint pentru")
        said.append(("clienți", 3.5, 3.9))       // one 1.9 s pause
        said.append(("mâine", 4.0, 4.3))
        let words = scribe(said)
        let r = VoiceAffect.analyse(words: words, thresholds: defaults, tense: false)
        XCTAssertEqual(r.marked.count, 1)
        XCTAssertFalse(r.verdict.hesitant)       // minLongPauses 2
        XCTAssertEqual(text(VoiceAffect.marked(words: words, report: r)), "fă un endpoint pentru [?] clienți mâine")
    }

    func testAPauseWithAGestureInItIsNotMarked() {
        let said: [(String, Double, Double)] = [("uite", 0.2, 0.5), ("aici", 3.0, 3.3)]
        let r = VoiceAffect.analyse(words: scribe(said), gestures: [1.4], thresholds: defaults, tense: false)
        XCTAssertTrue(r.marked.isEmpty)
        XCTAssertTrue(r.pauses[0].gesture)
    }

    func testABreathBetweenSentencesNeedsTheBoundaryThreshold() {
        let short: [(String, Double, Double)] = [("Gata.", 0.2, 0.5), ("Acum", 2.0, 2.3)]   // 1.5 s
        XCTAssertTrue(VoiceAffect.analyse(words: scribe(short), thresholds: defaults, tense: false).marked.isEmpty)
        let long: [(String, Double, Double)] = [("Gata.", 0.2, 0.5), ("Acum", 2.7, 3.0)]    // 2.2 s
        XCTAssertEqual(VoiceAffect.analyse(words: scribe(long), thresholds: defaults, tense: false).marked.count, 1)
        // An ellipsis is trailing off, not a boundary.
        let trail: [(String, Double, Double)] = [("pentru…", 0.2, 0.5), ("clienți", 2.0, 2.3)]
        XCTAssertEqual(VoiceAffect.analyse(words: scribe(trail), thresholds: defaults, tense: false).marked.count, 1)
    }

    func testWhisperStyleLeadingSpacesAreMarkedCleanly() {
        let words = [TimedWord(text: "pentru", start: 0.2, end: 0.5, isSpacing: false),
                     TimedWord(text: " clienți", start: 2.0, end: 2.4, isSpacing: false)]
        let r = VoiceAffect.analyse(words: words, thresholds: defaults, tense: false)
        XCTAssertEqual(text(VoiceAffect.marked(words: words, report: r)), "pentru [?] clienți")
    }

    func testMarksNeverLandInsideAShotMarker() {
        // A press in the long gap: excused, so the marker goes in alone.
        let said: [(String, Double, Double)] = [("uite", 0.2, 0.5), ("aici", 3.0, 3.3), ("jos", 3.4, 3.7),
                                                 ("apoi", 5.5, 5.8)]
        let words = scribe(said)
        let r = VoiceAffect.analyse(words: words, gestures: [1.5], thresholds: defaults, tense: false)
        let marked = VoiceAffect.marked(words: words, report: r)
        let placed = ShotMarker.place(words: marked, cues: [ShotMarker.Cue(kind: .shot, index: 1, at: 1.5)],
                                      shots: [1: "[📸1]"])
        XCTAssertEqual(placed.text, "uite [📸1] aici jos [?] apoi")
    }

    // MARK: - Rate, and what is off without data

    func testRateSignalIsOffUntilHisMedianIsKnown() {
        // Slow, evenly: 8 words over ~9 s, no long pause (each gap 0.9 s), no fillers.
        let words = scribe(even("aș vrea să văd lista de clienți azi", word: 0.25, gap: 0.9))
        XCTAssertFalse(VoiceAffect.analyse(words: words, thresholds: defaults, tense: false).verdict.hesitant)
        var t = defaults
        t.medianRate = 2.5
        t.requiredSignals = 1                    // the rate alone, to see it fire
        let r = VoiceAffect.analyse(words: words, thresholds: t, tense: false)
        XCTAssertTrue(r.verdict.hesitant)
        XCTAssertEqual(r.verdict.why.count, 1)
    }

    func testRequiredSignalsTwoNeedsTwo() {
        var t = defaults
        t.requiredSignals = 2
        let said: [(String, Double, Double)] = [
            ("vreau", 0.2, 0.5), ("vreau", 0.7, 1.0), ("să", 1.1, 1.2), ("să", 1.3, 1.4),
            ("mut", 1.5, 1.8), ("butonul", 2.3, 2.8), ("sus", 3.7, 4.0),
        ]
        XCTAssertFalse(VoiceAffect.analyse(words: scribe(said), thresholds: t, tense: false).verdict.hesitant)
    }

    // MARK: - Tense: the energy half, behind its flag

    func testTenseIsNeverRaisedWithTheFlagOff() {
        let words = scribe(even("de ce nu merge nici acum asta"))
        let hops = (0..<60).map { i in MeterHop(t: Float(0.2 + Double(i) * 0.064),
                                                 rms: i % 2 == 0 ? 200 : 8000, voiced: true) }
        let off = VoiceAffect.analyse(words: words, hops: hops, thresholds: defaults, tense: false)
        XCTAssertFalse(off.verdict.tense)
        XCTAssertNotNil(off.energySpreadDb)      // measured and filed all the same
        let on = VoiceAffect.analyse(words: words, hops: hops, thresholds: defaults, tense: true)
        XCTAssertTrue(on.verdict.tense)
        XCTAssertEqual(on.verdict.tag, "[voice: tense]")
    }

    // MARK: - Text, fillers, the file

    func testMarkedTextRefusesWordsThatDoNotSpellTheTranscript() {
        let said: [(String, Double, Double)] = [("pentru", 0.2, 0.5), ("clienți", 2.0, 2.4)]
        let words = scribe(said)
        let r = VoiceAffect.analyse(words: words, thresholds: defaults, tense: false)
        let marked = VoiceAffect.marked(words: words, report: r)
        XCTAssertEqual(VoiceAffect.markedText(text: "pentru clienți", words: words, marked: marked),
                       "pentru [?] clienți")
        XCTAssertNil(VoiceAffect.markedText(text: "pentru clienți și comenzi", words: words, marked: marked))
    }

    func testFillersAreSoundsNotWords() {
        for f in ["ăăă", "Ăă,", "mmm", "hm", "um", "Uh.", "erm", "îî", "aa", "ăhm"] {
            XCTAssertTrue(VoiceAffect.isFiller(f), f)
        }
        for w in ["a", "e", "deci", "adică", "like", "so", "am", "are", "era", "ah"] {
            XCTAssertFalse(VoiceAffect.isFiller(w), w)
        }
    }

    func testTheFileIsLayeredAndReadPerLanguage() {
        let obj: [String: Any] = [
            "thresholds": ["longPause": 1.3, "requiredSignals": 3],
            "ro": ["gaps": ["p97": 2.05], "rate": ["p10": 1.6, "p50": 2.4], "thresholds": ["boundaryPause": 2.4]],
            "en": ["rate": ["p50": 2.8]],
        ]
        let ro = VoiceAffect.load(from: obj, language: "ron")
        XCTAssertEqual(ro.longPause, 2.05)       // a p97 over the floor is taken as-is
        XCTAssertEqual(ro.medianRate, 2.4)
        XCTAssertEqual(ro.boundaryPause, 2.4)
        XCTAssertEqual(ro.requiredSignals, 3)
        XCTAssertEqual(ro.source, "file + ro.gaps.p97 + ro.rate.p50 + ro.thresholds")
        let en = VoiceAffect.load(from: obj, language: "en")
        XCTAssertEqual(en.longPause, 1.3)        // no gaps block → the hand override
        XCTAssertEqual(en.medianRate, 2.8)
        XCTAssertEqual(VoiceAffect.load(from: [:], language: nil), VoiceAffect.Thresholds())
    }

    /// His real p97s (0.94 s RO, 0.54 s EN) are low only because most gaps are 0:
    /// the threshold is max(p97, 1.5 s), and it takes two signals.
    func testALowP97IsFlooredAndTwoSignalsAreTheDefault() {
        XCTAssertEqual(defaults.longPause, 1.5)
        XCTAssertEqual(defaults.requiredSignals, 2)
        let obj: [String: Any] = ["ro": ["gaps": ["p97": 0.94], "rate": ["p50": 2.3]],
                                  "en": ["gaps": ["p97": 0.54]]]
        let ro = VoiceAffect.load(from: obj, language: "ro")
        XCTAssertEqual(ro.longPause, 1.5)
        XCTAssertEqual(ro.requiredSignals, 2)
        XCTAssertEqual(ro.source, "ro.gaps.p97 (floored) + ro.rate.p50")
        XCTAssertEqual(VoiceAffect.load(from: obj, language: "en").longPause, 1.5)
        // A 1.2 s gap is no longer a `[?]`; 1.5 s is.
        let short = scribe([("pentru", 0.2, 0.5), ("clienți", 1.7, 2.0)])
        XCTAssertTrue(VoiceAffect.analyse(words: short, thresholds: ro, tense: false).marked.isEmpty)
        let long = scribe([("pentru", 0.2, 0.5), ("clienți", 2.0, 2.3)])
        XCTAssertEqual(VoiceAffect.analyse(words: long, thresholds: ro, tense: false).marked.count, 1)
    }

    func testTheOutboxRecordStaysStudyShaped() {
        let said: [(String, Double, Double)] = [("pentru", 0.2, 0.5), ("clienți", 2.0, 2.4)]
        let json = VoiceAffect.analyse(words: scribe(said), thresholds: defaults, tense: false).json
        XCTAssertEqual(json["verdict"] as? String, "none")
        XCTAssertEqual((json["pauses"] as? [[String: Any]])?.count, 1)
        XCTAssertNotNil(json["fillers"])
        XCTAssertNotNil(json["rate"])
    }
}
