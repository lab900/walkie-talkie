import XCTest
@testable import WalkieTalkie

/// `WisprOwnership` — the firewall's tail keyed on rows, not the clock
/// (B, lab wave 2, 2026-09-28: 8 of his 8 sentences eaten in the 10 s tail).
final class WisprOwnershipTests: XCTestCase {
    let t: Double = 1_000
    func v(since: Double, released: Double, held: Int = 0, foreign: Int64 = 0, now: Double) -> WisprOwnership.Verdict {
        WisprOwnership.verdict(now: now, since: since, releasedAt: released, rowsHeld: held,
                               foreignRow: foreign, tail: 10, ceiling: 660)
    }
    func relays(_ x: WisprOwnership.Verdict) -> Bool { if case .relays = x { return true }; return false }

    func testInFlightIsTheRelays() {
        XCTAssertTrue(relays(v(since: t, released: 0, now: t + 5)))
    }

    func testTailWithoutANewerRowIsTheRelays() {
        XCTAssertTrue(relays(v(since: t, released: t + 5, now: t + 8)))
    }

    func testTailWithHisNewerRowPasses() {
        let x = v(since: t, released: t + 5, foreign: 42, now: t + 8)
        XCTAssertFalse(relays(x))
        XCTAssertEqual(x, .passes("row 42 is newer than the relay's — his own sentence"))
    }

    func testPastTheTailPasses() {
        XCTAssertFalse(relays(v(since: t, released: t + 5, now: t + 16)))
    }

    func testAHeldRowStillDropsWithNoRowOfHis() {
        // The relay's given-up row can still paste late: dropped, and the claim asks the rows.
        XCTAssertTrue(relays(v(since: t, released: t + 5, held: 1, foreign: 0, now: t + 8)))
    }

    func testNeverOwnedPasses() {
        XCTAssertFalse(relays(v(since: 0, released: 0, now: t)))
    }

    func testHisRowNeedsToBeNewerThanTheFloor() {
        XCTAssertFalse(WisprOwnership.rowIsHis(rowid: 10, startedAt: t, floor: 10, relayHadRow: true,
                                               relayClosedAt: t - 5, relayCmdVSeen: true, sinceRelease: 3))
        XCTAssertTrue(WisprOwnership.rowIsHis(rowid: 11, startedAt: t, floor: 10, relayHadRow: true,
                                              relayClosedAt: t - 5, relayCmdVSeen: true, sinceRelease: 3))
    }

    func testTheRelaysOwnPasteMayStillBeComing() {
        // Neither its ⌘V seen nor 1.5 s since idle: not yet his.
        XCTAssertFalse(WisprOwnership.rowIsHis(rowid: 11, startedAt: t, floor: 10, relayHadRow: true,
                                               relayClosedAt: t - 5, relayCmdVSeen: false, sinceRelease: 0.4))
        XCTAssertTrue(WisprOwnership.rowIsHis(rowid: 11, startedAt: t, floor: 10, relayHadRow: true,
                                              relayClosedAt: t - 5, relayCmdVSeen: false, sinceRelease: 1.6))
    }

    func testWithNoRelayRowALateRowFromBeforeTheCloseIsNotHis() {
        // A cold Wispr may create the relay's row late: it started before the relay's close.
        XCTAssertFalse(WisprOwnership.rowIsHis(rowid: 11, startedAt: t - 3, floor: 10, relayHadRow: false,
                                               relayClosedAt: t - 1.2, relayCmdVSeen: false, sinceRelease: 4))
        XCTAssertTrue(WisprOwnership.rowIsHis(rowid: 11, startedAt: t, floor: 10, relayHadRow: false,
                                              relayClosedAt: t - 1.2, relayCmdVSeen: false, sinceRelease: 4))
    }

    /// B2 (lab wave 3): a noted row of his passes even while older relay rows are held.
    func testHisNotedRowOutranksHeldRows() {
        XCTAssertFalse(relays(v(since: t, released: t + 6, held: 3, foreign: 130, now: t + 12)))
        XCTAssertFalse(relays(v(since: t, released: t + 6, held: 1, foreign: 130, now: t + 30)))
        XCTAssertTrue(relays(v(since: t, released: t + 6, held: 1, foreign: 0, now: t + 30)))
    }

    // MARK: B-risk (TX6b): a row the relay's own chord made is not his

    func testARowWithinASecondOfARelayChordIsTheRelays() {
        let chord = 1_000.4
        XCTAssertTrue(WisprOwnership.madeByRelayChord(startedAt: 1_000, chords: [chord]))   // same second (truncated)
        XCTAssertTrue(WisprOwnership.madeByRelayChord(startedAt: 1_001, chords: [chord]))   // 0.6 s later
        XCTAssertFalse(WisprOwnership.madeByRelayChord(startedAt: 1_002, chords: [chord]))  // his, later
        XCTAssertFalse(WisprOwnership.madeByRelayChord(startedAt: 999, chords: [chord]))    // before the chord
        XCTAssertFalse(WisprOwnership.rowIsHis(rowid: 9, startedAt: 1_000, floor: 8, relayHadRow: true,
                                               relayClosedAt: 990, relayCmdVSeen: true, sinceRelease: 5,
                                               relayChords: [chord]))
        XCTAssertTrue(WisprOwnership.rowIsHis(rowid: 9, startedAt: 1_003, floor: 8, relayHadRow: true,
                                              relayClosedAt: 990, relayCmdVSeen: true, sinceRelease: 5,
                                              relayChords: [chord]))
    }

    // MARK: E: the ghost microphone

    func testAMicOpeningAfterAnUnansweredChordIsAGhost() {
        XCTAssertNotNil(WisprOwnership.ghostMic(now: 1_015, micOpen: true, relayRecording: false, unansweredAt: 1_000,
                                                hisKeysHeld: false, hisChordAt: 0))
    }
    func testNotAGhostWhenItIsHisOrTooLateOrTheRelays() {
        XCTAssertNil(WisprOwnership.ghostMic(now: 1_015, micOpen: true, relayRecording: false, unansweredAt: 1_000,
                                             hisKeysHeld: true, hisChordAt: 0))             // his ptt held
        XCTAssertNil(WisprOwnership.ghostMic(now: 1_015, micOpen: true, relayRecording: false, unansweredAt: 1_000,
                                             hisKeysHeld: false, hisChordAt: 1_010))        // his chord since
        XCTAssertNil(WisprOwnership.ghostMic(now: 1_030, micOpen: true, relayRecording: false, unansweredAt: 1_000,
                                             hisKeysHeld: false, hisChordAt: 0))            // past 25 s
        XCTAssertNil(WisprOwnership.ghostMic(now: 1_015, micOpen: true, relayRecording: true, unansweredAt: 1_000,
                                             hisKeysHeld: false, hisChordAt: 0))            // the relay's sentence
        XCTAssertNil(WisprOwnership.ghostMic(now: 1_015, micOpen: false, relayRecording: false, unansweredAt: 1_000,
                                             hisKeysHeld: false, hisChordAt: 0))
        XCTAssertNil(WisprOwnership.ghostMic(now: 1_015, micOpen: true, relayRecording: false, unansweredAt: 0,
                                             hisKeysHeld: false, hisChordAt: 0))
    }
}
