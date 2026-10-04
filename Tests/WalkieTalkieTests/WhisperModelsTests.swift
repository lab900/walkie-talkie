import XCTest
@testable import WalkieTalkie

/// The local model picker (2026-10-03): full-size V3 before turbo, the original
/// before a LoRA on it (2026-10-04), titled from each `model-card.json`.
final class WhisperModelsTests: XCTestCase {

    private let card = """
    {"name": "whisper-turbo-victor", "label": "Large V3-turbo Victor LoRA", "short": "V3t-victor", "base": "openai/whisper-large-v3-turbo",
     "method": "LoRA r=32", "data": "3,086 clips / 9.3 h", "trained": "2026-10-03 on Runpod H100 SXM",
     "cost_usd": 3.6, "held-out": "733 Wispr dictations: WER 20.4% → 15.3%",
     "wer": {"before": 20.4, "after": 15.3}}
    """

    func testTitleIsReadFromTheCard() throws {
        let c = try XCTUnwrap(WhisperModels.Card.parse(Data(card.utf8)))
        let option = WhisperModels.Option(id: "/x/whisper-turbo-victor", card: c)
        XCTAssertEqual(StatusItem.localRowTitle(option, loading: false),
                       "Large V3-turbo Victor LoRA 💻")
        XCTAssertEqual(option.shortTitle, "V3t-victor")
        XCTAssertTrue(option.details.hasPrefix(
            "whisper-turbo-victor · trained 3 Oct 2026 · $3.6 · WER 20.4→15.3%\n"))
        XCTAssertTrue(option.details.contains("Base: openai/whisper-large-v3-turbo"))
        XCTAssertTrue(option.details.contains("Held-out: 733 Wispr dictations"))
    }

    func testOriginalIsNamedAsSuch() {
        XCTAssertEqual(StatusItem.localRowTitle(WhisperModels.Option(id: WhisperModels.original, card: nil),
                                                loading: false),
                       "Large V3-turbo 💻")
        XCTAssertEqual(WhisperModels.Option(id: WhisperModels.original, card: nil).shortTitle, "V3t")
        let noLabel = WhisperModels.Card(name: "x-model")
        XCTAssertEqual(WhisperModels.Option(id: "/m/x", card: noLabel).title, "x-model")
    }

    func testOptionsListV3ThenTurboOriginalFirst() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: dir) }
        let good = dir.appendingPathComponent("whisper-turbo-victor")
        let noWeights = dir.appendingPathComponent("half-copied")
        for d in [good, noWeights] { try FileManager.default.createDirectory(at: d, withIntermediateDirectories: true) }
        for f in ["config.json", "weights.safetensors"] {
            try Data("{}".utf8).write(to: good.appendingPathComponent(f))
        }
        try Data(card.utf8).write(to: good.appendingPathComponent("model-card.json"))
        try Data("{}".utf8).write(to: noWeights.appendingPathComponent("config.json"))

        // A LoRA on the full-size V3 goes before the original turbo (2026-10-04).
        let large = dir.appendingPathComponent("whisper-large-victor")
        try FileManager.default.createDirectory(at: large, withIntermediateDirectories: true)
        for f in ["config.json", "weights.safetensors"] {
            try Data("{}".utf8).write(to: large.appendingPathComponent(f))
        }
        try Data(#"{"name": "whisper-large-victor", "base": "openai/whisper-large-v3"}"#.utf8)
            .write(to: large.appendingPathComponent("model-card.json"))

        let ids = WhisperModels.options(in: dir).map(\.id)
        XCTAssertEqual(ids, [large.path, WhisperModels.original, good.path])
        XCTAssertEqual(WhisperModels.options(in: dir).last?.card?.name, "whisper-turbo-victor")
    }

    func testABadCardFallsBackToTheFolderName() {
        XCTAssertNil(WhisperModels.Card.parse(Data("{\"base\": \"x\"}".utf8)))
        XCTAssertEqual(WhisperModels.Option(id: "/m/some-model", card: nil).title, "some-model")
    }
}
