import XCTest
@testable import WalkieTalkie

/// `RestartGate` — the Wispr half of `busyWhy` and the inactivity clock
/// (2026-09-28, the 18:39 restart over his dictation).
final class RestartGateTests: XCTestCase {
    let now: TimeInterval = 1_800_000_000

    func testNothingFromWisprIsNoReason() {
        XCTAssertEqual(RestartGate.wisprReasons(.init(), now: now), [])
    }

    func testWisprMicrophoneOpenBlocks() {
        let why = RestartGate.wisprReasons(.init(micOpen: true), now: now)
        XCTAssertEqual(why, ["Wispr Flow's microphone open"])
    }

    func testAFreshRowStillBeingWorkedOnBlocks() {
        for status in ["", "processing", "raw_transcript"] {
            let w = RestartGate.WisprReading(rowId: 17893, rowStatus: status, rowStartedAt: now - 20)
            let why = RestartGate.wisprReasons(w, now: now)
            XCTAssertEqual(why.count, 1, status)
            XCTAssertTrue(why[0].hasPrefix("Wispr Flow transcribing (row 17893"), why[0])
        }
    }

    func testAFinishedRowIsNoReason() {
        let w = RestartGate.WisprReading(rowId: 1, rowStatus: "formatted", rowStartedAt: now - 3)
        XCTAssertEqual(RestartGate.wisprReasons(w, now: now), [])
    }

    /// Row 12814 stayed `raw_transcript` for ever; 17892 is NULL since 07:33.
    func testAStaleUnfinishedRowAgesOut() {
        let w = RestartGate.WisprReading(rowId: 17892, rowStatus: "", rowStartedAt: now - 61)
        XCTAssertEqual(RestartGate.wisprReasons(w, now: now), [])
    }

    func testInactivityIsFiveSecondsAfterTheLatestClock() {
        let t = Date(timeIntervalSince1970: now)
        XCTAssertEqual(RestartGate.inactivity, 5)
        XCTAssertEqual(RestartGate.inactivityLeft(now: t, lastInput: nil, lastInsert: nil, lastDictationEdge: nil), 0)
        XCTAssertEqual(RestartGate.inactivityLeft(now: t, lastInput: t.addingTimeInterval(-3),
                                                  lastInsert: t.addingTimeInterval(-60), lastDictationEdge: nil), 2, accuracy: 0.001)
        XCTAssertEqual(RestartGate.inactivityLeft(now: t, lastInput: t.addingTimeInterval(-6),
                                                  lastInsert: t.addingTimeInterval(-12), lastDictationEdge: t.addingTimeInterval(-30)), 0)
        XCTAssertEqual(RestartGate.inactivityLeft(now: t, lastInput: nil, lastInsert: nil,
                                                  lastDictationEdge: t.addingTimeInterval(-1)), 4, accuracy: 0.001)
    }
}
