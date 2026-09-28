import Foundation

/// **Wake on Wispr's commits, not on a timer** (batch 3, 2026-09-28 —
/// `evals/plan/wispr/integration-surfaces.md`, candidate #2).
///
/// The row readers (`WisprFlowSource.pollHistory`, the retired-discard and the
/// discard-close watches) ran on a 150 ms `Timer` each: a row was seen 75 ms
/// late on average, and the timer ran whether or not Wispr had written
/// anything. Wispr's `flow.sqlite` is in WAL mode, so **every commit writes
/// `flow.sqlite-wal`**: a kqueue vnode source on that file (`.write`,
/// `.extend`) says *someone committed* within a millisecond, and
/// `PRAGMA data_version` (`WisprHistory`'s cache) says whether the query needs
/// to run at all. The main file is watched too: a checkpoint writes it, and
/// the desk's fake (`WT_WISPR_DB`, rollback journal) commits there.
///
/// - **Re-armed on `.delete` / `.rename`** — the WAL is removed when the last
///   connection closes (Wispr quits) and recreated on the next open — and on
///   every safety tick, when the path (a `WT_WISPR_DB` switch) or the inode
///   moved, or a file that was missing appeared.
/// - **Second looks 5, 15 and 40 ms after every event**: the WAL frames are
///   written before the wal-index in `-shm` is updated, so a read that lands in
///   between sees the old snapshot and no further write follows.
/// - **A 1 s safety tick**, for a missed event and for the readers' clocks
///   (their deadlines also ask `wake(after:)` for a pass at the instant).
///
/// Subscribers run on main; with none the sources are cancelled and the tick
/// stops, so an idle relay watches nothing.
final class WisprHistoryWatch {

    static let safetyTick: TimeInterval = 1.0
    /// **Looks after each event**: the WAL frames are written before the
    /// wal-index in `-shm` says so, and a pass in between sees the old snapshot.
    /// One look at 40 ms left the desk at 62–69 ms twice in six commits (TW38,
    /// 2026-09-29); 5 / 15 / 40 ms catches the index as soon as it lands, and a
    /// look that finds nothing new costs one `PRAGMA data_version`.
    static let secondLooks: [TimeInterval] = [0.005, 0.015, 0.04]

    private var subscribers: [String: () -> Void] = [:]
    private var sources: [String: (source: DispatchSourceFileSystemObject, inode: UInt64)] = [:]
    private var tick: Timer?
    private var passQueued = false
    /// `GET /test/state.wisprLive.historyWake` — what woke the readers.
    private(set) var events = 0
    private(set) var ticks = 0
    private(set) var passes = 0

    /// Main thread. The same key replaces its closure.
    func subscribe(_ key: String, _ fn: @escaping () -> Void) {
        subscribers[key] = fn
        if tick == nil {
            arm()
            let t = Timer(timeInterval: Self.safetyTick, repeats: true) { [weak self] _ in
                guard let self else { return }
                self.ticks += 1
                self.arm()
                self.runPass()
            }
            tick = t
            RunLoop.main.add(t, forMode: .common)
        }
    }

    func unsubscribe(_ key: String) {
        subscribers.removeValue(forKey: key)
        guard subscribers.isEmpty else { return }
        tick?.invalidate()
        tick = nil
        for (_, s) in sources { s.source.cancel() }
        sources.removeAll()
    }

    var isWatching: Bool { !sources.isEmpty }
    var watchedPaths: [String] { sources.keys.sorted() }

    /// A pass at a reader's own deadline (a grace running out), not at a commit.
    func wake(after seconds: TimeInterval) {
        DispatchQueue.main.asyncAfter(deadline: .now() + seconds) { [weak self] in
            guard let self, !self.subscribers.isEmpty else { return }
            self.queuePass()
        }
    }

    private func paths() -> [String] {
        let db = WisprFlowDB.url.path
        return [db + "-wal", db]
    }

    private static func inode(_ path: String) -> UInt64? {
        ((try? FileManager.default.attributesOfItem(atPath: path))?[.systemFileNumber] as? NSNumber)?.uint64Value
    }

    /// Opens what is missing, drops what moved or is no longer wanted.
    private func arm() {
        let wanted = paths()
        for (path, s) in sources where !wanted.contains(path) || Self.inode(path) != s.inode {
            s.source.cancel()
            sources.removeValue(forKey: path)
        }
        for path in wanted where sources[path] == nil {
            guard let ino = Self.inode(path) else { continue }
            let fd = open(path, O_EVTONLY)
            guard fd >= 0 else { continue }
            let src = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd,
                                                                eventMask: [.write, .extend, .delete, .rename],
                                                                queue: .main)
            src.setEventHandler { [weak self, weak src] in
                guard let self, let src else { return }
                self.events += 1
                if !src.data.intersection([.delete, .rename]).isEmpty {
                    // The file is gone or renamed: this source watches nothing any more.
                    src.cancel()
                    if self.sources[path]?.source === src { self.sources.removeValue(forKey: path) }
                    DispatchQueue.main.async { [weak self] in
                        guard let self, !self.subscribers.isEmpty else { return }
                        self.arm()
                    }
                }
                self.queuePass()
                for look in Self.secondLooks { self.wake(after: look) }
            }
            src.setCancelHandler { close(fd) }
            src.resume()
            sources[path] = (src, ino)
        }
    }

    /// Several events in one run-loop turn are one pass, and passes are at
    /// least `minInterval` apart: a burst of commits (a Wispr busy writing
    /// other tables) is coalesced rather than run once per commit.
    private func queuePass() {
        guard !passQueued else { return }
        passQueued = true
        let wait = max(0, Self.minInterval - (CFAbsoluteTimeGetCurrent() - lastPassAt))
        DispatchQueue.main.asyncAfter(deadline: .now() + wait) { [weak self] in
            guard let self else { return }
            self.passQueued = false
            self.runPass()
        }
    }
    static let minInterval: TimeInterval = 0.004
    private var lastPassAt: CFAbsoluteTime = 0

    private func runPass() {
        guard !subscribers.isEmpty else { return }
        lastPassAt = CFAbsoluteTimeGetCurrent()
        passes += 1
        // A copy: a reader may unsubscribe (itself or another) during the pass.
        for (_, fn) in subscribers { fn() }
    }

    func describe() -> [String: Any] {
        ["watching": watchedPaths.map { ($0 as NSString).lastPathComponent },
         "subscribers": subscribers.keys.sorted(), "events": events, "ticks": ticks, "passes": passes,
         "queries": WisprHistory.queries, "cacheHits": WisprHistory.cacheHits]
    }
}
