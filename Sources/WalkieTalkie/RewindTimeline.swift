import Foundation

/// **How far Reverse tunnel has come in, as a function of the clock** (2026-09-23).
///
/// Victor: *"The reverse tunnel effect sometimes takes too long, and the
/// transcription finishes earlier than the animation completes … start the
/// reverse tunnel effect as early as the beginning of the transcription process,
/// and fit it to the expected duration of the transcription."* It was running
/// over **twice** the chip's estimate and never less than 3 s
/// (`max((estimate − warmup) × 2, 3)`), against an estimate taken from the local
/// model's curve whatever engine was live — so a 0.7 s Wispr sentence and a 3 s
/// Scribe one both landed with the tunnel barely a third of the way in.
///
/// Now the approach is fitted to `DecodeRate.predict` — the engine's *typical*
/// round trip, not its near-worst — and both ways of being wrong are absorbed
/// here rather than by the words (the first two bullets superseded on
/// 2026-09-25, below):
///
/// - **On time**: at the predicted instant the approach was at 90 %:
///   visibly converged, and still a little large, so it never reads as *done*
///   before the words are.
/// - **Late**: past the prediction it kept creeping toward 97 %, which it
///   never reached — slower and slower, never still, never at rest.
/// - **Early**: nothing here waits for anything. The words are delivered the
///   moment they arrive and the ring goes out in `collapse`, from wherever it
///   has got to.
///
/// **Ends at 120 % of the prediction, front-loaded** (2026-09-25) — superseded
/// the same week, kept for the record: the approach ended at 1.2 × the
/// prediction (`1 − (1 − u)^1.5`), at rest and held there.
///
/// **Never quite arrives** (2026-09-28). Victor: *"The reverse tunnel animation
/// that shows during the dictation should be logarithmically decreasing so that
/// we rarely hit the final size, and the final size should be 60 % of what it's
/// currently at … It should appear more time to be collapsing, although on a
/// slower pace as it gets slower and slower."* So:
///
/// - **Hyperbolic, not eased**: progress = `1 − 1 / (1 + tail·u)`, `u` the
///   time since the picture showed over the time to the prediction. Steep at
///   first (slope `tail`), then each second brings it a smaller step closer —
///   and it is never 1: at the prediction 80 %, at twice it 89 %, at five times
///   95 %, still creeping. In the geometric size that is 1.5 × rest at the
///   prediction, 1.24 × at twice, 1.1 × at five times. The words interrupt it
///   from wherever it got to (`collapse`); a late answer finds it moving.
/// - **Every size 0.6 of what it was**: `sizeFactor` 0.7 → 0.42.
/// - **The opacity keeps the prediction's clock** (`Pose.time`), as before.
///
/// Pure, so it is unit-tested (`Tests/WalkieTalkieTests/RewindTimingTests`).
enum RewindTimeline {
    /// How steep the hyperbola leaves (2026-09-28): the progress at the
    /// prediction is `tail / (1 + tail)` — 0.8 at 4.
    static let tail = 4.0
    /// The shortest approach worth drawing once the picture is visible — a
    /// prediction shorter than the warm-up would otherwise be a jump.
    static let minimumSpan = 0.6
    /// How fast the ring goes when the words land — *"fade out foarte repede"*.
    static let collapse: TimeInterval = 0.15

    struct Pose: Equatable {
        /// 0 = huge and invisible, → 1 at rest round the pointer, never reached.
        let progress: Double
        /// 0…1 of the time to the prediction, clamped — what the opacity reads.
        let time: Double
    }

    /// Steep at `u` = 0, ever flatter, never 1: `1 − 1 / (1 + tail·u)`, 0 for `u` ≤ 0.
    static func creep(_ u: Double) -> Double {
        guard u > 0 else { return 0 }
        return 1 - 1 / (1 + tail * u)
    }

    /// - Parameters:
    ///   - elapsed: seconds since the transcription began (the microphone's close).
    ///   - predicted: the typical round trip for this audio on this engine.
    ///   - visibleFrom: when the picture can first be seen — the engine's
    ///     warm-up. `u` = 1 at the prediction.
    static func pose(elapsed: TimeInterval, predicted: TimeInterval, visibleFrom: TimeInterval) -> Pose {
        let since = elapsed - visibleFrom
        guard since > 0 else { return Pose(progress: 0, time: 0) }
        let span = max(predicted - visibleFrom, minimumSpan)
        return Pose(progress: creep(since / span), time: min(since / span, 1))
    }

    /// **The whole tunnel 30 % smaller** (Victor, 2026-09-23: *"reduce the
    /// reverse tunnel's default size during transcription by 30%"*), then **60 %
    /// of that** (2026-09-28: *"the final size should be 60 % of what it's
    /// currently at"*): 0.7 × 0.6 = 0.42, a factor on every size of the run —
    /// the huge start, the creep, the rest it never quite reaches. Here rather
    /// than on the preset's `scale`, which would also change the engine's render
    /// resolution; `approach` is called for the rewind alone.
    static let sizeFactor = 0.42

    /// The stamp's scale (× the preset's resting size) and opacity for a pose,
    /// starting at `from` × `sizeFactor` — geometric in the scale, so each
    /// second shrinks it by the same ratio; the opacity rises ahead of it
    /// (t^0.6), so the tunnel is there, huge and faint, from the first frames.
    static func stamp(_ pose: Pose, from: Double) -> (scale: Double, alpha: Double) {
        (sizeFactor * pow(from, 1 - pose.progress), pow(pose.time, 0.6))
    }
}
