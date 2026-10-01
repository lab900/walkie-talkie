import Foundation
import SQLite3
import XCTest
@testable import WalkieTalkie

/// Batch 3 (2026-09-28, `evals/plan/wispr/integration-surfaces.md`): Wispr's row
/// lifecycle from its own code — which statuses are final, when a row is dead —
/// and the WAL watch that wakes the readers.
final class WisprRowLifeTests: XCTestCase {

    // MARK: 1. The vocabulary

    func testRawTranscriptAndItsSiblingsAreFinal() {
        for s in ["raw_transcript", "fallback", "verification_failed", "timeout"] {
            XCTAssertTrue(WisprState.isTerminal(s), s)
            XCTAssertTrue(WisprState.terminalStatuses.contains(s), s)
        }
        for s in ["", "recording", "processing"] { XCTAssertFalse(WisprState.isTerminal(s), s) }
    }

    func testPasteableIsWisprsOwnSet() {
        for s in ["formatted", "raw_transcript", "verification_failed", "extension_paste", "fallback"] {
            XCTAssertTrue(WisprState.pasteableStatuses.contains(s), s)
        }
        for s in ["timeout", "error", "empty", "no_audio", "dismissed"] {
            XCTAssertFalse(WisprState.pasteableStatuses.contains(s), s)
        }
    }

    func testTheMachineIsDoneAtRawTranscript() {
        var clock: CFAbsoluteTime = 0
        let m = WisprState(now: { clock })
        m.startChord("t"); clock = 1; m.stopChord("t")
        clock = 1.2; m.sawRow(7, status: "processing")
        clock = 1.5; m.sawRow(7, status: "raw_transcript")
        XCTAssertEqual(m.phase.name, "done")
    }

    // MARK: 2. The dead-row verdict

    let t0: Double = 1_000_000
    func facts(_ status: String, duration: Double? = nil, newest: Int64 = 10, pidNow: Int32 = 5,
               pidAt: Int32 = 5, dismissed: Double = 0, closed: Double? = nil, mic: Bool = false,
               at: Double) -> WisprState.RowFacts {
        .init(rowid: 10, status: status, duration: duration, newestRowid: newest, pidNow: pidNow,
              pidAtAdoption: pidAt, dismissedAt: dismissed, closedAt: closed ?? t0, wisprMicOpen: mic, now: at)
    }

    func testAProcessingRowIsAliveWhileNothingSaysOtherwise() {
        XCTAssertNil(WisprState.deadRow(facts("processing", duration: 4, at: t0 + 35)))
    }
    func testSupersededByANewerRowIsDeadAtOnce() {
        XCTAssertNotNil(WisprState.deadRow(facts("processing", duration: 4, newest: 11, at: t0 + 0.2)))
        XCTAssertNotNil(WisprState.deadRow(facts("", newest: 11, at: t0 + 0.2)))
    }
    func testANewerRowWhileTheRelayStillRecordsDecidesNothing() {
        XCTAssertNil(WisprState.deadRow(facts("", newest: 11, closed: 0, at: t0 + 0.2)))
    }
    func testANewerRowAboveAFinishedRowIsNotADeath() {
        XCTAssertNil(WisprState.deadRow(facts("formatted", newest: 11, at: t0 + 0.2)))
        XCTAssertNil(WisprState.deadRow(facts("raw_transcript", newest: 11, at: t0 + 0.2)))
    }
    func testAnotherWisprPidIsDead() {
        XCTAssertNotNil(WisprState.deadRow(facts("processing", pidNow: 6, pidAt: 5, at: t0 + 0.2)))
        // An unread pid (0) is not a different one.
        XCTAssertNil(WisprState.deadRow(facts("processing", pidNow: 0, pidAt: 5, at: t0 + 0.2)))
    }
    func testStillProcessingOneSecondAfterTheRelaysDismissIsDead() {
        XCTAssertNil(WisprState.deadRow(facts("processing", duration: 2, dismissed: t0 + 1, at: t0 + 1.9)))
        XCTAssertNotNil(WisprState.deadRow(facts("processing", duration: 2, dismissed: t0 + 1, at: t0 + 2.0)))
        // A dismiss under 0.5 s of audio writes nothing: NULL stays NULL.
        XCTAssertNotNil(WisprState.deadRow(facts("", dismissed: t0 + 1, at: t0 + 2.0)))
    }
    func testNullWithNoDurationThreeSecondsAfterTheCloseIsDead() {
        XCTAssertNil(WisprState.deadRow(facts("", at: t0 + 3.0)))
        XCTAssertNotNil(WisprState.deadRow(facts("", at: t0 + 3.1)))
        // …unless Wispr's microphone is still open: its stop has not happened yet.
        XCTAssertNil(WisprState.deadRow(facts("", mic: true, at: t0 + 3.1)))
        // A duration written means the stop path ran.
        XCTAssertNil(WisprState.deadRow(facts("", duration: 2, at: t0 + 3.1)))
    }

    // MARK: 3. The WAL watch

    /// A commit to a WAL-mode file wakes the watch well inside 50 ms, and the
    /// `data_version` gate answers the second read of the same question from
    /// the cache.
    func testACommitWakesTheWatchWithin50ms() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("wt-wal-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        let path = dir.appendingPathComponent("flow.sqlite").path
        var w: OpaquePointer?
        XCTAssertEqual(sqlite3_open(path, &w), SQLITE_OK)
        defer { sqlite3_close(w) }
        func exec(_ sql: String) { XCTAssertEqual(sqlite3_exec(w, sql, nil, nil, nil), SQLITE_OK, sql) }
        exec("pragma journal_mode=wal")
        exec("create table History (transcriptEntityId text, status text, pastedText text, formattedText text, e2eLatency float, app text, micDevice text, language text, timestamp datetime, asrText text, duration float)")
        exec("insert into History (status) values (null)")

        setenv("WT_WISPR_DB", path, 1)
        defer { unsetenv("WT_WISPR_DB") }
        XCTAssertEqual(WisprFlowDB.url.path, path)
        XCTAssertEqual(WisprHistory.newest()?.rowid, 1)
        let q0 = WisprHistory.queries
        _ = WisprHistory.newest()
        XCTAssertEqual(WisprHistory.queries, q0, "nothing committed: the gate answers from the cache")

        let watch = WisprHistoryWatch()
        var seenAt: CFAbsoluteTime = 0
        var seenStatus = ""
        watch.subscribe("t") {
            guard seenAt == 0, let e = WisprHistory.newest(), e.status == "processing" else { return }
            seenAt = CFAbsoluteTimeGetCurrent(); seenStatus = e.status
        }
        defer { watch.unsubscribe("t") }
        XCTAssertTrue(watch.watchedPaths.contains(path + "-wal"), "\(watch.watchedPaths)")
        RunLoop.main.run(until: Date().addingTimeInterval(0.1))
        let wrote = CFAbsoluteTimeGetCurrent()
        exec("update History set status = 'processing', duration = 2 where rowid = 1")
        let deadline = Date().addingTimeInterval(2)
        while seenAt == 0, Date() < deadline { RunLoop.main.run(until: Date().addingTimeInterval(0.005)) }
        XCTAssertEqual(seenStatus, "processing")
        let ms = (seenAt - wrote) * 1000
        print("wal watch: row seen \(String(format: "%.1f", ms)) ms after the commit")
        XCTAssertLessThan(ms, 50)
        XCTAssertGreaterThan(watch.events, 0, "woken by the file, not the 1 s tick")
        XCTAssertEqual(WisprHistory.newest()?.duration, 2)
    }

    /// 2026-10-01, row 18156: a clean stop chord Wispr never took — NULL, no
    /// duration, its microphone open — is the one state the relay acts on; a
    /// stop that took (`processing`, a duration, or the microphone shut) is not.
    func testStopWasLostOnlyWhileWisprStillListens() {
        XCTAssertTrue(WisprState.stopWasLost(status: "", duration: nil, wisprMicOpen: true))
        XCTAssertFalse(WisprState.stopWasLost(status: "processing", duration: nil, wisprMicOpen: true))
        XCTAssertFalse(WisprState.stopWasLost(status: "", duration: 22.1, wisprMicOpen: true))
        XCTAssertFalse(WisprState.stopWasLost(status: "", duration: nil, wisprMicOpen: false))
        XCTAssertFalse(WisprState.stopWasLost(status: "formatted", duration: 22.1, wisprMicOpen: false))
        XCTAssertGreaterThan(WisprState.stopTakesWithin, 0.453 * 2)        // the slowest taken stop, twice over
    }
}
