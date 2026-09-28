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
        XCTAssertEqual(P.title(s, error: nil, timeZone: utc), "🧾 ElevenLabs −33 / 10k / ?")
        XCTAssertTrue(s.exhausted)
        XCTAssertTrue(P.tooltip(s, error: nil, fetchedAt: nil).contains("user_read"))
    }

    func testRemainingAndResetDate() {
        let s = snap(used: 8_766, reset: Date(timeIntervalSince1970: 1_790_812_800)) // 2026-10-01 UTC
        XCTAssertEqual(P.title(s, error: nil, timeZone: utc), "🧾 ElevenLabs 1234 / 10k / Oct 1")
        XCTAssertFalse(s.exhausted)
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
