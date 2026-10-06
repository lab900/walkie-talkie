import AppKit

public struct CropSelectionStyle {
    public let hint: String
    public let movingSuffix: String
    public let centeredSuffix: String
    public let allowsMove: Bool
    public let moveToSuffix: String

    public init(hint: String, movingSuffix: String, centeredSuffix: String,
                allowsMove: Bool = false, moveToSuffix: String = "") {
        self.hint = hint
        self.movingSuffix = movingSuffix
        self.centeredSuffix = centeredSuffix
        self.allowsMove = allowsMove
        self.moveToSuffix = moveToSuffix
    }
}

/// No-op overlay: `begin` reports a cancelled selection straight away.
public enum CropSelectionOverlay {
    public enum Button { case left, middle }

    public struct Selection {
        public let rect: NSRect
        public let screen: NSScreen
        public let movedTo: NSRect?
    }

    public static var log: ((String) -> Void)?
    public static var onAwaitingDestination: ((Bool) -> Void)?

    public static func begin(button: Button, from anchor: NSPoint, style: CropSelectionStyle,
                             completion: @escaping (Selection?) -> Void) {
        log?("✂️ area selection unavailable (victor-mac-kit stub)")
        completion(nil)
    }

    public static func endDrag() {}
    public static func cancelIfParked() {}
    public static func destinationPressed(atCG point: CGPoint) {}
    public static func dragMoved(toCG point: CGPoint) {}
}
