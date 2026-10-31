import Cocoa
import PDFKit
import Vision

// Save through the same native print operation as the app, then inspect what
// the printer would receive. No physical printer or print panel is used.
@main struct LabelPrintingTests {
    static func require(_ condition: Bool, _ message: String) throws {
        if !condition { throw NSError(domain: "LabelPrintingTests", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
    }

    static func main() throws {
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)
        let folder = URL(fileURLWithPath: CommandLine.arguments[1])
        let cases = try JSONSerialization.jsonObject(with: Data(contentsOf: folder.appendingPathComponent("cases.json"))) as! [[String: Any]]
        var evidence: [[String: Any]] = []
        for fixture in cases {
            let name = fixture["name"] as! String
            let record = fixture["record"] as! String
            let width = fixture["paperWidth"] as! Double
            let height = fixture["paperHeight"] as! Double
            let document = PDFDocument(url: folder.appendingPathComponent(name + "-source.pdf"))!
            let info = LabelPrinting.printInfo(from: NSPrintInfo(dictionary: [:]))
            info.paperSize = NSSize(width: width, height: height)
            info.orientation = .portrait
            // The custom label sheet has no spare margins. A4/Letter simulate
            // symmetric hardware margins, while retaining the label's size.
            let margin = fixture["margin"] as! Double
            info.leftMargin = margin; info.rightMargin = margin
            info.topMargin = margin; info.bottomMargin = margin
            let output = folder.appendingPathComponent(name + "-printed.pdf")
            info.jobDisposition = .save
            info.dictionary()[NSPrintInfo.AttributeKey.jobSavingURL] = output
            let changePaper = fixture["changePaper"] as? Bool == true
            if changePaper {
                info.paperSize = NSSize(width: 612, height: 792)
                info.leftMargin = 18; info.rightMargin = 18
                info.topMargin = 18; info.bottomMargin = 18
            }
            let operation = LabelPrinting.operation(document: document, printInfo: info)!
            if changePaper {
                operation.printInfo.paperSize = NSSize(width: width, height: height)
            }
            operation.showsPrintPanel = false
            operation.showsProgressPanel = false
            try require(operation.run(), name + ": native print failed")
            let printed = PDFDocument(url: output)!
            try require(printed.pageCount == 1, name + ": label split across pages")
            let page = printed.page(at: 0)!
            let bounds = page.bounds(for: .mediaBox)
            try require(abs(bounds.width - width) < 0.1 && abs(bounds.height - height) < 0.1,
                        name + ": wrong paper dimensions \(bounds.size)")
            try require(page.string?.contains(record) == true, name + ": record ID missing")
            let thumbnail = page.thumbnail(of: NSSize(width: width * 3, height: height * 3), for: .mediaBox)
            let bitmap = NSBitmapImageRep(data: thumbnail.tiffRepresentation!)!
            let image = bitmap.cgImage!
            try bitmap.representation(using: .png, properties: [:])!.write(to: folder.appendingPathComponent(name + "-printed.png"))
            let request = VNDetectBarcodesRequest()
            request.symbologies = [.qr]
            try VNImageRequestHandler(cgImage: image).perform([request])
            guard let qr = request.results?.first(where: { $0.payloadStringValue == record }) else {
                throw NSError(domain: "LabelPrintingTests", code: 2, userInfo: [NSLocalizedDescriptionKey: name + ": printed QR cannot be decoded (cropped or damaged)"])
            }
            let qrWidth = qr.boundingBox.width * width
            let qrHeight = qr.boundingBox.height * height
            // Vision's estimated corners are approximate. Exact dimensions and
            // placement are checked from the printed vector paths in Python.
            evidence.append(["name": name, "record": record, "paperWidth": bounds.width,
                             "paperHeight": bounds.height, "qrWidth": qrWidth, "qrHeight": qrHeight,
                             "decoded": qr.payloadStringValue!])
            print("PASS \(name): one page, readable printed QR and record ID")
        }
        try JSONSerialization.data(withJSONObject: evidence, options: [.prettyPrinted, .sortedKeys])
            .write(to: folder.appendingPathComponent("results.json"))
    }
}
