import Darwin
import XCTest
@testable import WalkieTalkie

/// `ProcessClock` — whether Wispr's process is still there when its microphone
/// closes under a relay sentence (batch 4, item 3).
final class ProcessClockTests: XCTestCase {
    func testThisProcessIsAlive() {
        XCTAssertTrue(ProcessClock.isAlive(getpid()))
    }

    func testNoSuchProcessIsNotAlive() {
        XCTAssertFalse(ProcessClock.isAlive(0))
        XCTAssertFalse(ProcessClock.isAlive(99_999_999))
    }

    /// A killed child not yet reaped is a zombie — still in the table, not alive.
    func testAZombieIsNotAlive() throws {
        var pid: pid_t = 0
        let argv: [UnsafeMutablePointer<CChar>?] = [strdup("/bin/sleep"), strdup("30"), nil]
        defer { argv.forEach { free($0) } }
        XCTAssertEqual(posix_spawn(&pid, "/bin/sleep", nil, nil, argv, environ), 0)
        XCTAssertTrue(ProcessClock.isAlive(pid))
        kill(pid, SIGKILL)
        usleep(200_000)                       // dead, not reaped: SZOMB
        XCTAssertFalse(ProcessClock.isAlive(pid))
        var status: Int32 = 0
        waitpid(pid, &status, 0)
        XCTAssertFalse(ProcessClock.isAlive(pid))
    }
}

/// `ProcessExitWatch` — the kernel's exit event for another process (batch 4,
/// item 5: TW20's quit was noticed 1.48 s late, the check riding the row reader).
final class ProcessExitWatchTests: XCTestCase {
    func testTheExitIsToldAtOnce() throws {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/sleep")
        p.arguments = ["30"]
        try p.run()
        let pid = p.processIdentifier
        let told = expectation(description: "exit told")
        var at = Date.distantPast
        let q = DispatchQueue(label: "exit-watch-test")
        let watch = ProcessExitWatch(pid: pid, queue: q) { got in
            XCTAssertEqual(got, pid)
            at = Date()
            told.fulfill()
        }
        usleep(100_000)
        let killed = Date()
        kill(pid, SIGKILL)
        wait(for: [told], timeout: 2)
        XCTAssertLessThan(at.timeIntervalSince(killed), 0.2)
        withExtendedLifetime(watch) {}
    }

    func testACancelledWatchSaysNothing() throws {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/sleep")
        p.arguments = ["30"]
        try p.run()
        let quiet = expectation(description: "not told")
        quiet.isInverted = true
        let watch = ProcessExitWatch(pid: p.processIdentifier, queue: DispatchQueue(label: "exit-watch-test-2")) { _ in
            quiet.fulfill()
        }
        watch.cancel()
        p.terminate()
        wait(for: [quiet], timeout: 0.5)
    }
}
