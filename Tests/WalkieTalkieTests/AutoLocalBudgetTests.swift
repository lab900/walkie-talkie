import XCTest
@testable import WalkieTalkie

/// The auto fallback's budget (2026-09-28): the engine's p98 for this length,
/// clamped to [1.5 s, 0.3 × audio + 1 s] — `DecodeRate.budget`.
final class AutoLocalBudgetTests: XCTestCase {

    private func sample(_ audio: Double, _ decode: Double, engine: String = DecodeRate.elevenLabs) -> DecodeRate.Sample {
        DecodeRate.Sample(at: "", audio: audio, decode: decode, load: 0, cold: false, engine: engine)
    }

    private let eleven = DecodeRate.prior(for: DecodeRate.elevenLabs)

    func testUnderTwentySamplesThePriorTimesThreeStandsIn() {
        let window = (0..<19).map { sample(Double(5 + $0), 0.2) }   // fast, but too few to trust
        let b = DecodeRate.budget(window: window, prior: eleven, audio: 15, engine: DecodeRate.elevenLabs)
        XCTAssertEqual(b.samples, 19)
        XCTAssertTrue(b.fromPrior)
        XCTAssertEqual(b.p98, (0.9 + 0.08 * 15) * 3, accuracy: 1e-9)   // 6.3
        XCTAssertEqual(b.cap, 5.5, accuracy: 1e-9)
        XCTAssertEqual(b.seconds, 5.5, accuracy: 1e-9)                  // capped
    }

    func testTheCapIsThirtyPercentOfTheAudioPlusOneSecond() {
        for (audio, cap) in [(5.0, 2.5), (15.0, 5.5), (30.0, 10.0)] {
            let b = DecodeRate.budget(window: [], prior: DecodeRate.Prior(intercept: 50, slope: 1),
                                      audio: audio, engine: "x")
            XCTAssertEqual(b.cap, cap, accuracy: 1e-9)
            XCTAssertEqual(b.seconds, cap, accuracy: 1e-9)
        }
    }

    func testTheFloorIsOneAndAHalfSecondsEvenUnderTheCap() {
        // A fast engine and a 1 s clip: p98 and cap (1.3 s) both under the floor.
        let window = (0..<40).map { sample(Double($0 % 20) + 1, 0.1) }
        let b = DecodeRate.budget(window: window, prior: eleven, audio: 1, engine: DecodeRate.elevenLabs)
        XCTAssertLessThan(b.p98, 1.5)
        XCTAssertEqual(b.seconds, DecodeRate.budgetFloor, accuracy: 1e-9)
    }

    func testP98IsTheLineTimesTheResidualTail() {
        // decode = 1 + 0.05 × audio exactly, except 2 of 100 at twice that.
        var window: [DecodeRate.Sample] = []
        for i in 0..<100 {
            let a = Double(2 + i % 30)
            let d = (1 + 0.05 * a) * (i == 17 || i == 71 ? 2 : 1)
            window.append(sample(a, d))
        }
        let b = DecodeRate.budget(window: window, prior: eleven, audio: 20, engine: DecodeRate.elevenLabs)
        XCTAssertFalse(b.fromPrior)
        // The 0.98 quantile of 100 ratios (98 ones, 2 twos) interpolates at k = 97.02: 1.0 + 0.02.
        XCTAssertEqual(b.p98, (1 + 0.05 * 20) * 1.02, accuracy: 1e-6)
        XCTAssertEqual(b.seconds, b.p98, accuracy: 1e-9)   // 2.04 s: inside [1.5, 7.0]
    }

    func testTheTailNeverDiscountsTheLine() {
        let window = (0..<30).map { sample(Double(3 + $0), 1 + 0.05 * Double(3 + $0)) }
        let b = DecodeRate.budget(window: window, prior: eleven, audio: 10, engine: DecodeRate.elevenLabs)
        XCTAssertGreaterThanOrEqual(b.p98, 1.5 - 1e-9)   // tail ≥ 1: at least the line (1.5 s)
    }

    func testTheWindowIsTheEnginesNewestWarmSamples() {
        var all: [DecodeRate.Sample] = []
        for i in 0..<150 { all.append(sample(Double(i), 1, engine: DecodeRate.elevenLabs)) }
        all.append(sample(9, 1, engine: DecodeRate.wisprFlow))
        all.append(DecodeRate.Sample(at: "", audio: 9, decode: 9, load: 0, cold: true, engine: DecodeRate.elevenLabs))
        let w = DecodeRate.budgetWindow(of: all, engine: DecodeRate.elevenLabs)
        XCTAssertEqual(w.count, DecodeRate.budgetWindow)
        XCTAssertEqual(w.first?.audio, 50)
        XCTAssertTrue(w.allSatisfy { !$0.cold && $0.engineKey == DecodeRate.elevenLabs })
    }

    func testTheChipRowCountsDownInTenths() {
        XCTAssertEqual(AutoLocal.rowText(countdown: 2.13, loading: false, keys: "⌘⌃X"), "Local in 2.2 s  ⌘⌃X")
        XCTAssertEqual(AutoLocal.rowText(countdown: -0.4, loading: true, keys: "⌘⌃X"), "Local in 0.0 s (loading)  ⌘⌃X")
        XCTAssertEqual(AutoLocal.rowText(countdown: nil, loading: false, keys: "⌘⌃X"), "Local now  ⌘⌃X")
        XCTAssertEqual(AutoLocal.overBudgetFlash(engine: "Wispr Flow", budget: 2.04), "💻 Local — Wispr Flow over budget (2.0 s)")
    }
}
