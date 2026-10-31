"""Exercise table resizing, wrapping, row actions and safe Back navigation.

Uses disposable records and a local server. Requires Playwright and Chrome.
"""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import database as db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='itemori-layout-') as folder:
        data = Path(folder)
        path = data / 'data/machines.db'
        db.initialize_db(path)
        for index, name in enumerate(['Bookname', 'Genre', 'PIC', 'BorrowDate', 'ReturnDate', 'Borrower']):
            if index:
                db.add_field(path)
            db.save_field_name(path, db.get_fields(path)[index]['id'], name)
        fields = db.get_fields(path)
        books = ['Alice in Wonderland', 'A very long book title with enough words to wrap onto several lines', '<img src=x onerror=alert(1)>']
        for book in books:
            record = db.create_record(path)
            for field, value in zip(fields, [book, 'Non-fiction', 'Maria', '01/10/2026', '07/10/2026', 'Ellie']):
                db.save_record_value(path, record, field['id'], value)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        with (data / 'server.log').open('w') as log:
            process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
                                        '--server.headless=true', '--server.address=127.0.0.1',
                                        f'--server.port={port}', '--browser.gatherUsageStats=false'],
                                       cwd=ROOT, env=dict(os.environ, QR_ITEM_MANAGER_DATA_DIR=folder),
                                       stdout=log, stderr=log)
            try:
                url = f'http://127.0.0.1:{port}'
                for _ in range(100):
                    try:
                        with urlopen(url + '/_stcore/health', timeout=1):
                            break
                    except OSError:
                        time.sleep(.1)
                with sync_playwright() as p:
                    browser = p.chromium.launch(executable_path=args.browser, headless=True)
                    page = browser.new_page(viewport={'width': 1280, 'height': 900})
                    page.goto(url)
                    page.locator('.st-key-nav_Manage button').click()
                    handles = page.get_by_role('separator')
                    expect(handles).to_have_count(9)
                    table = page.locator('table.manage-records')
                    cells = table.locator('tbody tr').first.locator('td')
                    expect(cells.nth(2)).to_have_text(books[0])
                    assert table.locator('img').count() == 0

                    def drag(delta):
                        handle = page.get_by_role('separator', name='Resize Bookname column', exact=True)
                        box = handle.bounding_box()
                        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        page.mouse.down()
                        page.mouse.move(box['x'] + box['width']/2 + delta, box['y'] + box['height']/2, steps=12)
                        page.mouse.up()

                    before = cells.nth(2).bounding_box()['width']
                    drag(130)
                    assert abs(cells.nth(2).bounding_box()['width'] - before - 130) < 2
                    drag(-220)
                    assert cells.nth(2).bounding_box()['height'] > 45
                    assert cells.nth(2).evaluate('(e) => e.scrollHeight <= e.clientHeight && getComputedStyle(e).textOverflow !== "ellipsis"')
                    page.wait_for_timeout(250)
                    for i in range(3):
                        row = table.locator('tbody tr').nth(i).bounding_box()
                        button = page.locator(f'.st-key-delete_REC-000{i+1} button').bounding_box()
                        assert row['y'] <= button['y'] < row['y'] + row['height'], (row, button,
                            page.locator('.st-key-manage_add_slot').evaluate('(e) => e.outerHTML'),
                            page.locator('.st-key-manage_toolbar').evaluate('(e) => e.outerHTML')[:800])
                    page.locator('.st-key-delete_REC-0002 button').click()
                    expect(page.get_by_role('dialog')).to_contain_text('REC-0002')
                    page.locator('.st-key-cancel_delete button').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    expect(handles).to_have_count(9)
                    width = cells.nth(2).bounding_box()['width']
                    page.locator('.st-key-manage_search input').fill('Alice')
                    page.locator('.st-key-manage_search input').press('Enter')
                    expect(table.locator('tbody tr')).to_have_count(1)
                    assert abs(cells.nth(2).bounding_box()['width'] - width) < 2
                    page.get_by_role('link', name='REC-0001', exact=True).click()
                    entry = page.locator('.st-key-value_REC-0001_1 input')
                    expect(entry).to_have_value(books[0])
                    entry.fill('Unsaved draft')
                    page.locator('.st-key-detail_back button').click()
                    expect(page.get_by_role('dialog')).to_contain_text('Unsaved changes')
                    page.locator('.st-key-stay_on_page button').click()
                    expect(entry).to_have_value('Unsaved draft')
                    page.locator('.st-key-detail_back button').click()
                    page.locator('.st-key-leave_page button').click()
                    expect(table).to_be_visible()
                    assert db.get_record(path, 'REC-0001')['values'][fields[0]['id']] == books[0]
                    expect(handles).to_have_count(9)
                    assert abs(cells.nth(2).bounding_box()['width'] - width) < 2
                    page.set_viewport_size({'width': 600, 'height': 900})
                    page.wait_for_timeout(250)
                    assert page.locator('.manage-table-scroll').evaluate('(e) => e.scrollWidth > e.clientWidth')
                    row = table.locator('tbody tr').first.bounding_box()
                    button = page.locator('.st-key-delete_REC-0001 button').bounding_box()
                    assert row['y'] <= button['y'] < row['y'] + row['height'], (row, button)
                    evidence = ROOT / 'build/layout-test'
                    evidence.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(evidence / 'narrow.png'), full_page=True)
                    page.set_viewport_size({'width': 1280, 'height': 900})
                    page.screenshot(path=str(evidence / 'manage.png'), full_page=True)
                    browser.close()
                print('PASS: drag widths, full wrapped text, aligned deletion, rerenders, narrow screen and Back with unsaved changes')
            finally:
                process.terminate()
                process.wait(timeout=20)


if __name__ == '__main__':
    main()
