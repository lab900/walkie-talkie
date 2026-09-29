import XCTest
@testable import WalkieTalkie

/// The Engine list's rows (2026-09-28): Wispr Flow back behind
/// `WT_WISPR_ENGINE`, off by default until the VM lab's verdict.
final class EngineMenuTests: XCTestCase {

    func testSwitchAbsentIsTheListOfToday() {
        // Wispr Flow restored as an engine on 2026-09-29 (lab wave 5 YES): the row is on by default.
        XCTAssertTrue(StatusItem.wisprEngineDefault)
        XCTAssertEqual(StatusItem.engineRowIds(wisprSwitch: false, current: "eleven-live"),
                       ["eleven-live", "eleven", "whisper"])
    }

    func testSwitchOnPutsWisprLastWhereItWas() {
        XCTAssertEqual(StatusItem.engineRowIds(wisprSwitch: true, current: "eleven"),
                       ["eleven-live", "eleven", "whisper", "wispr"])
    }

    func testWisprPickedFromTheHarnessKeepsItsTickWithTheSwitchOff() {
        XCTAssertEqual(StatusItem.engineRowIds(wisprSwitch: false, current: "wispr").last, "wispr")
    }

    func testFxRowIsTheGlyphsAlone() {
        XCTAssertEqual(StatusItem.haloFx, "𝓯𝔁")
    }
}
