import XCTest
@testable import WalkieTalkie

/// `AutoLocal.wisprNotUp` — a Wispr sentence never waits for Wispr Flow to
/// start, whoever launched it (batch 4, item 4: TX9 relaunched Wispr from
/// outside, dictated 1 s later and paid Q14's 4.3–6.3 s three times).
final class AutoLocalWisprStartTests: XCTestCase {
    func testNotRunningIsNotUp() {
        XCTAssertEqual(AutoLocal.wisprNotUp(running: false, processAge: nil, launchedByRelayAgo: nil), "is not running")
    }

    func testLaunchedByTheRelayIsStillStarting() {
        XCTAssertEqual(AutoLocal.wisprNotUp(running: true, processAge: 30, launchedByRelayAgo: 3),
                       "is still starting (launched 3.0 s ago)")
    }

    /// TX9: the relay never launched it; its process is 1 s old.
    func testAYoungProcessIsStillStartingWhoeverLaunchedIt() {
        XCTAssertEqual(AutoLocal.wisprNotUp(running: true, processAge: 1.0, launchedByRelayAgo: nil),
                       "is still starting (its process is 1.0 s old)")
        XCTAssertNotNil(AutoLocal.wisprNotUp(running: true, processAge: 11.9, launchedByRelayAgo: nil))
    }

    func testAnOldProcessIsUp() {
        XCTAssertNil(AutoLocal.wisprNotUp(running: true, processAge: 12.0, launchedByRelayAgo: nil))
        XCTAssertNil(AutoLocal.wisprNotUp(running: true, processAge: 3_600, launchedByRelayAgo: 40))
        XCTAssertNil(AutoLocal.wisprNotUp(running: true, processAge: nil, launchedByRelayAgo: nil))
    }

    func testTheProcessClockReadsAYoungChild() throws {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/sleep")
        p.arguments = ["5"]
        try p.run()
        defer { p.terminate() }
        let age = try XCTUnwrap(ProcessClock.age(p.processIdentifier))
        XCTAssertGreaterThanOrEqual(age, -0.05)
        XCTAssertLessThan(age, 2.0)
        XCTAssertNotNil(AutoLocal.wisprNotUp(running: true, processAge: age, launchedByRelayAgo: nil))
        // This test process has been up longer than its child.
        XCTAssertGreaterThan(try XCTUnwrap(ProcessClock.age(getpid())), age)
    }
}
