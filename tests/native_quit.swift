import Cocoa
import WebKit

// Compile with Itemori.swift and LabelPrinting.swift and -D QUIT_TESTING. Uses a disposable local
// page and the real native window, Escape bridge, close button and quit sheet.
@main struct QuitTestMain {
    static func main() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        let delegate = AppDelegate()
        let lifecycle = QuitLifecycle(delegate)
        app.delegate = lifecycle
        let test = QuitTest(delegate)
        test.start()
        app.run()
        withExtendedLifetime((test, lifecycle)) {}
    }
}

final class QuitLifecycle: NSObject, NSApplicationDelegate {
    let delegate: AppDelegate
    init(_ delegate: AppDelegate) { self.delegate = delegate }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        print("Quit delegate invoked"); fflush(stdout)
        let reply = delegate.applicationShouldTerminate(sender)
        print("Quit reply", reply.rawValue); fflush(stdout)
        return reply
    }
    func applicationWillTerminate(_ notification: Notification) {
        delegate.applicationWillTerminate(notification)
    }
}

final class QuitTest {
    let delegate: AppDelegate
    let result = ProcessInfo.processInfo.environment["QUIT_TEST_RESULT"]!
    var stage = 0
    var deadline = Date().addingTimeInterval(30)
    var nextCheck = Date()
    var busy = false
    var confirmed = false
    var timer: Timer?
    var observer: NSObjectProtocol?
    init(_ delegate: AppDelegate) { self.delegate = delegate }
    func record(_ message: String) { try? message.write(toFile: result, atomically: true, encoding: .utf8) }
    func require(_ okay: Bool, _ message: String) {
        if !okay { record("FAIL: " + message); exit(1) }
    }
    func advance() { print("Completed stage", stage); fflush(stdout); stage += 1; deadline = Date().addingTimeInterval(10); nextCheck = Date().addingTimeInterval(0.3) }
    func js(_ script: String, completion: @escaping (Any?) -> Void) {
        busy = true
        delegate.webView.evaluateJavaScript(script) { value, error in
            self.busy = false
            self.require(error == nil, "JavaScript: \(String(describing: error))")
            completion(value)
        }
    }
    func escape(_ window: NSWindow) {
        window.makeKeyAndOrderFront(nil)
        let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [],
                                    timestamp: ProcessInfo.processInfo.systemUptime,
                                    windowNumber: window.windowNumber, context: nil,
                                    characters: "\u{1b}", charactersIgnoringModifiers: "\u{1b}",
                                    isARepeat: false, keyCode: 53)!
        NSApp.sendEvent(event)
    }
    func start() {
        delegate.makeMenu()
        delegate.endpoint = URL(string: ProcessInfo.processInfo.environment["QUIT_TEST_URL"]!)!
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .nonPersistent()
        delegate.configureQuitShortcut(config)
        delegate.webView = WKWebView(frame: .zero, configuration: config)
        delegate.webView.navigationDelegate = delegate
        delegate.window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 950, height: 700),
                                   styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
        delegate.window.title = "Itemori quit test — disposable session"
        delegate.window.delegate = delegate
        delegate.window.contentView = delegate.webView
        delegate.window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        delegate.webView.load(URLRequest(url: delegate.endpoint!))
        observer = NotificationCenter.default.addObserver(forName: NSApplication.willTerminateNotification, object: nil, queue: .main) { _ in
            self.record(self.confirmed ? "PASS native and iframe Escape, overlay priority, Cancel preserves edits, sheet Escape cancels, confirmed Quit terminates" : "FAIL: terminated without confirmation at stage \(self.stage)")
        }
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in self.step() }
    }
    func step() {
        guard !busy, Date() >= nextCheck else { return }
        require(Date() < deadline, "Timeout at stage \(stage)")
        switch stage {
        case 0:
            js("document.readyState==='complete' && !!document.getElementById('draft')") { ready in
                guard ready as? Bool == true else { return }
                self.js("""
                    document.getElementById('draft').value='unsaved edit';
                    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',repeat:true,bubbles:true,cancelable:true}));
                    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',isComposing:true,bubbles:true,cancelable:true}));
                    document.addEventListener('keydown', e => e.preventDefault(), {once:true});
                    document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
                    for (const role of ['dialog','listbox','menu']) {
                        const overlay=document.createElement('div');
                        overlay.setAttribute('role',role); overlay.textContent='preview'; document.body.append(overlay);
                        document.addEventListener('keydown',()=>overlay.remove(),{once:true});
                        document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
                    }
                    """) { _ in self.advance() }
            }
        case 1:
            require(delegate.quitAlert == nil, "Escape on an image dialog requested app quit")
            js("document.querySelector('iframe').contentDocument.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));") { _ in self.advance() }
        case 2:
            guard let alert = delegate.quitAlert else { return }
            require(alert.informativeText == "Any changes you have not saved will be lost.", "Missing quit warning")
            require(alert.buttons.map { $0.title } == ["Quit", "Cancel"], "Wrong confirmation buttons")
            require(alert.window.defaultButtonCell === alert.buttons[1].cell, "Cancel is not the default")
            alert.buttons[1].performClick(nil)
            advance()
        case 3:
            guard delegate.quitAlert == nil else { return }
            require(delegate.window.isVisible && !delegate.quitApproved, "Cancel closed the window")
            js("document.getElementById('draft').value") { value in
                self.require(value as? String == "unsaved edit", "Cancel lost the current edit")
                self.delegate.window.performClose(nil)
                self.advance()
            }
        case 4:
            guard let alert = delegate.quitAlert else { return }
            require(alert.informativeText == "Any changes you have not saved will be lost.", "Unsaved session did not warn")
            // A second Escape cancels the quit sheet instead of approving it.
            escape(alert.window)
            advance()
        case 5:
            guard delegate.quitAlert == nil else { return }
            require(delegate.window.isVisible && !delegate.quitApproved, "Sheet Escape did not cancel")
            NSApp.sendAction(#selector(NSApplication.terminate(_:)), to: NSApp, from: nil)
            self.advance()
        case 6:
            guard let alert = delegate.quitAlert else { return }
            require(alert.informativeText == "Any changes you have not saved will be lost.", "Missing quit warning")
            alert.buttons[1].performClick(nil)
            advance()
        case 7:
            guard delegate.quitAlert == nil else { return }
            delegate.window.makeFirstResponder(delegate.webView)
            js("document.getElementById('draft').focus()") { _ in
                self.escape(self.delegate.window)
                self.advance()
            }
        case 8:
            guard let alert = delegate.quitAlert else { return }
            require(alert.informativeText == "Any changes you have not saved will be lost.", "New edit did not restore warning")
            confirmed = true
            alert.buttons[0].performClick(nil)
            advance()
        default: break
        }
    }
}
