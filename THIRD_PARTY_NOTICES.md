# Third-party software

The standalone Mac preview additionally includes Python and PyInstaller runtime
support. Its `Contents/Resources/Licenses` directory retains the Python license,
package notices, and `build-inventory.json` identifying the build environment.
The Mac app menu provides access through **Third-party licenses**.

Itemori's original code and documentation in this branch are covered by
the root [MIT License](LICENSE), copyright 2026 syazanne. Third-party components
retain their own licenses. The root MIT license does not override them.

## Bundled browser decoder: jsQR 1.4.0

- Project: [cozmo/jsQR](https://github.com/cozmo/jsQR).
- License: **Apache-2.0**; [full license included here](scanner_frontend/vendor/LICENSE.jsQR.txt).
- Attribution and exact source: [NOTICES.txt](scanner_frontend/vendor/NOTICES.txt).
- The decoder file is included unmodified in `scanner_frontend/vendor/jsQR.js`.
- The release lists Cosmo Wolfe and Jefff Nelson as contributors.

The scanner serves the decoder, its license and its attribution together from
the local component. No CDN, npm install, or separate scanner Python package is
needed. Retain these files when sharing the app. For an upgrade, repeat the
release review recorded in [LICENSING.md](docs/LICENSING.md).

Camera Reading/OCR is a private experiment excluded from this public source
and the Mac release. Its dependencies are not distributed with Itemori.

## Python packages installed separately

`requirements.txt` installs these packages from their own distributions; their
license files and the notices for their bundled dependencies still apply.
The [inventory](docs/licenses/README.md) records the 38 installed runtime
packages inspected on 19 September 2026. Full license/notice copies are retained
in [docs/licenses/](docs/licenses/), with source locations and SHA-256 hashes in
[inventory.json](docs/licenses/inventory.json).

| Reviewed package | Top-level license | Retained license copy |
| --- | --- | --- |
| Streamlit 1.50.0 | Apache-2.0 | [License](docs/licenses/streamlit-1.50.0/LICENSE) |
| qrcode 8.2 | BSD-3-Clause, with an upstream MIT notice | [License](docs/licenses/qrcode-8.2/qrcode-8.2.dist-info/LICENSE) |
| Pillow 11.3.0 | MIT-CMU, plus bundled component notices | [License](docs/licenses/pillow-11.3.0/pillow-11.3.0.dist-info/licenses/LICENSE) |
| pypdf 6.18.1 | BSD-3-Clause | [License](docs/licenses/pypdf-6.18.1/pypdf-6.18.1.dist-info/licenses/LICENSE) |

If distributing installed packages, an executable, or a container image, also
include the applicable licenses and notices from those exact package versions.
The copies here document the reviewed versions, not every future installation.

## Additional notices from those distributions

- **Streamlit 1.50.0:** [LICENSE](docs/licenses/streamlit-1.50.0/LICENSE),
  [NOTICES](docs/licenses/streamlit-1.50.0/NOTICES), and the supplied frontend/font
  license texts are copied unchanged from its official release tag. The NOTICES
  file lists the applicable component attributions, license alternatives and
  source locations.
- **Pillow 11.3.0:** its complete license includes bundled codec/font-library
  notices. This software is based in part on the work of the Independent JPEG
  Group. This software also uses the FreeType library; its copyright notices
  and full license are retained in the Pillow license copy. The FreeType version
  in the inspected Pillow wheel is 2.13.3.
- **PyArrow 21.0.0:** its Apache `LICENSE.txt` and `NOTICE.txt` are both retained,
  including attributions for the Apache Software Foundation and bundled code.
- **certifi:** the September source-review snapshot used 2026.7.22. The Mac
  preview uses **2026.10.23** and includes its unmodified source, certificate
  data, full MPL-2.0 license and hashes under
  `Contents/Resources/Licenses/Sources/certifi-2026.10.23/`.
- **PyInstaller 6.16.0:** its full license and bundling exception are retained
  under `Contents/Resources/Licenses/installed/pyinstaller/`. The exception
  permits distributing the generated application under its own license; it
  does not replace the licenses of bundled dependencies.
- **NumPy 2.0.2:** its full license includes native-library terms and the GCC
  Runtime Library Exception. These notices have not been replaced by the
  project's MIT license.

These copies document the reviewed environment; another installation may
resolve different versions. For review scope and future redistribution steps,
see [docs/LICENSING.md](docs/LICENSING.md).
