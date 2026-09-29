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
