import AppKit

/// **The sound of the microphone opening.** It was a falling "womp" for one
/// morning (2026-10-01); Victor then asked for it out — *"înlocuiește-l cu un
/// hârâit ca de transmisie (white noise scurt), debifat by default în meniu"* —
/// so it is now a radio's squelch burst, synthesised here so no audio file rides
/// in the bundle, and it plays only while the `Radio Squelch` row is ticked.
enum StartChime {

    /// `UserDefaults` beside `autosend`: a preference, not data. Absent = off.
    static let defaultsKey = "startSquelch"

    static var isOn: Bool {
        get { UserDefaults.standard.bool(forKey: defaultsKey) }
        set { UserDefaults.standard.set(newValue, forKey: defaultsKey) }
    }

    /// The menu row's title.
    static let menuTitle = "Radio Squelch"

    private static let sound: NSSound? = NSSound(data: wav())

    static func play() {
        guard isOn, let sound else { return }
        if sound.isPlaying { sound.stop() }
        sound.play()
    }

    /// 0.16 s of white noise squeezed into a radio's band (one-pole high-pass
    /// at ~350 Hz, two low-passes at ~3 kHz), a 30 ms fade in, a fast 60 Hz
    /// flutter for the crackle and a 50 ms fade out — the "kssh" of a key-up,
    /// quiet (*"fă-l de 3x mai discret"*, then −30 %: gain 0.9 → 0.3 → 0.21).
    /// A fixed seed, so every launch hisses the same.
    private static func wav() -> Data {
        let rate = 44_100.0, seconds = 0.16
        let n = Int(rate * seconds)
        var samples = [Int16](repeating: 0, count: n)
        var seed: UInt32 = 0x5EED_1234
        func noise() -> Double {
            seed = seed &* 1_664_525 &+ 1_013_904_223
            return Double(seed >> 8) / Double(1 << 23) - 1
        }
        let hp = exp(-2 * .pi * 350 / rate), lp = 1 - exp(-2 * .pi * 3000 / rate)
        var hpIn = 0.0, hpOut = 0.0, lp1 = 0.0, lp2 = 0.0
        for i in 0..<n {
            let t = Double(i) / rate
            let x = noise()
            hpOut = hp * (hpOut + x - hpIn); hpIn = x
            lp1 += lp * (hpOut - lp1)
            lp2 += lp * (lp1 - lp2)
            // Raised-cosine edges, 30 ms in and 50 ms out — linear 4/25 ms ones
            // were "prea brutal" (2026-10-01).
            let attack = 0.5 - 0.5 * cos(.pi * min(1, t / 0.030))
            let release = 0.5 - 0.5 * cos(.pi * min(1, (seconds - t) / 0.050))
            let flutter = 0.75 + 0.25 * sin(2 * .pi * 60 * t)
            let v = lp2 * attack * release * flutter * 0.21
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
