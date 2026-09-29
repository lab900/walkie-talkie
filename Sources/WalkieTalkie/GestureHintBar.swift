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

    /// The hints for a stage, in the order he reaches for them. Pure, so the
    /// wording can be checked without a screen.
    static func hints(for s: Stage) -> [String] {
        guard s.listening else { return [] }
        if !s.prompting {
            return ["🔽→ stop", "🔽 stop + ⏎", "🔼← cancel", "⌘⌃X local model"]
        }
        var out = ["🔼 end dictation", "🔼← cancel", "🔽 screenshot",
                   s.filming ? "🔽↑ stop video" : "🔽↑ start video",
                   s.kamikaze ? "🔼↓ no kamikaze" : "🔼↓ kamikaze"]
        if !s.spawn { out.append("🔼↑ new session") }
        out.append("⌘⌃X local model")
        return out
    }

    private var panel: NSPanel?
    private var label: NSTextField?
    private var shown = Stage()

    private static let font = NSFont.systemFont(ofSize: 12, weight: .medium)
    private static let height: CGFloat = 26
    private static let padding: CGFloat = 12
    private static let margin: CGFloat = 16

    func update(_ stage: Stage) {
        let visible = stage.listening && AboutWindow.logiGesturesOn
        guard stage != shown || (panel != nil) != visible else { return }
        shown = stage
        guard visible else { hide(); return }
        show(Self.hints(for: stage).joined(separator: "   ·   "))
    }

    private func show(_ text: String) {
        guard let screen = Self.screenUnderMouse() else { return }
        let width = ceil((text as NSString).size(withAttributes: [.font: Self.font]).width) + Self.padding * 2
        let v = screen.visibleFrame
        let rect = NSRect(x: v.maxX - width - Self.margin, y: v.minY + Self.margin,
                          width: width, height: Self.height)
        if let panel, let label {
            label.stringValue = text
            panel.setFrame(rect, display: true)
            label.frame = NSRect(x: Self.padding, y: 0, width: width - Self.padding * 2, height: Self.height - 5)
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

        let content = NSView(frame: NSRect(origin: .zero, size: rect.size))
        content.wantsLayer = true
        content.layer?.cornerRadius = Self.height / 2
        content.layer?.backgroundColor = NSColor.black.withAlphaComponent(0.62).cgColor
        content.autoresizingMask = [.width, .height]
        let l = NSTextField(labelWithString: text)
        l.font = Self.font
        l.textColor = NSColor.white.withAlphaComponent(0.9)
        l.alignment = .center
        l.lineBreakMode = .byClipping
        l.frame = NSRect(x: Self.padding, y: 0, width: width - Self.padding * 2, height: Self.height - 5)
        l.autoresizingMask = [.width]
        content.addSubview(l)
        p.contentView = content
        p.alphaValue = 0
        p.orderFrontRegardless()
        NSAnimationContext.runAnimationGroup { $0.duration = 0.2; p.animator().alphaValue = 1 }
        panel = p
        label = l
        Log.info("⌨️ hint bar: \(text)")
    }

    private func hide() {
        guard let p = panel else { return }
        panel = nil
        label = nil
        NSAnimationContext.runAnimationGroup({ $0.duration = 0.25; p.animator().alphaValue = 0 },
                                            completionHandler: { p.orderOut(nil) })
    }

    private static func screenUnderMouse() -> NSScreen? {
        let at = NSEvent.mouseLocation
        return NSScreen.screens.first { NSMouseInRect(at, $0.frame, false) } ?? NSScreen.main
    }
}
