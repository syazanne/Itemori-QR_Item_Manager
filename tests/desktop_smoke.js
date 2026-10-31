// Runs in the packaged WKWebView, with remote HTTP resources blocked by the app.
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitFor(fn, label, timeout = 30000) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
        const error = document.querySelector('[data-testid="stException"]');
        if (error) throw new Error(error.textContent);
        const result = fn();
        if (result) return result;
        await pause(100);
    }
    throw new Error('Timed out: ' + label + '\n' + document.body.innerText.slice(-2500));
}
const keyed = key => document.querySelector('.st-key-' + key.replace(/[^a-zA-Z0-9_-]/g, '-'));
async function click(key) {
    const button = await waitFor(() => keyed(key)?.querySelector('button:not(:disabled)'), key);
    button.click();
    await pause(450);
}
async function setInput(key, value) {
    const input = await waitFor(() => keyed(key)?.querySelector('input'), key);
    input.focus();
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value);
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.blur();
    await pause(450);
}
await waitFor(() => keyed('value_REC-0001_1'), 'record details');
await setInput('value_REC-0001_1', 'Offline desktop test');
await click('save_value_1');
await waitFor(() => document.body.innerText.includes('Saved ✓'), 'saved record');
await click('generate_qr');
await waitFor(() => keyed('print_qr_label'), 'QR generated');
const qrDownload = await waitFor(() => [...document.querySelectorAll('button')].find(b => b.innerText.includes('Download QR')), 'QR download');
qrDownload.click();
await waitFor(() => (window.desktopDownloads || []).some(name => name.endsWith('.png')), 'native PNG download');
await click('print_qr_label');
await waitFor(() => document.querySelector('[role="dialog"]'), 'label dialog');
const printFrame = await waitFor(() => [...document.querySelectorAll('iframe')].find(f =>
    f.contentDocument?.querySelector('meta[name="itemori-label-pdf"]')), 'native print payload');
printFrame.contentDocument.querySelector('button').click();
await waitFor(() => window.desktopPrintCompleted === true, 'native print operation');
await click('download_label');
await waitFor(() => (window.desktopDownloads || []).some(name => name.endsWith('.pdf')), 'native PDF download');
const dialog = document.querySelector('[role="dialog"]');
const close = dialog.querySelector('button[aria-label="Close"]') || dialog.querySelector('[data-testid="stDialogDismissButton"]');
if (!close) throw new Error('Missing label dialog close control');
close.click();
await pause(400);
await click('detail_back');
const table = await waitFor(() => document.querySelector('table.manage-records'), 'Manage after Back');
const handle = await waitFor(() => table.querySelector('[aria-label="Resize Item column"]'), 'bundled column resizing');
if (table.tBodies[0].rows[0].cells[0].textContent !== '1') throw new Error('Missing row number');
const cell = table.tBodies[0].rows[0].cells[2];
const oldWidth = cell.getBoundingClientRect().width;
handle.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowLeft', bubbles: true}));
if (Math.abs(cell.getBoundingClientRect().width - oldWidth + 10) > 1) throw new Error('Native column resize failed');
if (getComputedStyle(cell).whiteSpace === 'nowrap') throw new Error('Record text cannot wrap');
await click('nav_Admin Panel');
const backupTab = await waitFor(() => [...document.querySelectorAll('[role="tab"]')].find(t => t.innerText.includes('Backup')), 'backup tab');
backupTab.click();
await click('create_backup');
const backup = await waitFor(() => [...document.querySelectorAll('button')].find(b => b.innerText.includes('Download backup ZIP')), 'backup download');
backup.click();
await waitFor(() => (window.desktopDownloads || []).some(name => name.endsWith('.zip')), 'native ZIP download');
if (keyed('nav_Camera Reading')) throw new Error('Debug Camera Reading is exposed in the release');
await click('nav_Home');
await click('home_help');
await waitFor(() => document.body.innerText.includes('Back to Home'), 'bundled user guide');
return JSON.stringify({ok: true, downloads: window.desktopDownloads, debugToolsHidden: true});
