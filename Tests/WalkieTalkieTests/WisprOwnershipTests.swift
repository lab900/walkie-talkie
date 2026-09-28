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
}
