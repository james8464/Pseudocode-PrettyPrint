// Draw the Pseudocode PrettyPrint application icon.
//
// Run from the repository root:
//   swift packaging/make_icon.swift packaging/icons/app-1024.png
//
// The macOS .icns and Windows .ico files are generated from the PNG by the
// commands in packaging/build_icons.sh.

import AppKit
import CoreGraphics
import Foundation

let output = CommandLine.arguments.count > 1
    ? CommandLine.arguments[1]
    : "packaging/icons/app-1024.png"

let size = 1024
guard let representation = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: size,
    pixelsHigh: size,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
) else {
    fatalError("Could not create the icon bitmap")
}
representation.size = NSSize(width: size, height: size)

NSGraphicsContext.saveGraphicsState()
guard let context = NSGraphicsContext(bitmapImageRep: representation) else {
    fatalError("Could not create the icon graphics context")
}
NSGraphicsContext.current = context

let canvas = CGFloat(size)
let inset: CGFloat = 72
let body = CGRect(
    x: inset,
    y: inset,
    width: canvas - inset * 2,
    height: canvas - inset * 2
)
let rounded = CGPath(
    roundedRect: body,
    cornerWidth: 190,
    cornerHeight: 190,
    transform: nil
)

context.cgContext.saveGState()
context.cgContext.addPath(rounded)
context.cgContext.clip()
let gradient = CGGradient(
    colorsSpace: CGColorSpaceCreateDeviceRGB(),
    colors: [
        NSColor(calibratedRed: 0.45, green: 0.30, blue: 0.95, alpha: 1).cgColor,
        NSColor(calibratedRed: 0.04, green: 0.51, blue: 1.00, alpha: 1).cgColor,
    ] as CFArray,
    locations: [0.0, 1.0]
)!
context.cgContext.drawLinearGradient(
    gradient,
    start: CGPoint(x: inset, y: canvas - inset),
    end: CGPoint(x: canvas - inset, y: inset),
    options: []
)
context.cgContext.restoreGState()

let font = NSFont.monospacedSystemFont(ofSize: 400, weight: .bold)
let paragraph = NSMutableParagraphStyle()
paragraph.alignment = .center
let shadow = NSShadow()
shadow.shadowColor = NSColor.black.withAlphaComponent(0.28)
shadow.shadowBlurRadius = 34
shadow.shadowOffset = NSSize(width: 0, height: -12)
let attributes: [NSAttributedString.Key: Any] = [
    .font: font,
    .foregroundColor: NSColor.white,
    .shadow: shadow,
    .paragraphStyle: paragraph,
]
let text = "{}" as NSString
let textSize = text.size(withAttributes: attributes)
let textRect = NSRect(
    x: 0,
    y: (canvas - textSize.height) / 2 + 18,
    width: canvas,
    height: textSize.height
)
text.draw(in: textRect, withAttributes: attributes)

NSGraphicsContext.restoreGraphicsState()

guard let png = representation.representation(using: .png, properties: [:]) else {
    fatalError("Could not encode the icon as PNG")
}
try png.write(to: URL(fileURLWithPath: output))
print("Wrote \(output)")
