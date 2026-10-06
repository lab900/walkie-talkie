// swift-tools-version: 5.9
import PackageDescription

// Stand-in for Victor Rentea's private `victor-mac-kit`. It only provides the
// API walkie-talkie compiles against. The area selection does nothing: every
// selection ends at once as cancelled.
let package = Package(
    name: "victor-mac-kit",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "VictorMacKit", targets: ["VictorMacKit"]),
    ],
    targets: [
        .target(name: "VictorMacKit"),
    ]
)
