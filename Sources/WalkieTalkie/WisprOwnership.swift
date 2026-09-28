import Foundation

/// **Whose is a Wispr ⌘V after the relay's own sentence went idle** — the pure
/// half of the firewall's tail (B, lab wave 2, 2026-09-28; `HotkeyTap` holds the
/// state, `WisprFlowSource` feeds it the rows).
///
/// The tail used to be a clock: every Wispr ⌘V within 10 s of the relay's
/// sentence going idle was dropped as *the relay's late paste*. In the lab that
/// ate **8 of his 8** own right ⌥⇧ sentences that landed in those 10 s, all of
/// them `formatted` by Wispr, all dropped with a log line only. Q19 (Victor's
/// Q7 = A) already said what his sentence is: his, pasted at the caret.
///
/// A ⌘V does not say which row it pastes. The rows do: Wispr creates a row at
/// the gesture, so his sentence has a row **newer than the relay's** seconds
/// before its ⌘V arrives. So the tail is keyed on rows, not the clock.
enum WisprOwnership {

    /// A ⌘V from Wispr: the relay's (drop — the row delivers) or not (pass).
    enum Verdict: Equatable {
        /// The relay's sentence, its late row, or the tail with no newer row seen.
        case relays(String)
        /// Not the relay's: Q9 (no relay sentence near) or his newer row in the tail.
        case passes(String)
    }

    /// - Parameters:
    ///   - since: the relay's gesture (0 = never owned).
    ///   - releasedAt: when its machine went idle (0 = still in flight).
    ///   - rowsHeld: rows the relay gave up on and still watches (Q2/Q14).
    ///   - foreignRow: a newer row the tail watch judged not the relay's (0 = none).
    static func verdict(now: Double, since: Double, releasedAt: Double, rowsHeld: Int,
                        foreignRow: Int64, tail: Double, ceiling: Double) -> Verdict {
        if rowsHeld > 0 { return .relays("a row the relay gave up on is still being watched") }
        guard since > 0, now - since < ceiling else { return .passes("no relay sentence near (Q9)") }
        if releasedAt == 0 { return .relays("the relay's sentence is in flight") }
        guard now - releasedAt < tail else { return .passes("past the relay's tail (Q9)") }
        if foreignRow > 0 { return .passes("row \(foreignRow) is newer than the relay's — his own sentence") }
        return .relays(String(format: "the relay's tail (%.1f s after idle), no newer row of his seen", now - releasedAt))
    }

    /// **Is this row his, not the relay's?** Asked by the tail watch of the
    /// newest `History` row.
    ///
    /// - Parameters:
    ///   - floor: the newest rowid the relay knows as its own or as older than
    ///     its gesture — max(its adopted row, the row on top at its chord).
    ///   - relayHadRow: whether the relay adopted a row for that sentence. When
    ///     it did not (a cold Wispr, no answer to the chord), a row that shows up
    ///     later may still be the relay's own, created late — so it also has to
    ///     have started at or after the relay's close.
    ///   - relayClosedAt: unix time the relay's sentence closed (its stop chord).
    ///   - relayCmdVSeen / sinceRelease: the relay's own ⌘V for its row is not
    ///     mistaken for his while it may still be coming — the row is his only
    ///     once the relay's ⌘V was seen or `pasteWait` has passed since idle.
    static func rowIsHis(rowid: Int64, startedAt: Double, floor: Int64, relayHadRow: Bool,
                         relayClosedAt: Double, relayCmdVSeen: Bool, sinceRelease: Double,
                         pasteWait: Double = 1.5) -> Bool {
        guard rowid > floor else { return false }
        // `startedAt` is whole seconds (strftime %s truncates): compare floors.
        if !relayHadRow, startedAt < relayClosedAt.rounded(.down) { return false }
        return relayCmdVSeen || sinceRelease >= pasteWait
    }
}
