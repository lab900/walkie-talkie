import AppKit

/// **The gestures that work right now, bottom right of the screen** (2026-09-29).
///
/// Victor: *"during dictation, show a small hint bar in the bottom right of the
/// screen with the key combos available at that stage (eg 🔽↑ stop video,
/// 🔼 end dictation...)"*. The chip by the pointer says what the sentence *is*;
/// this says what he can *do* to it, and changes with the stage: a prompt
/// offers the shutter, the film, kamikaze and a new session; a plain dictation
/// only its stop, its stop-and-Return and the cancel.
///
/// **Drawn as two crosses, one per side button** (2026-09-30, from his sketch):
/// 🔼 on top, 🔽 under it, as the buttons sit on the mouse. The centre box is the
/// click, the arms are the swipes, and a gesture with nothing to do right now
/// keeps an empty box so the shape — and where his thumb goes — never moves.
/// 🔼 → has no box at all: it ends the sentence like the click does.
///
/// Only in Logi mode — the glyphs are the side buttons' (`AboutWindow.logiGesturesOn`).
/// Never in a screenshot (`sharingType = .none`), never takes the mouse, and it
/// does not ride the pointer: a fixed corner, so it is read at a glance.
final class GestureHintBar {

    /// What the chip knows about the sentence, which is all the bar needs.
    struct Stage: Equatable {
        var listening = false
        /// A prompt (🔼 / 🔼 → / 🔼 ↑); false for a plain dictation.
        var prompting = false
        var filming = false
        var kamikaze = false
        /// The sentence already opens a new session — 🔼 ↑ has nothing left to do.
        var spawn = false
    }

    /// One button's gestures. `nil` = no box is drawn, `""` = an empty box.
    struct Cross: Equatable {
        var click: String? = ""
        var up: String? = ""
        var down: String? = ""
        var left: String? = ""
        var right: String? = ""
    }

    /// The two crosses for a stage — 🔼 first, 🔽 second. Pure, so the wording
    /// can be checked without a screen.
    static func crosses(for s: Stage) -> [Cross] {
        guard s.listening else { return [] }
        var front = Cross(right: nil)
        var back = Cross()
        front.left = "🗑️ cancel"
        if s.prompting {
            front.click = "🏁 end"
            front.up = s.spawn ? "" : "✨ new"
            front.down = s.kamikaze ? "☠️ no kamikaze" : "☠️ kamikaze"
            back.click = "📸 shot"
            back.up = s.filming ? "⏹️ stop video" : "🔴 video"
        } else {
            back.click = "⏎ stop + enter"
            back.right = "⏹️ stop"
        }
        return [front, back]
    }

    private var panel: NSPanel?
    private var board: Board?
    private var shown = Stage()

    fileprivate static let font = NSFont.systemFont(ofSize: 12, weight: .medium)
    fileprivate static let boxHeight: CGFloat = 24
    fileprivate static let minBoxWidth: CGFloat = 92
    fileprivate static let padding: CGFloat = 10
    fileprivate static let gap: CGFloat = 4
    /// Between the 🔼 cross and the 🔽 one: a row's worth, as in the sketch.
    fileprivate static let crossGap: CGFloat = 14
    private static let margin: CGFloat = 16

    func update(_ stage: Stage) {
        let visible = stage.listening && AboutWindow.logiGesturesOn
        guard stage != shown || (panel != nil) != visible else { return }
        shown = stage
        guard visible else { hide(); return }
        show(Self.crosses(for: stage))
    }

    private func show(_ crosses: [Cross]) {
        guard let screen = Self.screenUnderMouse() else { return }
        let size = Board.size(for: crosses)
        let v = screen.visibleFrame
        let rect = NSRect(x: v.maxX - size.width - Self.margin, y: v.minY + Self.margin,
                          width: size.width, height: size.height)
        Log.info("⌨️ hint bar: \(crosses.map(Self.describe).joined(separator: " / "))")
        if let panel, let board {
            board.crosses = crosses
            panel.setFrame(rect, display: true)
            return
        }
        let p = NSPanel(contentRect: rect, styleMask: [.borderless, .nonactivatingPanel],
                        backing: .buffered, defer: false)
        p.level = .statusBar
        p.isFloatingPanel = true
        p.backgroundColor = .clear
        p.isOpaque = false
        p.hasShadow = false
        p.ignoresMouseEvents = true
        p.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary, .ignoresCycle]
        p.sharingType = .none

        let b = Board(frame: NSRect(origin: .zero, size: rect.size))
        b.crosses = crosses
        b.autoresizingMask = [.width, .height]
        p.contentView = b
        p.alphaValue = 0
        p.orderFrontRegardless()
        NSAnimationContext.runAnimationGroup { $0.duration = 0.2; p.animator().alphaValue = 1 }
        panel = p
        board = b
    }

    private func hide() {
        guard let p = panel else { return }
        panel = nil
        board = nil
        NSAnimationContext.runAnimationGroup({ $0.duration = 0.25; p.animator().alphaValue = 0 },
                                            completionHandler: { p.orderOut(nil) })
    }

    private static func describe(_ c: Cross) -> String {
        [("·", c.click), ("↑", c.up), ("↓", c.down), ("←", c.left), ("→", c.right)]
            .compactMap { k, v in v.flatMap { $0.isEmpty ? nil : "\(k) \($0)" } }
            .joined(separator: ", ")
    }

    private static func screenUnderMouse() -> NSScreen? {
        let at = NSEvent.mouseLocation
        return NSScreen.screens.first { NSMouseInRect(at, $0.frame, false) } ?? NSScreen.main
    }

    /// The crosses, drawn. A three-column grid shared by both, so their centre
    /// boxes line up; every box is as wide as the widest label, so the board
    /// does not change width when a label does.
    final class Board: NSView {
        var crosses: [Cross] = [] { didSet { needsDisplay = true } }

        override var isFlipped: Bool { true }

        static func boxWidth(for crosses: [Cross]) -> CGFloat {
            let labels = crosses.flatMap { [$0.click, $0.up, $0.down, $0.left, $0.right] }.compactMap { $0 }
            let widest = labels.map { ($0 as NSString).size(withAttributes: [.font: GestureHintBar.font]).width }
                .max() ?? 0
            return max(GestureHintBar.minBoxWidth, ceil(widest) + GestureHintBar.padding * 2)
        }

        static func size(for crosses: [Cross]) -> NSSize {
            let w = boxWidth(for: crosses)
            let crossHeight = GestureHintBar.boxHeight * 3 + GestureHintBar.gap * 2
            let n = CGFloat(crosses.count)
            return NSSize(width: w * 3 + GestureHintBar.gap * 2,
                          height: crossHeight * n + GestureHintBar.crossGap * max(0, n - 1))
        }

        override func draw(_ dirtyRect: NSRect) {
            let w = Self.boxWidth(for: crosses)
            let h = GestureHintBar.boxHeight, gap = GestureHintBar.gap
            let crossHeight = h * 3 + gap * 2
            for (i, c) in crosses.enumerated() {
                let top = CGFloat(i) * (crossHeight + GestureHintBar.crossGap)
                func box(_ text: String?, col: Int, row: Int) {
                    guard let text else { return }
                    let r = NSRect(x: CGFloat(col) * (w + gap), y: top + CGFloat(row) * (h + gap),
                                   width: w, height: h)
                    drawBox(text, in: r)
                }
                box(c.up, col: 1, row: 0)
                box(c.left, col: 0, row: 1)
                box(c.click, col: 1, row: 1)
                box(c.right, col: 2, row: 1)
                box(c.down, col: 1, row: 2)
            }
        }

        private func drawBox(_ text: String, in r: NSRect) {
            let empty = text.isEmpty
            let path = NSBezierPath(roundedRect: r.insetBy(dx: 0.5, dy: 0.5), xRadius: 4, yRadius: 4)
            NSColor.black.withAlphaComponent(empty ? 0.22 : 0.66).setFill()
            path.fill()
            NSColor.white.withAlphaComponent(empty ? 0.22 : 0.45).setStroke()
            path.lineWidth = 1
            path.stroke()
            guard !empty else { return }
            let style = NSMutableParagraphStyle()
            style.alignment = .center
            style.lineBreakMode = .byClipping
            let attrs: [NSAttributedString.Key: Any] = [
                .font: GestureHintBar.font,
                .foregroundColor: NSColor.white.withAlphaComponent(0.92),
                .paragraphStyle: style,
            ]
            let s = text as NSString
            let th = s.size(withAttributes: attrs).height
            s.draw(in: NSRect(x: r.minX + 4, y: r.midY - th / 2, width: r.width - 8, height: th),
                   withAttributes: attrs)
        }
    }
}
