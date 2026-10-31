import Cocoa
import PDFKit

enum LabelPrinting {
    static func printInfo(from settings: NSPrintInfo = .shared) -> NSPrintInfo {
        let info = settings.copy() as! NSPrintInfo
        info.scalingFactor = 1
        info.isHorizontallyCentered = false
        info.isVerticallyCentered = false
        let margin: CGFloat = 5 * 72 / 25.4
        info.leftMargin = margin; info.rightMargin = margin
        info.topMargin = margin; info.bottomMargin = margin
        return info
    }

    static func operation(document: PDFDocument, printInfo: NSPrintInfo) -> NSPrintOperation? {
        // PDF points map directly to physical printer points. In particular,
        // do not lay out a small HTML label inside a separate WKWebView or fit
        // the label to an A4 sheet; that can crop it or change the QR size.
        guard let page = document.page(at: 0) else { return nil }
        let operation = NSPrintOperation(view: LabelPrintView(page: page, printInfo: printInfo), printInfo: printInfo)
        operation.printPanel.options.formUnion([.showsPaperSize, .showsOrientation, .showsScaling])
        return operation
    }
}

private final class LabelPrintView: NSView {
    private let page: PDFPage
    private let margins: NSEdgeInsets

    init(page: PDFPage, printInfo: NSPrintInfo) {
        self.page = page
        margins = NSEdgeInsets(top: printInfo.topMargin, left: printInfo.leftMargin,
                               bottom: printInfo.bottomMargin, right: printInfo.rightMargin)
        super.init(frame: NSRect(origin: .zero, size: page.bounds(for: .mediaBox).size))
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

    override func knowsPageRange(_ range: NSRangePointer) -> Bool {
        // Re-evaluate after paper changes in the print panel. Matching label
        // stock has no spare sheet margin; the PDF already has its quiet zone.
        if let info = NSPrintOperation.current?.printInfo {
            let spareX = max(0, info.paperSize.width - bounds.width) / 2
            let spareY = max(0, info.paperSize.height - bounds.height) / 2
            info.leftMargin = min(margins.left, spareX)
            info.rightMargin = min(margins.right, spareX)
            info.topMargin = min(margins.top, spareY)
            info.bottomMargin = min(margins.bottom, spareY)
        }
        range.pointee = NSRange(location: 1, length: 1)
        return true
    }

    override func rectForPage(_ page: Int) -> NSRect { bounds }

    override func draw(_ dirtyRect: NSRect) {
        guard let context = NSGraphicsContext.current?.cgContext else { return }
        page.draw(with: .mediaBox, to: context)
    }
}
