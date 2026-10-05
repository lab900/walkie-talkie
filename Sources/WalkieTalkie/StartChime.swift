import AppKit

/// **The sound of the microphone opening.** It was a falling "womp" for one
/// morning (2026-10-01); Victor then asked for it out — *"înlocuiește-l cu un
/// hârâit ca de transmisie (white noise scurt), debifat by default în meniu"* —
/// and it plays only while the `Radio Squelch` row is ticked. Synthesised white
/// noise until 2026-10-05, when he picked a real one: *"de la 0:24 taie efectul
/// de stație pornită"* from youtu.be/nt71N59hydQ — `assets/start-squelch.wav`,
/// 25.03–25.34 s of it, mono 44.1 kHz, turned down 6 dB (−17.4 dB, the old hiss.s
/// RMS, was inaudible: *"nu aud nimic"* — it is mostly a click), 3 ms in / 40 ms out.
enum StartChime {

    /// `UserDefaults` beside `autosend`: a preference, not data. Absent = off.
    static let defaultsKey = "startSquelch"

    static var isOn: Bool {
        get { UserDefaults.standard.bool(forKey: defaultsKey) }
        set { UserDefaults.standard.set(newValue, forKey: defaultsKey) }
    }

    /// The menu row's title.
    static let menuTitle = "Radio Squelch"

    private static let sound: NSSound? = url().flatMap { NSSound(contentsOf: $0, byReference: false) }

    static func play() {
        guard isOn, let sound else { return }
        if sound.isPlaying { sound.stop() }
        sound.play()
    }

    /// `Resources/start-squelch.wav` installed, `assets/start-squelch.wav` from a
    /// `.build` binary; nil (silence) when neither is there.
    private static func url() -> URL? {
        var candidates: [URL] = []
        if let res = Bundle.main.resourcePath { candidates.append(URL(fileURLWithPath: res).appendingPathComponent("start-squelch.wav")) }
        var dir = URL(fileURLWithPath: CommandLine.arguments[0], relativeTo: URL(fileURLWithPath: FileManager.default.currentDirectoryPath))
            .standardizedFileURL.resolvingSymlinksInPath().deletingLastPathComponent()
        for _ in 0..<4 { candidates.append(dir.appendingPathComponent("assets/start-squelch.wav")); dir = dir.deletingLastPathComponent() }
        return candidates.first { FileManager.default.fileExists(atPath: $0.path) }
    }
}
