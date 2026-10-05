import XCTest
@testable import WalkieTalkie

/// `LiveAgreement` — which segments of a live-caption window are settled (2026-10-05).
final class LiveAgreementTests: XCTestCase {
    private func seg(_ t: String, _ a: Double, _ b: Double) -> LocalWhisper.Segment { .init(text: t, start: a, end: b) }

    func testFirstDecodeSettlesNothing() {
        var g = LiveAgreement()
        XCTAssertEqual(g.absorb([seg(" Salut.", 0, 1.5), seg(" Ce faci", 2, 3)], speechSeconds: 3.2), 0)
        XCTAssertEqual(g.committedText, "")
        XCTAssertEqual(g.pendingText, "Salut. Ce faci")
    }

    func testAgreedSegmentSettlesAndMovesTheWindow() {
        var g = LiveAgreement()
        _ = g.absorb([seg(" Salut.", 0, 1.5), seg(" Ce faci", 2, 3)], speechSeconds: 3.2)
        // the next decode agrees on the first, case and punctuation aside
        let shift = g.absorb([seg(" salut", 0, 1.5), seg(" Ce faci azi?", 2, 4.5)], speechSeconds: 4.6)
        XCTAssertEqual(shift, 1.5)
        XCTAssertEqual(g.committedText, "salut")
        XCTAssertEqual(g.pending, [seg(" Ce faci azi?", 0.5, 3.0)])
    }

    func testTheLastSegmentIsNeverSettled() {
        var g = LiveAgreement()
        _ = g.absorb([seg(" Salut.", 0, 1.5)], speechSeconds: 5)
        XCTAssertEqual(g.absorb([seg(" Salut.", 0, 1.5)], speechSeconds: 5), 0)
        XCTAssertEqual(g.committedText, "")
    }

    func testASegmentEndingNearTheVoiceIsNotSettled() {
        var g = LiveAgreement()
        _ = g.absorb([seg(" Unu.", 0, 2.5), seg(" Doi", 2.6, 3)], speechSeconds: 3.0)
        // agreed, but it ends 0.5 s before the voice stopped — under `settle`
        XCTAssertEqual(g.absorb([seg(" Unu.", 0, 2.5), seg(" Doi", 2.6, 3)], speechSeconds: 3.0), 0)
    }

    func testDisagreementStopsAtTheFirstChange() {
        var g = LiveAgreement()
        _ = g.absorb([seg(" A.", 0, 1), seg(" B.", 1, 2), seg(" C", 2, 6)], speechSeconds: 6)
        let shift = g.absorb([seg(" A.", 0, 1), seg(" Be.", 1, 2), seg(" C", 2, 6)], speechSeconds: 6)
        XCTAssertEqual(shift, 1)
        XCTAssertEqual(g.committedText, "A.")
        XCTAssertEqual(g.pendingText, "Be. C")
    }

    func testSegmentsInTheTrailingSilenceAreDropped() {
        var g = LiveAgreement()
        _ = g.absorb([seg(" Gata.", 0, 1.2), seg(" Mulțumesc pentru vizionare!", 1.6, 3)], speechSeconds: 1.4)
        XCTAssertEqual(g.pendingText, "Gata.")
    }

    func testAnOverflowKeepsOnlyWhatEndsBeforeTheKeptTail() {
        var g = LiveAgreement()
        _ = g.absorb([seg(" Unu", 0, 6), seg(" doi", 6, 12), seg(" trei", 12, 28)], speechSeconds: 28.5)
        XCTAssertEqual(g.commitBefore(8.5), 6)
        XCTAssertEqual(g.committedText, "Unu")
        XCTAssertEqual(g.pending, [seg(" doi", 0, 6), seg(" trei", 6, 22)])
    }

    func testAnOverflowWithOneLongSegmentKeepsItAndStartsAfresh() {
        var g = LiveAgreement()
        _ = g.absorb([seg(" Foarte lung", 0, 28)], speechSeconds: 28.5)
        XCTAssertNil(g.commitBefore(8.5))
        XCTAssertEqual(g.committedText, "Foarte lung")
        XCTAssertEqual(g.pendingText, "")
    }
}
