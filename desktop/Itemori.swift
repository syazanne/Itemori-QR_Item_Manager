import Cocoa
import WebKit
import UniformTypeIdentifiers
import PDFKit

// The native shell owns its backend. No separate browser or Python installation is used.
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate, WKScriptMessageHandler {
    let appName = "Itemori"
    // Preserve existing records across the display-name change.
    let storageDirectoryName = "QR Item Manager"
    let process = Process()
    var window: NSWindow!
    var webView: WKWebView!
    var timer: Timer?
    var endpoint: URL?
    var runtimeDirectory: URL!
    var started = Date()
    var quitting = false
    var quitAlert: NSAlert?
    var quitKeyMonitor: Any?
    var quitApproved = false
    var checkingQuitState = false
    var testStarted = false
    var downloadURLs: [ObjectIdentifier: URL] = [:]
    let env = ProcessInfo.processInfo.environment
    var testScript: String? { env["QR_ITEM_MANAGER_TEST_SCRIPT"] }

    func applicationDidFinishLaunching(_ notification: Notification) {
        makeMenu()
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        configurePrintBridge(config)
        configureQuitShortcut(config)
        webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1320, height: 880),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Itemori - Item Record and QR Label"
        window.delegate = self
        window.minSize = NSSize(width: 900, height: 650)
        window.contentView = webView
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        webView.loadHTMLString("<html><body style='font:20px -apple-system;background:#f5f8f9;color:#193c4a;padding:60px'><h2>Itemori</h2><p>Item Record and QR Label</p><p>Opening your workspace…</p></body></html>", baseURL: nil)
        // The desktop workspace deliberately loads only local resources, even when online.
        let rules = """
        [{"trigger":{"url-filter":"^https?://","unless-domain":["127.0.0.1"]},"action":{"type":"block"}}]
        """
        WKContentRuleListStore.default().compileContentRuleList(forIdentifier: "OfflineWorkspace", encodedContentRuleList: rules) { list, error in
            guard let list = list else { self.fail("Could not initialize the offline workspace: \(error?.localizedDescription ?? "unknown error")"); return }
            config.userContentController.add(list)
            self.startBackend()
        }
    }

    var printingDocument: PDFDocument?

    func configureQuitShortcut(_ config: WKWebViewConfiguration) {
        if quitKeyMonitor == nil {
            quitKeyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
                guard let self = self, event.keyCode == 53, let alert = self.quitAlert,
                      self.window.attachedSheet === alert.window else { return event }
                if !event.isARepeat {
                    self.window.endSheet(alert.window, returnCode: .alertSecondButtonReturn)
                }
                return nil
            }
        }
        config.userContentController.add(self, name: "requestQuit")
        let script = """
        document.addEventListener('keydown', event => {
            if (event.key !== 'Escape' || event.repeat || event.isComposing) return;
            // Capture overlay state before Escape dismisses it. A widget gets
            // the first Escape; a later Escape can request application quit.
            let overlay = true;
            try {
                const docs = window === window.top ? [document] : [document, window.top.document];
                overlay = docs.some(doc => [...doc.querySelectorAll(
                    '[role="dialog"], [aria-modal="true"], [role="listbox"], [role="menu"], [data-testid="stPopoverBody"]'
                )].some(node => node.getClientRects().length > 0));
            } catch (_) {}
            setTimeout(() => {
                if (!overlay && !event.defaultPrevented) {
                    window.webkit.messageHandlers.requestQuit.postMessage('escape');
                }
            }, 0);
        }, true);
        """
        config.userContentController.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentStart, forMainFrameOnly: false))
    }

    func configurePrintBridge(_ config: WKWebViewConfiguration) {
        config.userContentController.add(self, name: "printLabel")
        let script = """
        window.print = () => {
            const pdf = document.querySelector('meta[name="itemori-label-pdf"]')?.content;
            if (pdf) window.webkit.messageHandlers.printLabel.postMessage(pdf);
        };
        """
        config.userContentController.addUserScript(WKUserScript(source: script, injectionTime: .atDocumentStart, forMainFrameOnly: false))
    }

    func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
        if message.name == "requestQuit" {
            guard message.body as? String == "escape",
                  message.frameInfo.securityOrigin.host == "127.0.0.1",
                  message.frameInfo.securityOrigin.port == endpoint?.port,
                  window.attachedSheet == nil, printingDocument == nil else { return }
            NSApp.terminate(nil)
            return
        }
        guard message.name == "printLabel", let encoded = message.body as? String,
              message.frameInfo.securityOrigin.host == "127.0.0.1",
              message.frameInfo.securityOrigin.port == endpoint?.port,
              printingDocument == nil, window.attachedSheet == nil else { return }
        guard let data = Data(base64Encoded: encoded), let document = PDFDocument(data: data),
              document.pageCount == 1,
              let operation = LabelPrinting.operation(document: document, printInfo: LabelPrinting.printInfo()) else {
            let alert = NSAlert()
            alert.messageText = "The label could not be prepared for printing"
            alert.informativeText = "Close this dialog and open Print QR label again. You can also download the label PDF."
            alert.beginSheetModal(for: window)
            return
        }
        printingDocument = document
        operation.jobTitle = "Itemori QR label"
        if testScript != nil, let path = env["QR_ITEM_MANAGER_TEST_PRINT"] {
            operation.printInfo.jobDisposition = .save
            operation.printInfo.dictionary()[NSPrintInfo.AttributeKey.jobSavingURL] = URL(fileURLWithPath: path)
            operation.showsPrintPanel = false
            operation.showsProgressPanel = false
            let success = operation.run()
            printingDocument = nil
            webView.evaluateJavaScript("window.desktopPrintCompleted = \(success ? "true" : "false");")
            return
        }
        operation.showsPrintPanel = true
        operation.runModal(for: window, delegate: self,
                           didRun: #selector(printFinished(_:success:context:)), contextInfo: nil)
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        NSApp.terminate(nil)
        return false // Keep the workspace intact while the confirmation is open.
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if quitApproved { return .terminateNow }
        if quitAlert != nil || checkingQuitState { return .terminateCancel }
        // A file picker or export sheet must finish or be cancelled first.
        guard let window = window, window.attachedSheet == nil else { return .terminateCancel }
        checkingQuitState = true
        self.checkingQuitState = false
        self.showQuitConfirmation(unsaved: true)
        return .terminateCancel
    }

    func showQuitConfirmation(unsaved: Bool) {
        let alert = NSAlert()
        alert.alertStyle = unsaved ? .warning : .informational
        alert.messageText = "Quit app?"
        alert.informativeText = unsaved ? "Any changes you have not saved will be lost." : ""
        // Use native Quit/Cancel ordering but make Cancel the default.
        // The local key monitor explicitly handles Escape on this sheet.
        let quit = alert.addButton(withTitle: "Quit")
        quit.keyEquivalent = ""
        let cancel = alert.addButton(withTitle: "Cancel")
        cancel.keyEquivalent = "\u{1b}"
        alert.window.defaultButtonCell = cancel.cell as? NSButtonCell
        quitAlert = alert
        alert.beginSheetModal(for: window) { response in
            self.quitAlert = nil
            self.quitApproved = response == .alertFirstButtonReturn
            if self.quitApproved { NSApp.terminate(nil) }
        }
    }

    func makeMenu() {
        let menu = NSMenu()
        let appItem = NSMenuItem(); menu.addItem(appItem)
        let appMenu = NSMenu(); appItem.submenu = appMenu
        appMenu.addItem(withTitle: "About \(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        let profiles = appMenu.addItem(withTitle: "Show data folder", action: #selector(showStorage), keyEquivalent: ""); profiles.target = self
        let licenses = appMenu.addItem(withTitle: "Third-party licenses", action: #selector(showLicenses), keyEquivalent: ""); licenses.target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let editItem = NSMenuItem(); menu.addItem(editItem)
        let edit = NSMenu(title: "Edit"); editItem.submenu = edit
        edit.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        NSApp.mainMenu = menu
    }

    func storageURL() -> URL {
        if let override = env["QR_ITEM_MANAGER_DATA_DIR"] { return URL(fileURLWithPath: override, isDirectory: true) }
        return FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent(storageDirectoryName)
    }
    @objc func showStorage() { NSWorkspace.shared.open(storageURL()) }
    @objc func showLicenses() {
        if let resource = Bundle.main.resourceURL { NSWorkspace.shared.open(resource.appendingPathComponent("Licenses")) }
    }

    func startBackend() {
        do {
            let resources = Bundle.main.resourceURL!
            runtimeDirectory = FileManager.default.temporaryDirectory.appendingPathComponent("qr-item-manager-\(UUID().uuidString)")
            try FileManager.default.createDirectory(at: runtimeDirectory, withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: storageURL(), withIntermediateDirectories: true)
            let log = storageURL().appendingPathComponent("desktop.log")
            FileManager.default.createFile(atPath: log.path, contents: nil)
            let output = try FileHandle(forWritingTo: log)
            process.executableURL = resources.appendingPathComponent("backend/qr-item-manager-backend")
            process.arguments = ["--ready-file", runtimeDirectory.appendingPathComponent("ready.json").path, "--parent-pid", String(ProcessInfo.processInfo.processIdentifier)]
            process.standardOutput = output; process.standardError = output
            var environment = env
            environment["QR_ITEM_MANAGER_DATA_DIR"] = storageURL().path
            environment.removeValue(forKey: "PYTHONHOME"); environment.removeValue(forKey: "PYTHONPATH")
            process.environment = environment
            process.terminationHandler = { _ in
                DispatchQueue.main.async { if !self.quitting { self.fail("The workspace engine stopped. See desktop.log in your data folder.") } }
            }
            try process.run()
            started = Date()
            timer = Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { _ in self.checkBackend() }
        } catch { fail("Could not open the workspace: \(error.localizedDescription)") }
    }

    func checkBackend() {
        if Date().timeIntervalSince(started) > 90 { fail("The workspace took too long to start. See desktop.log in your data folder."); return }
        guard endpoint == nil, let data = try? Data(contentsOf: runtimeDirectory.appendingPathComponent("ready.json")),
              let info = try? JSONSerialization.jsonObject(with: data) as? [String: Int], let port = info["port"] else { return }
        let url = URL(string: "http://127.0.0.1:\(port)")!
        var request = URLRequest(url: url.appendingPathComponent("_stcore/health")); request.timeoutInterval = 1
        URLSession.shared.dataTask(with: request) { _, response, _ in
            guard (response as? HTTPURLResponse)?.statusCode == 200 else { return }
            DispatchQueue.main.async {
                guard self.endpoint == nil, !self.quitting else { return }
                self.endpoint = url; self.timer?.invalidate()
                var initial = URLComponents(url: url, resolvingAgainstBaseURL: false)!
                if self.testScript != nil, let query = self.env["QR_ITEM_MANAGER_TEST_QUERY"] { initial.percentEncodedQuery = query }
                self.webView.load(URLRequest(url: initial.url!))
            }
        }.resume()
    }

    func isLocal(_ url: URL?) -> Bool {
        guard let url = url, let endpoint = endpoint else { return false }
        return url.scheme == "http" && url.host == "127.0.0.1" && url.port == endpoint.port
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let url = action.request.url
        if isLocal(url) || url?.scheme == "blob" || url?.scheme == "about" {
            decisionHandler(action.shouldPerformDownload ? .download : .allow)
        } else {
            if action.navigationType == .linkActivated, let url = url, ["https", "http"].contains(url.scheme ?? "") { NSWorkspace.shared.open(url) }
            decisionHandler(.cancel)
        }
    }
    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        decisionHandler(response.canShowMIMEType ? .allow : .download)
    }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }

    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        if testScript != nil, let file = env["QR_ITEM_MANAGER_TEST_UPLOAD"] { completionHandler([URL(fileURLWithPath: file)]); return }
        let panel = NSOpenPanel(); panel.canChooseDirectories = false; panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.beginSheetModal(for: window) { result in completionHandler(result == .OK ? panel.urls : nil) }
    }
    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin, initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType, decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(origin.host == "127.0.0.1" && origin.port == endpoint?.port && type == .camera ? .prompt : .deny)
    }

    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        if testScript != nil, let directory = env["QR_ITEM_MANAGER_TEST_DOWNLOADS"] {
            let url = URL(fileURLWithPath: directory).appendingPathComponent(suggestedFilename)
            downloadURLs[ObjectIdentifier(download)] = url; completionHandler(url); return
        }
        let panel = NSSavePanel(); panel.nameFieldStringValue = suggestedFilename; panel.canCreateDirectories = true
        panel.beginSheetModal(for: window) { result in
            let url = result == .OK ? panel.url : nil
            if let url = url { self.downloadURLs[ObjectIdentifier(download)] = url }
            completionHandler(url)
        }
    }
    func downloadDidFinish(_ download: WKDownload) {
        if let url = downloadURLs.removeValue(forKey: ObjectIdentifier(download)) {
            if testScript != nil {
                let encoded = String(data: try! JSONSerialization.data(withJSONObject: [url.lastPathComponent]), encoding: .utf8)!
                webView.evaluateJavaScript("window.desktopDownloads = (window.desktopDownloads || []).concat(\(encoded));")
            }
        }
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        downloadURLs.removeValue(forKey: ObjectIdentifier(download))
        if (error as NSError).code != NSURLErrorCancelled {
            let alert = NSAlert(); alert.messageText = "Export could not be saved"; alert.informativeText = error.localizedDescription
            alert.beginSheetModal(for: window)
        }
    }

    // Explicit developer harness exercises the packaged WKWebView using temporary data.
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard isLocal(webView.url), !testStarted, let scriptPath = testScript else { return }
        testStarted = true
        guard let script = try? String(contentsOfFile: scriptPath) else { finishTest("ERROR: missing test script"); return }
        webView.callAsyncJavaScript(script, arguments: [:], in: nil, in: .page) { result in
            switch result {
            case .success(let value): self.finishTest(String(describing: value))
            case .failure(let error): self.finishTest("ERROR: \(error)")
            }
        }
    }
    @objc func printFinished(_ operation: NSPrintOperation, success: Bool, context: UnsafeMutableRawPointer?) {
        printingDocument = nil
    }

    func finishTest(_ message: String) {
        if let path = env["QR_ITEM_MANAGER_TEST_RESULT"] { try? message.write(toFile: path, atomically: true, encoding: .utf8) }
        let config = WKSnapshotConfiguration()
        webView.takeSnapshot(with: config) { image, _ in
            if let image = image, let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff),
               let png = bitmap.representation(using: .png, properties: [:]), let path = self.env["QR_ITEM_MANAGER_TEST_RESULT"] {
                try? png.write(to: URL(fileURLWithPath: path + ".png"))
            }
            self.quitApproved = true
            NSApp.terminate(nil)
        }
    }
    func fail(_ message: String) {
        timer?.invalidate()
        if testScript != nil { finishTest("ERROR: " + message); return }
        let alert = NSAlert(); alert.messageText = "Unable to open workspace"; alert.informativeText = message
        alert.runModal(); quitApproved = true; NSApp.terminate(nil)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationWillTerminate(_ notification: Notification) {
        quitting = true; timer?.invalidate(); webView?.stopLoading()
        if let monitor = quitKeyMonitor { NSEvent.removeMonitor(monitor) }
        if process.isRunning {
            process.terminate()
            let deadline = Date().addingTimeInterval(3)
            while process.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.05) }
            if process.isRunning { kill(process.processIdentifier, SIGKILL) }
        }
        if let directory = runtimeDirectory { try? FileManager.default.removeItem(at: directory) }
    }
}

#if !QUIT_TESTING
@main struct ItemoriMain {
    static func main() {
        let application = NSApplication.shared
        application.setActivationPolicy(.regular)
        let delegate = AppDelegate()
        application.delegate = delegate
        application.run()
        withExtendedLifetime(delegate) {}
    }
}
#endif
