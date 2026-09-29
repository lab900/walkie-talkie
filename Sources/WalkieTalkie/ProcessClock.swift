import Darwin
import Foundation

/// **Another process, read from the kernel's process table** (batch 4,
/// 2026-09-29) — `sysctl(KERN_PROC_PID)`, no AppKit, any thread. For Wispr
/// Flow's main process: whether it is still alive when its microphone closes
/// under a relay sentence (a quit is not his stop, item 3).
enum ProcessClock {
    private static func info(_ pid: pid_t) -> kinfo_proc? {
        guard pid > 0 else { return nil }
        var info = kinfo_proc()
        var size = MemoryLayout<kinfo_proc>.stride
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid]
        guard sysctl(&mib, u_int(mib.count), &info, &size, nil, 0) == 0, size > 0,
              info.kp_proc.p_pid == pid else { return nil }
        return info
    }

    /// Alive = in the process table and not a zombie (a SIGKILLed process
    /// stays in the table as `SZOMB` until its parent reaps it).
    static func isAlive(_ pid: pid_t) -> Bool {
        guard let i = info(pid) else { return false }
        return Int32(i.kp_proc.p_stat) != SZOMB
    }
}
