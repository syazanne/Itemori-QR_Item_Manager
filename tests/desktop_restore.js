// The runner prepends the shared helpers from desktop_smoke.js.
await waitFor(() => keyed('value_REC-0001_1')?.querySelector('input')?.value === 'Offline desktop test', 'persisted record after restart');
await waitFor(() => keyed('print_qr_label'), 'persisted QR after restart');
await click('nav_Admin Panel');
const backupTab = await waitFor(() => [...document.querySelectorAll('[role="tab"]')].find(t => t.innerText.includes('Backup')), 'backup tab');
backupTab.click();
// WebKit requires a real user gesture for a file picker. Supply a File to the
// uploader for automation; the native picker itself remains a manual check.
const input = await waitFor(() => document.querySelector('input[type="file"]'), 'restore uploader');
const transfer = new DataTransfer();
transfer.items.add(new File([backupBytes], 'desktop-backup.zip', {type: 'application/zip'}));
input.files = transfer.files;
input.dispatchEvent(new Event('change', {bubbles: true}));
await click('review_restore');
await click('confirm_restore');
await waitFor(() => document.body.innerText.includes('Backup restored.'), 'restore completed');
return JSON.stringify({ok: true, restart: true, restore: true});
