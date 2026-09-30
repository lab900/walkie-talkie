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
        /// Right ⌘⌥ is held for it: his hand is on the keyboard, not the mouse,
        /// so there is nothing to show (2026-09-30, Victor: *"no need to display
        /// those shortcuts while cmd-opt pressed down dictation"*).
        var held = false
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
        guard s.listening, !s.held else { return [] }
        var front = Cross(right: nil)
        var back = Cross()
        front.left = "🗑️ cancel"
        if s.prompting {
            front.click = "🏁 end"
            front.up = s.spawn ? "" : "✨ new"
            // Kamikaze is its emoji alone, crossed out once it is on (2026-09-30,
            // Victor: *"instead of 'no kamikaze', kamikaze crossed out"*).
            front.down = s.kamikaze ? Self.struck + "☠️" : "☠️"
            back.click = "📸 shot"
            // Stop is ⏹️, never the word (2026-09-30).
            back.up = s.filming ? "⏹️ video" : "🔴 video"
        } else {
            back.click = "⏹️ + ⏎"
            back.right = "⏹️"
        }
        return [front, back]
    }

    /// A label starting with this is drawn crossed out, without it.
    static let struck = "~"

    private var panel: NSPanel?
    private var board: Board?
    private var shown = Stage()

    fileprivate static let font = NSFont.systemFont(ofSize: 12, weight: .medium)
    fileprivate static let boxHeight: CGFloat = 24
    fileprivate static let minBoxWidth: CGFloat = 68
    fileprivate static let padding: CGFloat = 6
    fileprivate static let gap: CGFloat = 4
    /// Between the 🔼 cross and the 🔽 one: a row's worth, as in the sketch —
    /// widened 2026-09-30 so the two read as two buttons.
    fileprivate static let crossGap: CGFloat = 24
    /// The whole bar is see-through (2026-09-30, Victor: *"should be semi-transparent"*):
    /// it sits over whatever he is working on in that corner.
    fileprivate static let opacity: CGFloat = 0.6
    private static let margin: CGFloat = 16

    func update(_ stage: Stage) {
        let visible = stage.listening && !stage.held && AboutWindow.logiGesturesOn
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
            let cg = NSGraphicsContext.current?.cgContext
            cg?.setAlpha(GestureHintBar.opacity)
            cg?.beginTransparencyLayer(auxiliaryInfo: nil)
            defer { cg?.endTransparencyLayer() }
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

        private func drawBox(_ label: String, in r: NSRect) {
            let struck = label.hasPrefix(GestureHintBar.struck)
            let text = struck ? String(label.dropFirst(GestureHintBar.struck.count)) : label
            let empty = text.isEmpty
            let path = NSBezierPath(roundedRect: r.insetBy(dx: 0.5, dy: 0.5), xRadius: 4, yRadius: 4)
            // An unused gesture is a plain gray box (2026-09-30, Victor: *"place
            // gray boxes on all unused gestures"*) — seen, and plainly not a label.
            (empty ? NSColor(white: 0.5, alpha: 0.55) : NSColor.black.withAlphaComponent(0.66)).setFill()
            path.fill()
            NSColor.white.withAlphaComponent(empty ? 0.3 : 0.45).setStroke()
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
            let ts = s.size(withAttributes: attrs)
            s.draw(in: NSRect(x: r.minX + 4, y: r.midY - ts.height / 2, width: r.width - 8, height: ts.height),
                   withAttributes: attrs)
            guard struck else { return }
            let half = min(ts.width, r.width - 8) / 2 + 3
            let slash = NSBezierPath()
            slash.move(to: NSPoint(x: r.midX - half, y: r.maxY - 3))
            slash.line(to: NSPoint(x: r.midX + half, y: r.minY + 3))
            slash.lineWidth = 2.5
            slash.lineCapStyle = .round
            NSColor.systemRed.setStroke()
            slash.stroke()
        }
    }
}
