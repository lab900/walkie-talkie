import XCTest
@testable import WalkieTalkie

/// `VoicedMeter` (2026-09-27, Q13): the windows run over the stream, so a
/// buffer length that is not a multiple of 1024 no longer loses its tail.
/// Loopback's 4096 frames at 48 kHz convert to **1365** at 16 kHz — the case
/// that used to meter three quarters of the audio.
final class VoicedMeterTests: XCTestCase {

    /// Room tone, then speech-like bursts of a 220 Hz tone at ~−20 dBFS, then
    /// room tone and a tail that is not a whole window. The bursts are uneven
    /// runs of whole windows *of the stream* — so the truth is exact for a
    /// meter whose windows run over the stream, and 1365-frame buffers cut
    /// across every one of them. Returns the samples and the true voiced seconds.
    private func signal() -> (samples: [Int16], voiced: TimeInterval) {
        let hop = VoicedMeter.hop
        var out: [Int16] = []
        var truth = 0
        var rng = SystemRandomNumberGenerator()
        func tone(_ n: Int) {
            let at = out.count
            for i in 0..<n { out.append(Int16(3000 * sin(2 * .pi * 220 * Double(at + i) / 16000))) }
            truth += n
        }
        func room(_ n: Int) {
            for _ in 0..<n { out.append(Int16.random(in: -20...20, using: &rng)) }
        }
        room(8 * hop)
        for (on, off) in [(5, 3), (7, 3), (4, 5), (10, 3), (6, 8)] {
            tone(on * hop); room(off * hop)
        }
        room(500)
        return (out, Double(truth) / 16000)
    }

    /// Feeds `samples` in buffers of `size` the way `MicRecorder.meter` does,
    /// flushes at the end like `close()`, and returns what it counted.
    private func run(_ samples: [Int16], buffers size: Int) -> (voiced: TimeInterval, hops: [MeterHop]) {
        var meter = VoicedMeter()
        var voiced: TimeInterval = 0, hops: [MeterHop] = []
        samples.withUnsafeBufferPointer { all in
            var i = 0
            while i < all.count {
                let end = min(i + size, all.count)
                let fed = meter.feed(UnsafeBufferPointer(rebasing: all[i..<end]), at: Double(i))
                voiced += fed.seconds
                hops += fed.hops
                i = end
            }
        }
        voiced += meter.flush().seconds
        return (voiced, hops)
    }

    func testLoopbackSizedBuffersCountEverySample() {
        let (x, truth) = signal()
        let (voiced, hops) = run(x, buffers: 1365)
        XCTAssertEqual(voiced, truth, accuracy: 0.1, "1365-frame buffers: \(voiced) s voiced, truth \(truth) s")
        XCTAssertEqual(hops.count, x.count / 1024, "one hop per full window over the whole stream")
    }

    func testWindowSizedBuffersCountEverySample() {
        let (x, truth) = signal()
        let (voiced, _) = run(x, buffers: 1024)
        XCTAssertEqual(voiced, truth, accuracy: 0.1, "1024-frame buffers: \(voiced) s voiced, truth \(truth) s")
    }

    /// The buffer size is the device's business, not the meter's: every full
    /// window — its `t`, its RMS, its verdict — comes out the same whether the
    /// stream arrived in 1024s, 1365s or one piece, and that equals the old
    /// meter on 1024-frame buffers, which never had a tail to drop.
    func testHopsDoNotDependOnBufferSize() {
        let (x, _) = signal()
        let whole = run(x, buffers: x.count).hops
        XCTAssertEqual(run(x, buffers: 1024).hops, whole)
        XCTAssertEqual(run(x, buffers: 1365).hops, whole)
        XCTAssertEqual(run(x, buffers: 333).hops, whole)
        for (k, h) in whole.enumerated() {
            XCTAssertEqual(Double(h.t), Double(k * 1024) / 16000, accuracy: 1e-6)
        }
    }

    /// A sentence that ends mid-window: the last partial window is judged at
    /// the close, at its true length.
    func testFlushCountsAVoicedTail() {
        var x = [Int16](repeating: 5, count: 1024)
        for i in 0..<2500 { x.append(Int16(3000 * sin(2 * .pi * 220 * Double(i) / 16000))) }
        let (voiced, hops) = run(x, buffers: 1365)
        XCTAssertEqual(voiced, Double(2048 + 452) / 16000, accuracy: 1e-9)
        XCTAssertEqual(hops.count, 3, "the partial window adds seconds, not a 64 ms hop")
    }

    func testResetDropsTheCarry() {
        var meter = VoicedMeter()
        let loud = [Int16](repeating: 3000, count: 500)
        _ = loud.withUnsafeBufferPointer { meter.feed($0, at: 0) }
        meter.reset()
        XCTAssertEqual(meter.flush().seconds, 0)
        XCTAssertEqual(meter.noiseFloor, -1)
    }
}
