# ============================================================
# change_index.py
# Builds the index RIDGE uses to tell what changed since the last
# post (ADR-0008).
#
# hash_file_text() turns a file's text into a short fingerprint.
# The same words always give the same fingerprint, so RIDGE can
# tell a real edit apart from a file whose timestamp changed while
# its text stayed the same.
#
# scan_project() looks through the folders a project's ridge.yml
# lists, and records an entry for every allowed file: its path
# relative to the project folder, its size, when it was last
# changed, and its fingerprint.
#
# Not built yet: saving and loading the index, comparing a scan to
# the saved index, and fingerprints for each paragraph.
# ============================================================

from hashlib import sha256
from pathlib import Path    

def hash_file_text(file_path):
    # To build: read the file's text, make Windows and Linux line
    # endings the same, and return the fingerprint as text.

    text = file_path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")  # Windows to Linux line endings

    return sha256(text.encode("utf-8")).hexdigest()[:16]  # 16 hex chars = 64 bits


def scan_project(project_location, conventions, included_patterns):
    # To build: return a dict with one entry per allowed file in the
    # folders listed under conventions. The key is the file's path
    # relative to project_location. The value holds the size, the
    # last-changed time, and the fingerprint.

    index = {}

    for record_type, folder_path in conventions.items():
        folder = Path(project_location) / folder_path
        if not folder.exists():
            continue  # ADR-0006: a missing folder is normal for a new project

        matching = set()  # a set keeps one copy of each file, even if it matches two patterns

        for pattern in included_patterns:
            matching.update(folder.glob(pattern))  # glob finds files in the folder but not subfolders   

        for file_path in sorted(matching): # sort so the index is always built the same way, even if the OS lists files in a different order
            relative_path = file_path.relative_to(project_location).as_posix()  # use forward slashes for cross-platform consistency    
            
            index[relative_path] = {
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
                "hash": hash_file_text(file_path),
            }
    return index
