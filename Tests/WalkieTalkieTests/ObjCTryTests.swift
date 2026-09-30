import AVFoundation
import ObjCTry
import XCTest

/// The two `SIGABRT`s of `evals/wispr-catchup/` (2026-09-30): `-[AVAudioPlayerNode
/// play]` raises an `NSException` on an engine that is not running, and Swift
/// cannot catch one. `AudioBridge` routes every engine call through `WTTry`.
final class ObjCTryTests: XCTestCase {

    func testANormalBlockAnswersNil() {
        var ran = false
        XCTAssertNil(WTTry { ran = true })
        XCTAssertTrue(ran)
    }

    func testARaisedExceptionComesBackAsAnError() {
        let error = WTTry {
            NSException(name: .invalidArgumentException, reason: "boom", userInfo: nil).raise()
        } as NSError?
        XCTAssertEqual(error?.domain, "NSException")
        XCTAssertEqual(error?.localizedDescription, "boom")
        XCTAssertEqual(error?.localizedFailureReason, NSExceptionName.invalidArgumentException.rawValue)
    }

    /// The crash's own call, `-[AVAudioPlayerNode play]`, made to raise the one way
    /// that is deterministic on this Mac: a player no engine owns. The guest's
    /// two crashes kept no exception text (`abort() called` only), and a started-
    /// then-stopped engine does not raise here — so this pins the guard, not the
    /// exact condition of 17:09 / 17:44.
    func testPlayRaisingIsCaughtNotFatal() {
        let player = AVAudioPlayerNode()
        let error = WTTry { player.play() }
        XCTAssertNotNil(error, "play() on an unattached player no longer raises — the guard is untested")
    }
}
