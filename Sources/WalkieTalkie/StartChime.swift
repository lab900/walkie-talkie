import AppKit

/// **The sound of the microphone opening** (2026-10-01). Victor: *"când începe să
/// asculte dictarea, să facă un zgomot ca de mică decepție, un hăuit scurt"* — a
/// short falling "womp", synthesised here so no audio file rides in the bundle.
/// `WT_START_SOUND=0` silences it for a run.
enum StartChime {
    static let isOn = ProcessInfo.processInfo.environment["WT_START_SOUND"] != "0"

    private static let sound: NSSound? = NSSound(data: wav())

    static func play() {
        guard isOn, let sound else { return }
        if sound.isPlaying { sound.stop() }
        sound.play()
    }

    /// 0.24 s: a sine with a soft second harmonic gliding down a fourth
    /// (520 → 390 Hz), a 12 ms attack and an exponential fall.
    private static func wav() -> Data {
        let rate = 44_100.0, seconds = 0.24
        let n = Int(rate * seconds)
        var samples = [Int16](repeating: 0, count: n)
        var phase = 0.0
        for i in 0..<n {
            let t = Double(i) / rate, x = t / seconds
            let freq = 520.0 * pow(390.0 / 520.0, x)
            phase += 2 * .pi * freq / rate
            let attack = min(1, t / 0.012)
            let env = attack * exp(-3.2 * x) * (1 - x * x * x)
            let v = (sin(phase) + 0.25 * sin(2 * phase)) / 1.25 * env * 0.35
            samples[i] = Int16(max(-1, min(1, v)) * Double(Int16.max))
        }
        var d = Data()
        func u32(_ v: UInt32) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        func u16(_ v: UInt16) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        let bytes = UInt32(n * 2)
        d.append(contentsOf: Array("RIFF".utf8)); u32(36 + bytes)
        d.append(contentsOf: Array("WAVEfmt ".utf8)); u32(16); u16(1); u16(1)
        u32(UInt32(rate)); u32(UInt32(rate) * 2); u16(2); u16(16)
        d.append(contentsOf: Array("data".utf8)); u32(bytes)
        samples.withUnsafeBytes { d.append(contentsOf: $0) }
        return d
    }
}
