import XCTest
@testable import WalkieTalkie

/// 🧾 The Engine list's quota row (2026-09-28): `remaining / total in k / reset "Mon d"`.
final class ElevenLabsQuotaTests: XCTestCase {
    private typealias P = ElevenLabsQuotaPolicy
    private let utc = TimeZone(identifier: "UTC")!

    private func snap(used: Int, total: Int = 10_000, reset: Date? = nil,
                      missingUserRead: Bool = false) -> P.Snapshot {
        P.Snapshot(used: used, total: total, reset: reset, usedSource: "", totalSource: "",
                   subscriptionStatus: missingUserRead ? 401 : 200, missingUserRead: missingUserRead)
    }

    func testOverdrawnWithoutUserReadIsTodaysRow() {
        let s = snap(used: 10_033, missingUserRead: true)
        XCTAssertEqual(P.title(s, error: nil, timeZone: utc), "🧾 ElevenLabs 10 033 / 10k / ?")
        XCTAssertTrue(s.exhausted)
        XCTAssertEqual(P.pace(s), .red)
        XCTAssertTrue(P.tooltip(s, error: nil, fetchedAt: nil).contains("user_read"))
    }

    func testUsedAndResetDate() {
        let s = snap(used: 8_766, reset: Date(timeIntervalSince1970: 1_790_812_800)) // 2026-10-01 UTC
        XCTAssertEqual(P.title(s, error: nil, timeZone: utc), "🧾 ElevenLabs 8 766 / 10k / Oct 1")
        XCTAssertFalse(s.exhausted)
    }

    // The colour is a trend against the days gone by, not a level (2026-09-28).
    private let reset = Date(timeIntervalSince1970: 1_790_812_800)            // 2026-10-01 UTC
    private func daysBefore(_ d: Double) -> Date { reset.addingTimeInterval(-d * 86_400) }

    func testOnTrendIsGreen() {
        // Half the period gone, half the plan used: exactly on trend.
        let s = snap(used: 5_000, reset: reset)
        XCTAssertEqual(P.burnRate(s, now: daysBefore(15)), 1.0, accuracy: 0.001)
        XCTAssertEqual(P.pace(s, now: daysBefore(15)), .green)
        // Plenty left with most of the period gone: green.
        XCTAssertEqual(P.pace(snap(used: 2_000, reset: reset), now: daysBefore(3)), .green)
    }

    func testOverTrendIsOrangeThenRed() {
        // A third of the period gone, 4 000 used → lands at 12 000: orange.
        XCTAssertEqual(P.pace(snap(used: 4_000, reset: reset), now: daysBefore(20)), .orange)
        // A third gone, 6 000 used → 18 000, ×1.8: red.
        XCTAssertEqual(P.pace(snap(used: 6_000, reset: reset), now: daysBefore(20)), .red)
    }

    func testFirstDayIsFlooredToOneDay() {
        // 300 on the first hour of a new period = 300 × 30 = 9 000 projected: still green.
        XCTAssertEqual(P.pace(snap(used: 300, reset: reset), now: daysBefore(29.96)), .green)
        XCTAssertEqual(P.pace(snap(used: 400, reset: reset), now: daysBefore(29.96)), .orange)
    }

    func testNoResetDateMeasuresTheRollingWindowWhole() {
        XCTAssertEqual(P.pace(snap(used: 9_000)), .green)
        XCTAssertEqual(P.pace(snap(used: 12_000)), .red)
        XCTAssertTrue(P.tooltip(snap(used: 5_000), error: nil, fetchedAt: nil).contains("Trend: 5 000 of 10 000"))
    }

    func testZeroLeftIsExhausted() {
        XCTAssertTrue(snap(used: 10_000).exhausted)
    }

    func testBeforeTheFirstAnswer() {
        XCTAssertEqual(P.title(nil, error: nil), "🧾 ElevenLabs …")
        XCTAssertEqual(P.title(nil, error: "no key"), "🧾 ElevenLabs ?")
    }

    func testTotalsAreShortenedToK() {
        XCTAssertEqual(P.kilo(10_000), "10k")
        XCTAssertEqual(P.kilo(100_000), "100k")
        XCTAssertEqual(P.kilo(1_500), "1.5k")
        XCTAssertEqual(P.kilo(500), "500")
    }

    func testMissingUserReadIsRecognised() {
        let body = Data(#"{"detail":{"status":"missing_permissions","message":"missing user_read"}}"#.utf8)
        XCTAssertEqual(P.parseSubscription(status: 401, body: body), .missingUserRead)
    }

    func testSubscriptionGivesAllThreeNumbers() {
        let body = Data(#"{"character_count":1234,"character_limit":10000,"next_character_count_reset_unix":1790812800}"#.utf8)
        XCTAssertEqual(P.parseSubscription(status: 200, body: body),
                       .ok(used: 1234, limit: 10000, reset: Date(timeIntervalSince1970: 1790812800)))
    }

    func testCharacterStatsAreSummed() {
        XCTAssertEqual(P.sumCharacterStats(Data(#"{"time":[1,2],"usage":{"All":[2874.0,35.0]}}"#.utf8)), 2909)
    }

    func testQuotaToleratesSeparators() {
        XCTAssertEqual(P.quota(from: "30 000"), 30_000)
        XCTAssertEqual(P.quota(from: "10_000"), 10_000)
        XCTAssertNil(P.quota(from: nil))
    }
}
