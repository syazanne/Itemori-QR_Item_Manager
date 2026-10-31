# Itemori

**Offline item records, organised with QR labels.**

Itemori (formerly QR Item Manager) helps you keep track of belongings, books,
tools, supplies, and equipment. Give each item a permanent Record ID, save its
details, generate a QR label, and scan the label to open its record.

[User guide](https://github.com/syazanne/Itemori-QR_Item_Manager/blob/project-1-item-manager2/docs/USER_GUIDE.md) · [Source code](https://github.com/syazanne/Itemori-QR_Item_Manager/tree/project-1-item-manager2) · [MIT license](LICENSE)

## What you can do

- Choose up to **six custom fields**, with Text / Number or Date inputs.
- Add, search, view, edit, and delete item records.
- Generate QR images and printable labels with permanent Record IDs.
- Scan a QR label with your camera to open its record.
- Save records locally in SQLite.
- Export a backup ZIP and restore it when moving to another installation.

The QR contains only the Record ID, such as `REC-0001`. Editing an item's details
does not change its ID or require a new label. Use Itemori's scanner to open the
record; a general phone camera may show the ID as text.

## Get Itemori

### Mac app preview

The standalone **Itemori.app** preview targets **Apple Silicon Macs (M1 and
later), macOS 14 or later**. It includes Python and the required components,
opens in its own window, and works offline without Terminal setup.

**The Mac preview has not yet been published as a GitHub Release.** There is no
installer download on this repository yet. GitHub's **Code → Download ZIP**
downloads source code, not the standalone application. You can run the published
source version using the instructions below.

### Run from source

The published application source currently lives on
[`project-1-item-manager2`](https://github.com/syazanne/Itemori-QR_Item_Manager/tree/project-1-item-manager2).
The `main` branch is the repository overview.

You need Python **3.9 or later, except 3.9.7**, a terminal, and a browser.
Internet access is needed to install dependencies; the core item manager works
locally after setup. A camera is optional, and a printer is only needed for
paper labels. No account, API key, or separate database server is required.

On macOS or Linux:

```bash
git clone --branch project-1-item-manager2 https://github.com/syazanne/Itemori-QR_Item_Manager.git
cd Itemori-QR_Item_Manager
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Alternatively, open the source branch, choose **Code → Download ZIP**, extract
it, and run the setup commands from the folder containing `app.py`.

Open **http://localhost:8502** in your browser and keep the terminal running.
Stop the app with **Ctrl+C**. For later sessions, activate the environment and
run `python -m streamlit run app.py` again.

The published source has been tested with Python **3.9.6** and Streamlit
**1.50.0**. Dependency minimums are in [requirements.txt](https://github.com/syazanne/Itemori-QR_Item_Manager/blob/project-1-item-manager2/requirements.txt).

## Start with one item

1. Open **Admin Panel → Field Settings** and save your field names and types.
2. Go to **Manage → Add**, then open the new Record ID.
3. Enter the item's details and **Save** each field.
4. Select **Generate QR**, then download the image or print a label.
5. Open **Home → Scan QR** to scan the label and view the item in Library.

Use **Edit Record** to update details. Save each field before leaving the page;
unsaved changes are not included in backups.

| Page | Purpose |
| --- | --- |
| Home | Scan a QR label or open the built-in guide. |
| Library | Search and view item records. |
| Manage | Add, edit, or delete records and create QR labels. |
| Admin Panel | Configure fields and use Backup & Restore. |

See the [step-by-step user guide](https://github.com/syazanne/Itemori-QR_Item_Manager/blob/project-1-item-manager2/docs/USER_GUIDE.md) for field setup,
scanning, label printing, and backups.

## Data and backups

Source installations store the database in `data/machines.db` and QR images in
`qr_codes/`. The Mac desktop preview stores its data separately under
`~/Library/Application Support/QR Item Manager/`; the original folder name is
retained so records remain available after the rename to Itemori.

In **Admin Panel → Backup & Restore**, create and download a backup ZIP.
Restore replaces the current collection and creates a safety backup first; it
does not merge collections. Keep downloaded backups on separate storage.
Records do not synchronize automatically between installations.

Personal databases, generated QR images, backups, Python environments, and
built applications are excluded from Git. The source repository contains no
personal collection to import automatically.

## Scope

Itemori is a local item-record tool. It does not currently provide borrowing
workflows, stock accounting, login accounts, or access roles. Library is a
read-only view, not an access-control boundary. Anyone with access to the app
can navigate to Manage and Admin Panel.

Record IDs are permanent and are not reused after deletion. Last updated shows
the latest saved change, not a full edit history. The interface is currently in
English. Lists display all matching records without pagination.

## Development

The main files are:

| Path | Purpose |
| --- | --- |
| `app.py` | Streamlit interface and navigation. |
| `database.py` | SQLite schema and record operations. |
| `field_utils.py` | Field types and date handling. |
| `qr_utils.py` / `label_utils.py` | QR images and printable labels. |
| `scanner.py` / `scanner_frontend/` | Local camera scanning and bundled jsQR decoder. |
| `backup_utils.py` | Backup validation, export, and restore. |
| `tests/` | Automated regression tests. |

Run tests from the source checkout:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## License

Itemori's original application code and documentation are licensed under the
**[MIT License](LICENSE)** — copyright **2026 syazanne**.

Third-party components retain their own licenses. See
[THIRD_PARTY_NOTICES.md](https://github.com/syazanne/Itemori-QR_Item_Manager/blob/project-1-item-manager2/THIRD_PARTY_NOTICES.md) and the
[dependency notices](https://github.com/syazanne/Itemori-QR_Item_Manager/blob/project-1-item-manager2/docs/licenses/README.md).
