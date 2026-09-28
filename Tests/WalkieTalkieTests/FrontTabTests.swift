import XCTest
@testable import WalkieTalkie

/// The bind gesture's *tab in front* (2026-09-28): Terminal's windows walked
/// front to back, the ones that cannot answer skipped, and every `osascript`
/// failure kept with its reason — including a Terminal that never answers.
final class FrontTabTests: XCTestCase {

    private typealias TB = TerminalBinding

    /// Four windows as the script reports them: one threw, one is in the Dock,
    /// one tab has no tty (its process completed), one title holds a tab.
    private let sample = [
        "windows\t5",
        "skip\t1\tthrew -1728",
        "skip\t2\tis miniaturized",
        "tab\t3\t\tfalse\t0 25 800 600\twt-witness\t",
        "tab\t4\t/dev/ttys023\tfalse\t-1920 25 0 1070\t✳ workspace — plan\t✳ plan\tpart two",
        "tab\t5\t/dev/ttys004\ttrue\t1730 552 2690 1068\t~/workspace\t",
        "",
    ].joined(separator: "\n")

    func testTheScanKeepsEveryWindowWithATtyAndSaysWhyTheOthersWereSkipped() {
        let scan = TB.parseFrontTabScan(sample)
        XCTAssertEqual(scan.windows, 5)
        XCTAssertEqual(scan.candidates.map(\.tty), ["/dev/ttys023", "/dev/ttys004"])
        XCTAssertEqual(scan.skipped, ["window 1 threw -1728", "window 2 is miniaturized", "window 3 has no tty"])

        let first = scan.candidates[0]
        XCTAssertEqual(first.index, 4)
        XCTAssertFalse(first.frontmost)
        XCTAssertEqual(first.bounds, [-1920, 25, 0, 1070])
        XCTAssertEqual(first.name, "✳ workspace — plan")
        XCTAssertEqual(first.title, "✳ plan\tpart two", "a tab inside the custom title is kept, not split on")

        let second = scan.candidates[1]
        XCTAssertTrue(second.frontmost)
        XCTAssertNil(second.title, "an empty custom title is no title")
    }

    func testNoWindowsIsAnEmptyScan() {
        let scan = TB.parseFrontTabScan("windows\t0\n")
        XCTAssertEqual(scan.windows, 0)
        XCTAssertTrue(scan.candidates.isEmpty)
        XCTAssertNil(TB.pickFrontTab(scan) { _ in true })
    }

    func testJunkLinesAreIgnored() {
        let scan = TB.parseFrontTabScan("garbage\ntab\t1\nwindows\tx\ntab\t2\t/dev/ttys9\ttrue")
        XCTAssertEqual(scan.windows, 0)
        XCTAssertEqual(scan.candidates.map(\.tty), ["/dev/ttys9"])
        XCTAssertNil(scan.candidates[0].bounds)
    }

    func testKeyboardFocusWinsThenFrontmostThenOrder() {
        let scan = TB.parseFrontTabScan(sample)
        // Focus names window 4 (by frame), though Terminal calls window 5 frontmost.
        let byFocus = TB.pickFrontTab(scan) { $0.bounds == [-1920, 25, 0, 1070] }
        XCTAssertEqual(byFocus?.0.tty, "/dev/ttys023")
        XCTAssertEqual(byFocus?.1, "keyboard focus")

        // Focus unknown (or ambiguous) → `frontmost`.
        XCTAssertEqual(TB.pickFrontTab(scan) { _ in false }?.0.tty, "/dev/ttys004")
        XCTAssertEqual(TB.pickFrontTab(scan) { _ in true }?.1, "frontmost")

        // Nobody frontmost → the first that answered, front to back.
        let noFront = TB.parseFrontTabScan(sample.replacingOccurrences(of: "\ttrue\t", with: "\tfalse\t"))
        let byOrder = TB.pickFrontTab(noFront) { _ in false }
        XCTAssertEqual(byOrder?.0.tty, "/dev/ttys023")
        XCTAssertEqual(byOrder?.1, "front-to-back order")
    }

    func testAFailureKeepsItsStatusAndStderr() {
        let outcome = TB.runOutcome("/bin/sh", ["-c", "echo out; echo boom >&2; exit 3"])
        XCTAssertEqual(outcome, .failed(status: 3, stderr: "boom"))
        XCTAssertNil(outcome.output)
        XCTAssertEqual(TB.runOutcome("/bin/sh", ["-c", "echo ' hi '"]), .ok("hi"))
    }

    func testAnAppleScriptErrorReachesTheCallerWithItsNumber() {
        let outcome = TB.osascriptOutcome("error \"boom\" number 42")
        guard case .failed(let status, let stderr) = outcome else { return XCTFail("\(outcome)") }
        XCTAssertNotEqual(status, 0)
        XCTAssertTrue(stderr.contains("boom") && stderr.contains("(42)"), stderr)
    }

    func testAScriptThatNeverAnswersIsKilledAtTheTimeout() {
        let started = Date()
        let outcome = TB.osascriptOutcome("do shell script \"sleep 10\"", timeout: 1)
        let took = Date().timeIntervalSince(started)
        XCTAssertEqual(outcome, .timedOut(1))
        XCTAssertLessThan(took, 4, "killed near the timeout, not after the sleep")
        XCTAssertTrue(outcome.reason.contains("timed out"))
    }

    func testThisProcessHasAStartTimeInThePast() {
        let started = TB.processStartDate()
        XCTAssertNotNil(started)
        XCTAssertLessThanOrEqual(started!, Date())
        XCTAssertGreaterThan(started!, Date().addingTimeInterval(-86_400))
    }
}
