import Foundation

/// **Auto fallback to local (p98)** — the Engine submenu's checkbox
/// (2026-09-28). Victor, 22:25: *"I don't think I will ever have the patience to
/// wait for 36 seconds. I will probably hit ⌘⌃X and use the local model
/// fallback. Plus, 10 s startup time is killing. … (Auto fallback to local model
/// should be a checkbox in the Engine submenu.)"*
///
/// ON (the default): a sentence waiting on ElevenLabs or Wispr Flow longer than
/// its budget (`DecodeRate.budget`, the engine's p98 for that length, clamped)
/// is handed to this Mac exactly as ⌘⌃X hands it (`via: local-auto`); the local
/// weights are kept warm while another engine is picked; and a sentence started
/// on Engine = Wispr while Wispr Flow is not running (or still starting) goes to
/// the local model at once while Wispr is launched in the background.
/// OFF: the behaviour before that evening — the relay waits on the engine.
enum AutoLocal {

    /// `UserDefaults` beside `dictationSource` and `autosend`: a preference,
    /// not data, so `--home` does not move it.
    static let defaultsKey = "autoLocalFallback"

    static var isOn: Bool {
        get { UserDefaults.standard.object(forKey: defaultsKey) as? Bool ?? true }
        set { UserDefaults.standard.set(newValue, forKey: defaultsKey) }
    }

    /// The Engine submenu's row title.
    static let menuTitle = "Auto fallback to local (p98)"

    /// **The chip's row while the budget runs** — `Local in 2.1 s  ⌘⌃X`
    /// (tenths; never below 0.0). Nil countdown is ⌘⌃X's own `Local now`.
    static func rowText(countdown: TimeInterval?, loading: Bool, keys: String) -> String {
        let head: String
        if let c = countdown {
            head = String(format: "Local in %.1f s", max(0, (c * 10).rounded(.up) / 10))
        } else {
            head = "Local now"
        }
        return head + (loading ? " (loading)" : "") + "  " + keys
    }

    /// The flash when the budget runs out: `💻 Local — ElevenLabs over budget (2.4 s)`.
    static func overBudgetFlash(engine: String, budget: TimeInterval) -> String {
        String(format: "💻 Local — %@ over budget (%.1f s)", engine, budget)
    }

    /// The flash when a Wispr sentence starts with Wispr Flow down (or just launched).
    static let wisprStartingFlash = "💻 Local — Wispr Flow is starting"

    /// A Wispr Flow the relay launched itself counts as *starting* this long —
    /// Victor: *"10 s startup time is killing"*. The process is up well before
    /// its microphone answers a chord.
    static let wisprStartupGrace: TimeInterval = 12
}
