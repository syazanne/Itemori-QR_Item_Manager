# Itemori for Mac

The standalone application includes Python, Streamlit and QR scanning assets.
It opens in its own Mac window and stores records on the
Mac. No Python setup, Terminal, account, or internet connection is needed to use
it. This build supports **Apple Silicon (M1 and later), macOS 14 and later**.
It is not an Intel Mac, Windows, or iPad build.

## Install and use

1. Download `Itemori-v0.1.9-preview-macOS-AppleSilicon.zip` and unzip it.
2. Drag **Itemori.app** into **Applications**.
3. Double-click the app. Configure fields in **Admin Panel**, then add items in
   **Manage**. The built-in **How to use** guide also works offline.
4. Allow camera access when using **Scan QR**.
5. Save your edits before quitting. Closing the window or choosing **Quit**
   stops the application's local server.

Press **Esc** to show **Quit app?**, with **Cancel** and **Quit** buttons.
Cancel keeps the app and unsaved edits open; Esc on the quit popup also cancels.
When a dialog, dropdown, preview, or native file/print panel is open, Esc dismisses
that interface first. A held Escape key does not repeatedly request quit.

This initial preview uses a local ad-hoc signature and is **not notarized by
Apple**. A copy downloaded from the internet may be blocked by macOS. If you
trust the source, review **System Settings → Privacy & Security → Open Anyway**.
Do not disable Gatekeeper. A public release intended for frictionless downloads
still needs Developer ID signing and Apple notarization.

The `.app` is the application itself. The ZIP preserves its files for download;
a `.dmg` is not required. No installer needs to fetch extra components.

## Records, upgrades, and backups

The app starts with an empty collection; personal development records are never
included in the download. To move records from the source version, create a
backup there and restore the ZIP in the desktop app's **Admin Panel → Backup &
Restore**. Restore replaces the desktop collection and creates a safety backup.

The existing storage folder is retained across the rename so previous records
remain available. Desktop data is stored in:

```text
~/Library/Application Support/QR Item Manager/
  data/machines.db
  data/backups/
  data/scanner_component_jsqr/
  qr_codes/
  desktop.log
```

Use **Itemori → Show data folder** in the Mac menu to find it. Replacing
or moving the `.app` does not remove these records. Keep downloaded backup ZIPs
on separate storage. Source checkouts retain their original project-local data
paths; development and desktop records do not synchronize automatically.

PNG, PDF, and backup downloads use a native **Save** dialog. The label's **Print
label** button opens the Mac print panel using the same vector PDF as the
downloaded label. Labels retain their selected 40, 50, or 60 mm size and are
placed at the upper left of the selected paper, with a 5 mm sheet margin on
larger paper. Matching label paper uses the white space already inside the label.
Label size includes the QR code, white space and Record ID. Choose the paper
loaded in the printer, use 100% / Actual Size, and disable Scale to Fit to retain
the label's dimensions. The print panel exposes Paper Size, Orientation and Scale.
Alternatively, save the label PDF and print it in Preview.
Camera hardware, permission prompts, and
physical printer output should be checked on the target Mac.

The app's server listens only on `127.0.0.1`, using an available port. The native
window blocks remote HTTP resources and disables Streamlit usage telemetry.
QR scanning assets are bundled locally. Camera Reading/OCR is a private
debug experiment excluded from the public source and Mac app. External documentation
links open separately in the browser and require internet access.

## Build from source

On an Apple Silicon Mac with Xcode Command Line Tools and Python installed:

```bash
python3 -m venv .venv-desktop
.venv-desktop/bin/python -m pip install -r desktop/requirements-build.txt
.venv-desktop/bin/python scripts/build_macos.py
```

The outputs are `app/Itemori.app`,
`app/Itemori-v0.1.9-preview-macOS-AppleSilicon.zip`, and `app/READ-ME.txt`. Build outputs
are ignored by Git. Upload the ZIP and instructions as release assets when
publishing a release; the repository remains available for source changes.

If the project lives in an iCloud-synced Desktop folder, install by extracting
the ZIP into Applications. iCloud can add Finder metadata to a loose `.app`
after signing. The build signs outside iCloud before creating the archive, and
the integration check verifies and runs an extracted copy of that archive.

The build uses PyInstaller for the Python runtime and Swift/WebKit for the Mac
window. `desktop/requirements-macos.lock` records the Python 3.9 build package
versions and constrains installation. Its resources are explicitly selected; `.venv`, databases, generated QR
images, backups, and test fixtures are excluded. License texts and a build
package inventory are retained in **Contents/Resources/Licenses** and accessible
through **Itemori → Third-party licenses**.

Run the Python tests and the native integration check with:

```bash
.venv-desktop/bin/python -m unittest discover -s tests -v
.venv-desktop/bin/python scripts/test_macos.py
.venv-desktop/bin/python scripts/test_macos_print.py
.venv-desktop/bin/python scripts/test_macos_quit.py
```

The native check requires a logged-in Mac desktop. It creates disposable records,
opens the actual packaged window, edits a record, generates a QR, downloads PNG,
PDF and ZIP files, checks that debug tools are hidden, opens the bundled help
page, restarts, uploads/restores a backup, and confirms a reset of its disposable
collection. Results and
a screenshot go in `build/desktop-test`. Automation supplies the backup file to
the uploader because WebKit's file picker requires a real user gesture. Native
file panels, camera hardware and physical printing remain manual checks.

For isolated development/testing, `QR_ITEM_MANAGER_DATA_DIR` overrides the data
directory. Normal Finder launches do not require any environment variables.

## Preview 0.1.1 validation (31 October 2026)

The 65 Python tests passed. The native
integration check passed startup, record editing and persistence after restart,
QR generation, native print-to-PDF, PNG/PDF/ZIP downloads, offline English OCR, bundled help, backup
upload and restore with a safety copy. The extracted archive's ad-hoc signature
passed `codesign --verify --deep --strict`. Hardware camera access, native file
panels and physical printing still need manual checks; notarization is not part
of this preview.

Version 0.1.1 replaces HTML printing in the Mac shell with PDF printing to fix
clipped QR codes. Nine print regression cases cover every label size on A4,
Letter, and matching label paper. Each saves through the native print operation,
decodes the rendered QR, checks the Record ID, and verifies that every QR module
retains its size and centered position within 0.01 PDF point. These checks save
PDF files and never send a job to a physical printer.

Version 0.1.2 adds Escape to open the quit confirmation. Native keyboard tests
verify the shortcut from the main page and a component frame, priority for open
dialogs/dropdowns/menus, repeated-key and composition handling, preservation of
unsaved text after Cancel, Escape cancelling the quit sheet, and confirmed Quit
terminating the app.

Version 0.1.3 moves native printing to the upper left using a PDF-backed print
view. Print regression checks verify actual-size QR modules and upper-left
placement, readable QR codes, Record IDs and one-page output on larger sheets
and matching label paper. Paper-size changes are tested after the operation is
created, as well as at initial setup. These checks save PDFs, not physical prints.

Version 0.1.4 adds draggable column widths and wrapped record values in Manage
and Library, plus **Back to Manage** in Record Details. The 65 Python tests pass.
Browser checks cover pointer resizing, row-action alignment on wide and narrow
windows, retained widths during navigation, and Back with unsaved edits. The
packaged-app check also exercises keyboard resizing and Back before its existing
printing, download, OCR, restart and restore checks.

Version 0.1.5 adds a **No.** column and record counts in Manage and Library.
Numbers follow the visible list, including after deletion and filtering, while
Record IDs remain stable. All 66 Python tests and the browser layout checks pass.

Version 0.1.6 removes Camera Reading and its OCR assets from the release; the
source experiment is available with `ITEMORI_DEBUG=1`. **Admin Panel → Reset App**
requires typing `RESET` before clearing records, fields, QR images and in-app
backups, restoring one blank field and restarting Record IDs. Downloaded files
outside the app remain. All 71 Python tests pass, including reset rollback and
cleanup-error reporting. The native integration check verifies hidden debug
tools even with the debug environment flag set, reset cancellation, draft
preservation, typed confirmation, cleared preferences and default fields, and
preservation of downloaded backups, using disposable data only.

Version 0.1.7 places **← Back to Library** above the Library record heading,
matching the Back to Manage button. The bottom action row contains only
**Scan another QR** and **Edit Record**. Existing Library navigation tests pass.
