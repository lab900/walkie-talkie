import XCTest
@testable import WalkieTalkie

/// `ZeroPeakWatch` (2026-09-28, wave 3's finding A): buffers flowing, every
/// sample 0, before the take's first sound → a restart after 1 s, at most three,
/// then *gave up* (the take stays DEAF). Driven over a timeline: a buffer every
/// 85 ms (Loopback/BlackHole: 4096 frames at 48 kHz), the watchdog's beat every
/// 0.5 s from 1.0 s, as `MicRecorder.watchForSilentEngine` schedules it.
final class ZeroPeakWatchTests: XCTestCase {

    private let hop = 4096.0 / 48000.0

    /// Runs `until` seconds: `peak(t)` is each buffer's peak (nil = no buffer),
    /// the beat ticks at 1.0, 1.5, 2.0 … Returns every event with its time.
    private func run(until end: Double, peak: (Double) -> Int?) -> [(t: Double, e: ZeroPeakWatch.Event)] {
        var w = ZeroPeakWatch()
        var out: [(Double, ZeroPeakWatch.Event)] = []
        var nextBuffer = hop, nextBeat = 1.0
        while min(nextBuffer, nextBeat) <= end {
            if nextBuffer <= nextBeat {
                if let p = peak(nextBuffer) { w.buffer(at: nextBuffer, peak: p) }
                nextBuffer += hop
            } else {
                if let e = w.tick(at: nextBeat) {
                    out.append((nextBeat, e))
                    if case .restart = e { w.tapRestarted(at: nextBeat) }
                }
                nextBeat += 0.5
            }
        }
        return out
    }

    private func steps(_ events: [(t: Double, e: ZeroPeakWatch.Event)]) -> [Int] {
        events.compactMap { if case let .restart(step, _, _) = $0.e { return step }; return nil }
    }

    /// The VM's DEAF take: 105 buffers, peak 0. Three restarts, ≥ 1 s apart,
    /// then gave up — and nothing after that.
    func testAllZerosRestartsThreeTimesThenGivesUp() {
        let ev = run(until: 9) { _ in 0 }
        XCTAssertEqual(steps(ev), [1, 2, 3])
        let times = ev.map(\.t)
        for (a, b) in zip(times, times.dropFirst()) { XCTAssertGreaterThanOrEqual(b - a, 1.0) }
        guard case let .gaveUp(restarts, buffers, seconds)? = ev.last?.e else { return XCTFail("no gaveUp: \(ev)") }
        XCTAssertEqual(restarts, 3)
        XCTAssertGreaterThan(buffers, 40)
        XCTAssertGreaterThan(seconds, 3.5)
        XCTAssertEqual(ev.count, 4)
        if case let .restart(_, buffers, seconds) = ev[0].e {
            XCTAssertGreaterThanOrEqual(buffers, 11)       // 1 s of 85 ms buffers
            XCTAssertGreaterThanOrEqual(seconds, 1.0)
        }
    }

    /// A real microphone: never exact zero. Nothing fires.
    func testNoiseNeverFires() {
        XCTAssertTrue(run(until: 10) { _ in 37 }.isEmpty)
    }

    /// Speech first, then a Loopback gone quiet after its clip: the watch is off
    /// after the first sound — silence after a clip is not a stall.
    func testZerosAfterTheFirstSoundAreNotAStall() {
        XCTAssertTrue(run(until: 10) { t in t < 0.5 ? 9000 : 0 }.isEmpty)
    }

    /// Under a second of zeros before the clip: no restart (every desk case
    /// plays 0.4 s after the microphone opens).
    func testShortLeadInDoesNotFire() {
        XCTAssertTrue(run(until: 6) { t in t < 0.9 ? 0 : 12000 }.isEmpty)
    }

    /// Audio after the first restart: one restart, then `cameBack` with the
    /// buffer's peak and how long after the restart it arrived; nothing more.
    func testCameBackAfterRestartOne() {
        let ev = run(until: 8) { t in t < 1.6 ? 0 : 16000 }
        XCTAssertEqual(steps(ev), [1])
        guard ev.count == 2, case let .cameBack(step, peak, after) = ev[1].e else { return XCTFail("\(ev)") }
        XCTAssertEqual(step, 1)
        XCTAssertEqual(peak, 16000)
        XCTAssertLessThan(after, 0.5)
    }

    /// Audio after the second restart (the engine rebuild): steps 1, 2, then back.
    func testCameBackAfterTheRebuild() {
        let ev = run(until: 8) { t in t < 3.1 ? 0 : 500 }
        XCTAssertEqual(steps(ev), [1, 2])
        guard case let .cameBack(step, _, _)? = ev.last?.e else { return XCTFail("\(ev)") }
        XCTAssertEqual(step, 2)
    }

    /// No buffers at all is the missing-buffer watchdog's, not this one's: a
    /// window never opens without buffers, and one that stopped flowing
    /// (last buffer ≥ 0.5 s ago) does not fire.
    func testNoBuffersOrAGapIsNotThisWatch() {
        XCTAssertTrue(run(until: 6) { _ in nil }.isEmpty)
        XCTAssertTrue(run(until: 6) { t in t < 0.3 ? 0 : nil }.isEmpty)
    }

    /// A tap restart for another reason (configuration change, missing buffer)
    /// opens a fresh window: 1 s of zeros is counted from the buffers after it.
    func testAnotherRestartOpensAFreshWindow() {
        var w = ZeroPeakWatch()
        var t = 0.0
        while t < 0.9 { t += hop; w.buffer(at: t, peak: 0) }
        w.tapRestarted(at: t)
        let restartAt = t
        while t < restartAt + 0.9 { t += hop; w.buffer(at: t, peak: 0) }
        XCTAssertNil(w.tick(at: t))                 // 1.8 s of zeros, but only 0.9 s since the restart
        while t < restartAt + 1.1 { t += hop; w.buffer(at: t, peak: 0) }
        guard case .restart(1, _, _)? = w.tick(at: t) else { return XCTFail("expected restart 1") }
    }
}
