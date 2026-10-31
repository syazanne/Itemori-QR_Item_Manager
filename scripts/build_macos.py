"""Build a self-contained Apple Silicon app and a ZIP suitable for downloading."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "Itemori"
VERSION = "0.1.9"
ARCHIVE_NAME = f"{NAME}-v{VERSION}-preview-macOS-AppleSilicon.zip"
BUNDLE_ID = "com.syazanne.qritemmanager"


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def copy_without_finder_metadata(source, destination):
    shutil.copyfile(source, destination)
    shutil.copymode(source, destination)
    return destination


def collect_licenses(destination):
    shutil.copytree(ROOT / "docs/licenses", destination / "runtime")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copyfile(ROOT / name, destination / name)
    inventory = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = dist.metadata["Name"]
        files = []
        for file in dist.files or []:
            if ".dist-info/" not in str(file) or not any(term in str(file).lower() for term in ("license", "copying", "notice")):
                continue
            source = Path(dist.locate_file(file))
            if not source.is_file():
                continue
            target = destination / "installed" / name / str(file)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            files.append(str(target.relative_to(destination)))
        inventory.append({"package": name, "version": dist.version, "files": files})
    python_license = Path(sys.base_prefix) / "lib" / ("python" + str(sys.version_info.major) + "." + str(sys.version_info.minor)) / "LICENSE.txt"
    if not python_license.is_file():
        raise RuntimeError("Python's LICENSE.txt is required for the standalone build.")
    shutil.copyfile(python_license, destination / "Python-LICENSE.txt")
    (destination / "build-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    # Supply the exact unmodified MPL-covered source alongside the executable.
    certifi = metadata.distribution("certifi")
    source_root = destination / "Sources" / ("certifi-" + certifi.version)
    source_files = {}
    for file in certifi.files or []:
        if file.parts[0] != "certifi" or file.suffix == ".pyc":
            continue
        source = Path(certifi.locate_file(file))
        target = source_root / file
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        source_files[str(file)] = hashlib.sha256(target.read_bytes()).hexdigest()
    if not {"certifi/core.py", "certifi/cacert.pem"} <= source_files.keys():
        raise RuntimeError("The certifi source and certificate data must accompany the release.")
    shutil.copyfile(certifi.locate_file(f"certifi-{certifi.version}.dist-info/licenses/LICENSE"), source_root / "LICENSE")
    (source_root / "SHA256.json").write_text(json.dumps(source_files, indent=2) + "\n")
    (destination / "README.txt").write_text(
        "Itemori original code: MIT; third-party components retain their own terms.\n"
        "installed/ contains notices from the actual build environment.\n"
        "runtime/ retains the historical source review, including Streamlit frontend notices.\n"
        "build-inventory.json lists the build environment, including tools not shipped at runtime.\n"
        f"certifi {certifi.version}: unmodified MPL-2.0-covered source and certificate data\n"
        f"are included in Sources/certifi-{certifi.version}/ with their license and hashes.\n"
        "Python-LICENSE.txt and installed/pyinstaller/ retain interpreter and bundling terms.\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-backend", action="store_true")
    options = parser.parse_args()
    if sys.platform != "darwin" or platform.machine() != "arm64":
        parser.error("Build this version on an Apple Silicon Mac.")
    os.environ.setdefault("PYINSTALLER_CONFIG_DIR", str(ROOT / "build/pyinstaller-cache"))
    os.environ.setdefault("CLANG_MODULE_CACHE_PATH", str(ROOT / "build/clang-cache"))
    if not options.reuse_backend:
        run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", "build/runtime",
            "--workpath", "build/pyinstaller", "desktop/backend.spec")
    backend = ROOT / "build/runtime/qr-item-manager-backend"
    for name in ("app.py", "desktop_ui/records_table.js", "scanner_frontend/vendor/jsQR.js", "docs/USER_GUIDE.md"):
        if not (backend / "_internal" / name).is_file():
            raise RuntimeError("Missing bundled resource: " + name)
    if (backend / "_internal/camera_reading_frontend").exists():
        raise RuntimeError("Debug OCR assets must not be included in the release. Rebuild without --reuse-backend.")
    output = ROOT / "app"
    output.mkdir(exist_ok=True)
    release_app = output / (NAME + ".app")
    if release_app.exists():
        info = release_app / "Contents/Info.plist"
        if not info.is_file() or plistlib.loads(info.read_bytes()).get("CFBundleIdentifier") != BUNDLE_ID:
            raise RuntimeError("Refusing to replace an unrecognized app: " + str(release_app))
    # iCloud-managed Desktop folders can restore FinderInfo while codesign runs.
    # Assemble and sign outside that folder, then archive the verified bundle.
    staging = tempfile.TemporaryDirectory(prefix="qr-item-manager-package-")
    app = Path(staging.name) / (NAME + ".app")
    contents = app / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir()
    shutil.copytree(backend, resources / "backend", symlinks=True)
    collect_licenses(resources / "Licenses")
    info = {
        "CFBundleName": NAME, "CFBundleDisplayName": NAME, "CFBundleExecutable": "Itemori",
        "CFBundleIdentifier": BUNDLE_ID, "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": VERSION, "CFBundleVersion": "10",
        "LSMinimumSystemVersion": "14.0", "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "NSCameraUsageDescription": "Scan QR item labels using your camera.",
        "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
        "NSHumanReadableCopyright": "Copyright © 2026 syazanne. Original application code: MIT.",
    }
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    run("xcrun", "swiftc", "-parse-as-library", "-swift-version", "5", "-O",
        "-target", "arm64-apple-macosx14.0", "desktop/Itemori.swift", "desktop/LabelPrinting.swift",
        "-o", str(macos / "Itemori"), "-framework", "Cocoa", "-framework", "WebKit", "-framework", "PDFKit")
    for attribute in ("com.apple.FinderInfo", "com.apple.ResourceFork"):
        run("xattr", "-dr", attribute, str(app))
    run("codesign", "--force", "--deep", "--sign", "-", str(app))
    run("codesign", "--verify", "--deep", "--strict", str(app))
    archive = output / ARCHIVE_NAME
    archive.unlink(missing_ok=True)
    run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(archive))
    if release_app.exists():
        shutil.rmtree(release_app)
    shutil.copytree(app, release_app, symlinks=True, copy_function=copy_without_finder_metadata)
    # The cloud file provider can add metadata while the directory is copied.
    for attribute in ("com.apple.FinderInfo", "com.apple.ResourceFork"):
        run("xattr", "-dr", attribute, str(release_app))
    verification = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(release_app)],
        text=True, capture_output=True,
    )
    if verification.returncode:
        if "resource fork, Finder information, or similar detritus not allowed" not in verification.stderr:
            raise RuntimeError(verification.stderr)
        # Some iCloud folders immediately restore these attributes. Validate the
        # archive independently; it is the distributable, signed copy.
        extracted = Path(staging.name) / "archive-check"
        run("ditto", "-x", "-k", str(archive), str(extracted))
        run("codesign", "--verify", "--deep", "--strict", str(extracted / (NAME + ".app")))
        print("iCloud added Finder metadata to the project copy. Install from the verified ZIP into Applications.")
    staging.cleanup()
    (output / "READ-ME.txt").write_text(
        f"Itemori — macOS preview {VERSION}\n\n"
        f"Download: {ARCHIVE_NAME}\n\n"
        "Requires an Apple Silicon Mac (M1 or later), macOS 14 or later.\n"
        "Unzip, drag Itemori.app into Applications, then double-click it.\n"
        "Python, Terminal and internet access are not required to use the app.\n\n"
        "This preview is locally signed, not Apple-notarized. A downloaded copy may be\n"
        "blocked by macOS. Only if you trust its source, review System Settings >\n"
        "Privacy & Security > Open Anyway. Do not disable Gatekeeper.\n\n"
        "Data: ~/Library/Application Support/QR Item Manager/\n"
        "To move existing records, use Admin Panel > Backup & Restore.\n"
        "The download contains no personal records.\n"
    )
    print("Built:", release_app, "\nDownload:", archive)


if __name__ == "__main__":
    main()
