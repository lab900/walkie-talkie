import Darwin
import XCTest
@testable import WalkieTalkie

/// Batch 5 (2026-09-29): Wispr's microphone closing under a relay sentence — a
/// quit, or Wispr ending the dictation itself? Lab wave 5, TW20 / TQ2 on a real
/// SIGKILL: the 100 ms poll saw the close first and the kernel's exit event came
/// 0.35–0.39 s after it; batch 4's 0.3 s grace had already ended the take.
final class WisprQuitOrderTests: XCTestCase {
    private var clock: CFAbsoluteTime = 100
    private lazy var m = WisprState(now: { self.clock })

    private func listening() {
        m.startChord("relay"); clock += 0.25
        m.sawRow(7, status: "")                       // the row came before the poll saw the mic
        clock += 0.2; m.poll(true)
        XCTAssertEqual(m.phase, .listening)
    }

    /// The real order: the poll's close, then the exit 100–400 ms later → a quit.
    func testThePollsCloseThenTheExitIsAQuit() {
        for gap in [0.1, 0.3, 0.39, 0.9] {
            listening()
            clock += 2.5
            let v = m.wisprSideClose(by: "the 100 ms poll", processGone: false)
            XCTAssertEqual(v, .pending(until: clock + WisprState.quitCloseGrace), "gap \(gap)")
            clock += gap
            m.wisprProcessExited()
            XCTAssertEqual(m.wisprCloseDue(processGone: false), .quit, "gap \(gap)")
            // …and still a quit when the deadline fires after it.
            clock += WisprState.quitCloseGrace
            XCTAssertEqual(m.wisprCloseDue(processGone: false), .quit, "gap \(gap)")
            // The machine was never told of the close: the phase is still listening.
            XCTAssertEqual(m.phase, .listening, "gap \(gap)")
        }
    }

    /// Wave 5 exactly: batch 4's 0.3 s would have said `wisprEnded` before the exit at 0.35 s.
    func testTheGraceOutlastsWaveFivesGap() {
        XCTAssertGreaterThan(WisprState.quitCloseGrace, 0.39 * 2)
        listening(); clock += 3
        _ = m.wisprSideClose(by: "the 100 ms poll", processGone: false)
        clock += 0.3
        XCTAssertEqual(m.wisprCloseDue(processGone: false), .pending(until: clock - 0.3 + WisprState.quitCloseGrace))
        clock += 0.05; m.wisprProcessExited()
        XCTAssertEqual(m.wisprCloseDue(processGone: false), .quit)
    }

    /// The exit first, the close after (the desk's `fakeExit` order) → a quit at once.
    func testTheExitThenTheCloseIsAQuitAtOnce() {
        listening(); clock += 3
        m.wisprProcessExited()
        clock += 0.05
        XCTAssertEqual(m.wisprSideClose(by: "the CoreAudio edge", processGone: false), .quit)
    }

    /// The kernel already says exiting (`P_WEXIT`) at the close → a quit at once.
    func testADyingProcessAtTheCloseIsAQuitAtOnce() {
        listening(); clock += 3
        XCTAssertEqual(m.wisprSideClose(by: "the 100 ms poll", processGone: true), .quit)
    }

    /// Wispr alive through the grace → it ended the dictation itself; not before.
    func testWisprAliveThroughTheGraceEndedIt() {
        listening(); clock += 3
        let at = clock
        _ = m.wisprSideClose(by: "the 100 ms poll", processGone: false)
        clock += WisprState.quitCloseGrace - 0.01
        XCTAssertEqual(m.wisprCloseDue(processGone: false), .pending(until: at + WisprState.quitCloseGrace))
        clock += 0.01
        XCTAssertEqual(m.wisprCloseDue(processGone: false), .wisprEnded)
    }

    /// Its row moved after the close (its stop path ran) → ended by Wispr, early.
    func testARowThatMovedEndsItEarly() {
        listening(); clock += 3
        _ = m.wisprSideClose(by: "the 100 ms poll", processGone: false)
        clock += 0.4; m.wisprAliveAfterClose()
        XCTAssertEqual(m.wisprCloseDue(processGone: false), .wisprEnded)
    }

    /// A second close path during the grace keeps the first one's clock.
    func testASecondWitnessSharesTheGrace() {
        listening(); clock += 3
        let at = clock
        _ = m.wisprSideClose(by: "the 100 ms poll", processGone: false)
        clock += 0.5
        XCTAssertEqual(m.wisprSideClose(by: "the CoreAudio edge", processGone: false),
                       .pending(until: at + WisprState.quitCloseGrace))
        XCTAssertEqual(m.wisprCloseBy, "the 100 ms poll")
    }

    /// The next chord forgets the last sentence's close and exit.
    func testTheNextChordStartsClean() {
        listening(); clock += 3
        m.wisprProcessExited()
        m.startChord("next")
        XCTAssertNil(m.wisprExitAt)
        XCTAssertNil(m.wisprCloseAt)
        clock += 1
        XCTAssertEqual(m.wisprSideClose(by: "the 100 ms poll", processGone: false),
                       .pending(until: clock + WisprState.quitCloseGrace))
    }

    /// 12:20 on 2026-09-29: Wispr's input went off and came back — a blip. The
    /// next close of the same sentence gets its own grace, not the stale one.
    func testAnInputThatComesBackForgetsTheClose() {
        listening(); clock += 1
        _ = m.wisprSideClose(by: "the 100 ms poll", processGone: false)
        clock += 2
        m.wisprInputReopened()
        XCTAssertNil(m.wisprCloseAt)
        clock += 5
        XCTAssertEqual(m.wisprSideClose(by: "the 100 ms poll", processGone: false),
                       .pending(until: clock + WisprState.quitCloseGrace))
    }

    /// …but an exit already seen is still a quit.
    func testAReopenDoesNotForgetAnExit() {
        listening(); clock += 1
        _ = m.wisprSideClose(by: "the 100 ms poll", processGone: false)
        m.wisprProcessExited()
        m.wisprInputReopened()
        XCTAssertEqual(m.wisprCloseDue(processGone: false), .quit)
    }
}

/// `ProcessClock.isDyingOrGone` — `P_WEXIT`, set the moment a SIGKILL is acted on.
final class ProcessDyingTests: XCTestCase {
    func testThisProcessIsNotDying() {
        XCTAssertFalse(ProcessClock.isDyingOrGone(getpid()))
    }

    func testNoSuchProcessIsGone() {
        XCTAssertTrue(ProcessClock.isDyingOrGone(99_999_999))
    }

    func testAKilledChildIsDyingBeforeItIsReaped() {
        var pid: pid_t = 0
        let argv: [UnsafeMutablePointer<CChar>?] = [strdup("/bin/sleep"), strdup("30"), nil]
        defer { argv.forEach { free($0) } }
        XCTAssertEqual(posix_spawn(&pid, "/bin/sleep", nil, nil, argv, environ), 0)
        XCTAssertFalse(ProcessClock.isDyingOrGone(pid))
        kill(pid, SIGKILL)
        usleep(100_000)
        XCTAssertTrue(ProcessClock.isDyingOrGone(pid))
        var status: Int32 = 0
        waitpid(pid, &status, 0)
        XCTAssertTrue(ProcessClock.isDyingOrGone(pid))
    }
}
