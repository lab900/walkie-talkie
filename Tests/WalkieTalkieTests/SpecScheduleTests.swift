import XCTest
@testable import WalkieTalkie

/// The local transcript prepared ahead (2026-09-29): started `budget − localEta`
/// after the close, held, offered on the row, **never inserted by the clock** —
/// `AutoLocal.specStart` / `shouldStart` / `row` and the `📊 fallback:` trace.
final class SpecScheduleTests: XCTestCase {

    func testTheDecodeStartsLocalEtaBeforeTheBudget() {
        // Victor's example: a 6 s p95 and a ~3 s local decode → start around 3 s.
        XCTAssertEqual(AutoLocal.specStart(budget: 6, localEta: 3), 3, accuracy: 1e-9)
        XCTAssertEqual(AutoLocal.localEta(typical: 0.8), 1.1, accuracy: 1e-9)   // + the 0.3 s margin
        XCTAssertEqual(AutoLocal.specStart(budget: 4.2, localEta: AutoLocal.localEta(typical: 0.8)), 3.1, accuracy: 1e-9)
    }

    func testALocalEtaAtOrOverTheBudgetStartsAtTheClose() {
        XCTAssertEqual(AutoLocal.specStart(budget: 2.5, localEta: 2.5), 0, accuracy: 1e-9)
        XCTAssertEqual(AutoLocal.specStart(budget: 10, localEta: 19), 0, accuracy: 1e-9)   // a long take
        XCTAssertTrue(AutoLocal.shouldStart(elapsed: 0, startAt: 0, phase: .planned, wavKnown: true))
    }

    func testOnlyAPlannedDecodeWithItsWavStartsAndOnlyFromItsStartTime() {
        XCTAssertFalse(AutoLocal.shouldStart(elapsed: 2.9, startAt: 3, phase: .planned, wavKnown: true))
        XCTAssertTrue(AutoLocal.shouldStart(elapsed: 3.0, startAt: 3, phase: .planned, wavKnown: true))
        XCTAssertFalse(AutoLocal.shouldStart(elapsed: 9, startAt: 3, phase: .planned, wavKnown: false))   // no WAV yet
        for p in [AutoLocal.SpecPhase.running, .ready, .failed, .skipped, .discarded] {
            XCTAssertFalse(AutoLocal.shouldStart(elapsed: 99, startAt: 0, phase: p, wavKnown: true), p.rawValue)   // never twice
        }
    }

    func testTheRowWaitsForTheWordsWhenADecodeIsPlanned() {
        // With a decode planned: no row until it is ready — however long the wait.
        for p in [AutoLocal.SpecPhase.planned, .running, .failed, .skipped, .discarded] {
            XCTAssertEqual(AutoLocal.row(waiting: true, pastDelay: true, spec: p).shown, false, p.rawValue)
        }
        XCTAssertEqual(AutoLocal.row(waiting: true, pastDelay: false, spec: .ready).shown, true)
        XCTAssertEqual(AutoLocal.row(waiting: true, pastDelay: false, spec: .ready).ready, true)
        // The words landed: the row goes, whatever the decode did.
        XCTAssertEqual(AutoLocal.row(waiting: false, pastDelay: true, spec: .ready).shown, false)
        // No decode planned (checkbox off, a sentence never armed): ⌘⌃X's plain row after a second.
        XCTAssertEqual(AutoLocal.row(waiting: true, pastDelay: false, spec: nil).shown, false)
        XCTAssertEqual(AutoLocal.row(waiting: true, pastDelay: true, spec: nil).shown, true)
        XCTAssertEqual(AutoLocal.row(waiting: true, pastDelay: true, spec: nil).ready, false)
    }

    private func budget(_ seconds: Double, samples: Int = 100, engine: String = DecodeRate.wisprFlow) -> DecodeRate.Budget {
        DecodeRate.Budget(seconds: seconds, unclamped: seconds, samples: samples, cap: 10, engine: engine, audio: 12.3)
    }

    func testTheTraceLineHasEveryFieldFromTheClose() {
        var t = AutoLocal.Trace(budget: budget(4.2), localEta: 1.1)
        XCTAssertEqual(t.specPlanned, 3.1, accuracy: 1e-9)
        t.specStart = 3.12; t.localReady = 4.0; t.budgetExpired = 4.21; t.engineAnswer = 20.5
        t.outcome = "engine"; t.toWords = 20.6
        t.wasted = AutoLocal.Trace.wasted(specStarted: true, outcome: "engine")
        XCTAssertEqual(t.logLine,
                       "📊 fallback: engine=wispr-flow audio=12.3 budget=4.20(p95,n=100) localEta=1.10 specStart=3.12 "
                       + "localReady=4.00 engineAnswer=20.50 budgetExpired=4.21 outcome=engine wasted=true toWords=20.60")
        let j = t.json
        XCTAssertEqual(j["outcome"] as? String, "engine")
        XCTAssertEqual(j["wasted"] as? Bool, true)
        XCTAssertEqual(j["quantile"] as? Double, 0.95)
        XCTAssertEqual(j["localReady"] as? Double, 4.0)
        XCTAssertNotNil(try? JSONSerialization.data(withJSONObject: j))
    }

    func testNeverIsWrittenForWhatDidNotHappen() {
        var t = AutoLocal.Trace(budget: budget(2.0, samples: 7, engine: DecodeRate.elevenLabs), localEta: 0.9)
        t.outcome = "engine"; t.engineAnswer = 1.2; t.toWords = 1.25
        XCTAssertTrue(t.logLine.contains("specStart=never localReady=never engineAnswer=1.20 budgetExpired=never"), t.logLine)
        XCTAssertTrue(t.logLine.contains("budget=2.00(p95,n=7)"), t.logLine)
        XCTAssertTrue(t.json["specStart"] is NSNull)
    }

    func testWastedIsADecodeThatRanForWordsThatWereNotTheLocalOnes() {
        XCTAssertTrue(AutoLocal.Trace.wasted(specStarted: true, outcome: "engine"))
        XCTAssertTrue(AutoLocal.Trace.wasted(specStarted: true, outcome: "cancelled"))
        XCTAssertFalse(AutoLocal.Trace.wasted(specStarted: true, outcome: "local-forced"))
        XCTAssertFalse(AutoLocal.Trace.wasted(specStarted: true, outcome: "local-fallback"))
        XCTAssertFalse(AutoLocal.Trace.wasted(specStarted: false, outcome: "engine"))
    }

    func testTheOutcomeOfADelivery() {
        XCTAssertEqual(AutoLocal.Trace.outcome(via: "local-forced"), "local-forced")
        XCTAssertEqual(AutoLocal.Trace.outcome(via: "local-fallback"), "local-fallback")
        XCTAssertEqual(AutoLocal.Trace.outcome(via: "elevenlabs-scribe"), "engine")
        XCTAssertEqual(AutoLocal.Trace.outcome(via: "wispr-history"), "engine")
        XCTAssertEqual(AutoLocal.Trace.outcome(via: nil), "engine")
    }
}
