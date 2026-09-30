import XCTest
@testable import WalkieTalkie

/// The corner hint bar per stage: what each gesture does *now*, drawn as two
/// crosses — 🔼 then 🔽 (2026-09-30) — and nothing at all when no sentence is open.
final class GestureHintBarTests: XCTestCase {

    typealias Cross = GestureHintBar.Cross

    func testNothingWhenNotDictating() {
        XCTAssertEqual(GestureHintBar.crosses(for: .init()), [])
    }

    func testAPromptIsVictorsSketch() {
        XCTAssertEqual(GestureHintBar.crosses(for: .init(listening: true, prompting: true)), [
            Cross(click: "🏁 end", up: "✨ new", down: "☠️", left: "🗑️ cancel", right: nil),
            Cross(click: "📸 shot", up: "🔴 video", down: "", left: "", right: ""),
        ])
    }

    func testTheFilmKamikazeAndSpawnFollowTheirState() {
        let c = GestureHintBar.crosses(for: .init(listening: true, prompting: true, filming: true,
                                                  kamikaze: true, spawn: true))
        XCTAssertEqual(c[0].up, "", "a new session already marked: the box stays, empty")
        XCTAssertEqual(c[0].down, "~☠️", "crossed out, no words")
        XCTAssertEqual(c[1].up, "⏹️ video")
    }

    func testAPlainDictationOnlyStopsOrCancels() {
        XCTAssertEqual(GestureHintBar.crosses(for: .init(listening: true, prompting: false)), [
            Cross(click: "", up: "", down: "", left: "🗑️ cancel", right: nil),
            Cross(click: "⏹️ + ⏎", up: "", down: "", left: "", right: "⏹️"),
        ])
    }

    func testNothingWhileRightCmdOptIsHeld() {
        XCTAssertEqual(GestureHintBar.crosses(for: .init(listening: true, prompting: false, held: true)), [])
    }

    /// `HINT_BAR_PNG=<dir> swift test --filter GestureHintBarTests` draws each
    /// stage over a dark and a light desktop, to look at.
    func testRenderForReview() throws {
        guard let dir = ProcessInfo.processInfo.environment["HINT_BAR_PNG"] else { return }
        let stages: [(String, GestureHintBar.Stage)] = [
            ("prompt", .init(listening: true, prompting: true)),
            ("prompt-filming", .init(listening: true, prompting: true, filming: true, kamikaze: true, spawn: true)),
            ("plain", .init(listening: true, prompting: false)),
        ]
        for (name, stage) in stages {
            for (bgName, bg) in [("dark", NSColor(white: 0.12, alpha: 1)), ("light", NSColor(white: 0.93, alpha: 1))] {
                let crosses = GestureHintBar.crosses(for: stage)
                let size = GestureHintBar.Board.size(for: crosses)
                let board = GestureHintBar.Board(frame: NSRect(x: 20, y: 20, width: size.width, height: size.height))
                board.crosses = crosses
                let host = NSView(frame: NSRect(x: 0, y: 0, width: size.width + 40, height: size.height + 40))
                host.wantsLayer = true
                host.layer?.backgroundColor = bg.cgColor
                host.addSubview(board)
                let rep = try XCTUnwrap(host.bitmapImageRepForCachingDisplay(in: host.bounds))
                host.cacheDisplay(in: host.bounds, to: rep)
                try XCTUnwrap(rep.representation(using: .png, properties: [:]))
                    .write(to: URL(fileURLWithPath: dir).appendingPathComponent("\(name)-\(bgName).png"))
            }
        }
    }
}
