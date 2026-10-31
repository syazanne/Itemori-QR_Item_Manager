"""Regression checks for native QR size, placement and changes of paper size."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import qrcode
from label_utils import LABEL_SIZES, label_pdf
from pypdf import PdfReader


def qr_rectangles(page):
    rectangles = []
    def visit(operator, operands, matrix, _text_matrix):
        if operator != b"re":
            return
        x, y, width, height = map(float, operands)
        if not (0 < width < 10 and abs(width - height) < 0.001):
            return
        a, b, c, d, e, f = matrix
        corners = [(a * px + c * py + e, b * px + d * py + f)
                   for px, py in ((x, y), (x + width, y), (x, y + height), (x + width, y + height))]
        xs, ys = zip(*corners)
        rectangles.append((min(xs), min(ys), max(xs), max(ys)))
    page.extract_text(visitor_operand_before=visit)
    return rectangles


def main():
    output = ROOT / "build/print-test"
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    mm = 72 / 25.4
    for size in LABEL_SIZES:
        for paper, width, height, margin in (("A4", 210 * mm, 297 * mm, 18),
                                              ("A5", 148 * mm, 210 * mm, 18),
                                              ("215x345", 215 * mm, 345 * mm, 18),
                                              ("Letter", 612, 792, 18),
                                              ("Label", size * mm, size * mm, 0),
                                              ("ChangedToLabel", size * mm, size * mm, 0)):
            name = f"{size}mm-{paper}"
            record = "REC-0001"
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
            qr.add_data(record)
            qr.make(fit=True)
            dark_side = (size - 8) * mm * (len(qr.get_matrix()) - 8) / len(qr.get_matrix())
            (output / (name + "-source.pdf")).write_bytes(label_pdf(record, size))
            cases.append(dict(name=name, record=record, paperWidth=width, paperHeight=height,
                              margin=margin, qrDarkSide=dark_side, changePaper=paper == "ChangedToLabel"))
    (output / "cases.json").write_text(json.dumps(cases))
    env = dict(os.environ, CLANG_MODULE_CACHE_PATH=str(ROOT / "build/clang-cache"))
    executable = output / "LabelPrintingTests"
    subprocess.run(["xcrun", "swiftc", "-parse-as-library", "-swift-version", "5",
                    "-target", "arm64-apple-macosx14.0", str(ROOT / "desktop/LabelPrinting.swift"),
                    str(ROOT / "tests/LabelPrintingTests.swift"), "-o", str(executable),
                    "-framework", "Cocoa", "-framework", "PDFKit", "-framework", "Vision"],
                   env=env, check=True)
    subprocess.run([str(executable), str(output)], check=True)
    for case in cases:
        source = PdfReader(output / (case["name"] + "-source.pdf")).pages[0]
        printed = PdfReader(output / (case["name"] + "-printed.pdf")).pages[0]
        before, after = qr_rectangles(source), qr_rectangles(printed)
        assert before and len(before) == len(after), case["name"] + ": QR modules missing"
        offset_x = case["margin"]
        offset_y = float(printed.mediabox.height) - case["margin"] - float(source.mediabox.height)
        for original, actual in zip(before, after):
            expected = (original[0] + offset_x, original[1] + offset_y,
                        original[2] + offset_x, original[3] + offset_y)
            assert all(abs(x - y) < 0.01 for x, y in zip(actual, expected)), (case["name"], actual, expected)
        print("PASS", case["name"], ": every QR module preserved at actual size and placed at the upper-left margin within 0.01 point")


if __name__ == "__main__":
    main()
