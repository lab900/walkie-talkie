import XCTest
@testable import WalkieTalkie

/// `BridgePacer` (2026-09-29): the held head of a sentence handed to Wispr late,
/// then taken back to live — silence ahead of the first word cut, pauses
/// shortened and 1.1× while lagging, 1.0 once `synced`.
final class BridgePacerTests: XCTestCase {

    private let hop = 0.085   // one recorder buffer, 1365 frames at 16 kHz

    private func chunks(_ pattern: String) -> [(seconds: TimeInterval, voiced: Bool)] {
        pattern.map { (hop, $0 == "v") }
    }

    func testTrimKeepsThePadAheadOfTheFirstWord() {
        // 10 silent buffers (0.85 s of reaction time), then speech.
        let c = chunks("ssssssssss" + "vvvv")
        let first = BridgePacer.trimStart(c, pad: 0.3)
        XCTAssertEqual(first, 6, "0.3 s = 4 buffers of 85 ms kept before the first voiced one")
        XCTAssertTrue(c[first...].contains { $0.voiced })
    }

    func testTrimWithSpeechAtTheTopKeepsEverything() {
        XCTAssertEqual(BridgePacer.trimStart(chunks("vvss"), pad: 0.3), 0)
    }

    func testTrimWithNoSpeechYetKeepsOnlyTheTail() {
        let c = chunks("ssssssssss")
        XCTAssertEqual(BridgePacer.trimStart(c, pad: 0.3), 6)
        XCTAssertEqual(BridgePacer.trimStart([], pad: 0.3), 0)
    }

    func testPausesAreShortenedOnlyWhileLagging() {
        var p = BridgePacer()
        XCTAssertTrue(p.admit(seconds: hop, voiced: true, lag: 1))
        // A pause while 1 s behind: the first 0.25 s is kept, the rest dropped.
        let kept = (0..<10).filter { _ in p.admit(seconds: hop, voiced: false, lag: 1) }.count
        XCTAssertEqual(kept, 2, "85 ms × 3 = 0.255 s is past keptGap — the third is dropped")
        XCTAssertEqual(p.dropped, hop * 8, accuracy: 1e-9)
        // Live: the same pause is played whole.
        var live = BridgePacer()
        XCTAssertTrue((0..<10).allSatisfy { _ in live.admit(seconds: hop, voiced: false, lag: 0.1) })
        XCTAssertEqual(live.dropped, 0)
    }

    func testSpeechIsNeverDropped() {
        var p = BridgePacer()
        _ = (0..<10).map { _ in p.admit(seconds: hop, voiced: false, lag: 5) }
        XCTAssertTrue(p.admit(seconds: hop, voiced: true, lag: 5))
        XCTAssertEqual(p.silentRun, 0)
    }

    func testRateRampsWithTheLagUpToTheCeiling() {
        var t = BridgePacer.Tuning()
        t.maxRate = 1.5; t.rampLag = 3
        let p = BridgePacer(tuning: t)
        XCTAssertEqual(p.rate(lag: 0.2), 1.0)
        XCTAssertEqual(p.rate(lag: 0.21), 1.1, accuracy: 0.01, "just behind: the old catch-up rate")
        XCTAssertEqual(p.rate(lag: 1.6), 1.3, accuracy: 0.001, "half-way up the ramp")
        XCTAssertEqual(p.rate(lag: 3), 1.5, accuracy: 0.001)
        XCTAssertEqual(p.rate(lag: 9), 1.5, "never past what Wispr tolerates — the rest drains after the stop")
    }

    func testRateIsFasterOnlyAboveSynced() {
        let p = BridgePacer()
        XCTAssertEqual(p.rate(lag: 1.0), 1.1)
        XCTAssertEqual(p.rate(lag: 0.21), 1.1)
        XCTAssertEqual(p.rate(lag: 0.2), 1.0)
        XCTAssertEqual(p.rate(lag: 0.085), 1.0, "one buffer queued is live — faster would starve the player mid-word")
    }
}
