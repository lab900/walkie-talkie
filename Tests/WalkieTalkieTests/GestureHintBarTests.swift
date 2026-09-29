import XCTest
@testable import WalkieTalkie

/// The corner hint bar's wording per stage (2026-09-29): what each gesture does
/// *now*, and nothing at all when no sentence is open.
final class GestureHintBarTests: XCTestCase {

    func testNothingWhenNotDictating() {
        XCTAssertEqual(GestureHintBar.hints(for: .init()), [])
    }

    func testAPromptOffersTheShutterTheFilmAndANewSession() {
        let h = GestureHintBar.hints(for: .init(listening: true, prompting: true))
        XCTAssertEqual(h.first, "🔼 end dictation")
        XCTAssertTrue(h.contains("🔽 screenshot"))
        XCTAssertTrue(h.contains("🔽↑ start video"))
        XCTAssertTrue(h.contains("🔼↑ new session"))
    }

    func testTheFilmAndKamikazeHintsFollowTheirState() {
        let h = GestureHintBar.hints(for: .init(listening: true, prompting: true, filming: true,
                                                kamikaze: true, spawn: true))
        XCTAssertTrue(h.contains("🔽↑ stop video"))
        XCTAssertTrue(h.contains("🔼↓ no kamikaze"))
        XCTAssertFalse(h.contains("🔼↑ new session"))
    }

    func testAPlainDictationOnlyStopsOrCancels() {
        XCTAssertEqual(GestureHintBar.hints(for: .init(listening: true, prompting: false)),
                       ["🔽→ stop", "🔽 stop + ⏎", "🔼← cancel", "⌘⌃X local model"])
    }
}
