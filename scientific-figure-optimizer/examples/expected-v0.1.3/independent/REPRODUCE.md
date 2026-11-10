Tested Python 3.12.14; use the same Python minor version for this lock.

From this folder, create an isolated environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe figure.py verify .
.venv\Scripts\python.exe figure.py render brief.json --out ../rerun-new-version
.venv\Scripts\python.exe figure.py verify ../rerun-new-version
```

Font: DejaVu Sans; SHA256 3fdf69cabf06049ea70a00b5919340e2ce1e6d02b0cc3c4b44fb6801bd1e0d22. The portable brief enforces this fingerprint. DejaVu Sans comes with pinned Matplotlib. Custom fonts require an independently licensed installation; no fonts are copied. This dependency closure targets the recorded Python/OS; other platforms require revalidation. SVG text needs the font on the editing machine. File bytes may differ due to export timestamps; compare numerical readback, point order, source hash and dimensions. Human scientific and final-size visual review remains required.
