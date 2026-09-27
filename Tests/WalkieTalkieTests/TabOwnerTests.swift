import XCTest
@testable import WalkieTalkie

/// The bound tab's identity (TD21, batch 7, 2026-09-27): a tty number is reused,
/// the tab's `login` by pid + start time is not.
final class TabOwnerTests: XCTestCase {

    func testTheTokenRoundTrips() {
        let owner = TerminalBinding.TTYOwner(pid: 11581, started: 1_758_842_783)
        XCTAssertEqual(owner.token, "owner=11581@1758842783")
        XCTAssertEqual(TerminalBinding.TTYOwner(token: owner.token), owner)
        XCTAssertEqual(TerminalBinding.TTYOwner(token: "11581@1758842783\n"), owner)
    }

    func testAnythingElseIsNoOwner() {
        for junk in ["", "owner=", "owner=abc@1", "owner=12", "%1", "listening", "owner=0@5", "owner=5@0"] {
            XCTAssertNil(TerminalBinding.TTYOwner(token: junk), junk)
        }
    }

    func testTheOwnerOfThisProcessTTYIsAnswerableOrNil() {
        // No tty in CI / `swift test` under a GUI parent: nil is a legal answer;
        // a tty that does not exist must be nil, never a guess.
        XCTAssertNil(TerminalBinding.tabOwner(onTTY: "ttys999"))
    }
}
