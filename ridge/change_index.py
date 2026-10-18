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
# index_path_for(), save_index() and load_index() keep the index
# in a JSON file between runs, so next week's scan has something
# to compare against. Each project gets its own file, named after
# its id. A save writes to a temporary file first and swaps it in
# only when the write has finished, so a crash halfway through
# leaves the old index as it was.
#
# hash_paragraphs() gives each paragraph its own fingerprint, so
# RIDGE can say which part of a file changed instead of only that
# something did.
#
# compare_indexes() lines up last run's index against this run's
# scan and sorts the files into new, deleted, changed and renamed.
#
# compare_entries() looks inside one changed file and says which
# header fields changed and which paragraphs were added or removed.
# ============================================================

import json
import os
import sys
from hashlib import sha256
from pathlib import Path

from ridge.records import read_header_and_body


def hash_file_text(file_path):
    # Windows and Linux end lines differently. Making them the same
    # first means a file only gets a new fingerprint when its words
    # change.
    text = file_path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")  # Windows to Linux line endings

    return sha256(text.encode("utf-8")).hexdigest()[:16]  # 16 hex chars = 64 bits


def hash_paragraphs(text):
    text = text.replace("\r\n", "\n")  # Windows to Linux line endings

    paragraph_hashes = []

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()  # remove leading/trailing whitespace

        if paragraph.strip():  # ignore empty paragraphs
            paragraph_hashes.append(sha256(paragraph.encode("utf-8")).hexdigest()[:16])

    return paragraph_hashes


def scan_project(project_location, conventions, included_patterns):
    # Returns one entry per allowed file, keyed by its path relative
    # to the project folder. The scan lists every allowed file,
    # broken ones included. Judging whether a file is a valid record
    # is records.py's job.
    index = {}

    for folder_path in conventions.values():
        folder = Path(project_location) / folder_path
        if not folder.exists():
            continue  # ADR-0006: a missing folder is normal for a new project

        # A set keeps one copy of each file, even if it matches two
        # patterns.
        matching = set()

        for pattern in included_patterns:
            matching.update(
                folder.glob(pattern)
            )  # a pattern starting with **/ also reaches subfolders

        # Sorted, so the index comes out in the same order on every
        # computer, whatever order the operating system lists files in.
        for file_path in sorted(matching):
            relative_path = file_path.relative_to(
                project_location
            ).as_posix()  # forward slashes on every computer

            header, body = read_header_and_body(file_path)

            index[relative_path] = {
                "header": header,
                "paragraphs": hash_paragraphs(body),
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
                "hash": hash_file_text(file_path),
            }

    return index


def index_path_for(state_folder, project_id):
    # Every project gets its own memory file, named after its id, so
    # a damaged file only ever affects one project.
    file_name = f"{project_id}-index.json"
    index_path = Path(state_folder) / file_name
    return index_path


def save_index(index, index_path):
    # Writes to a scratch copy first and swaps it in only when the
    # write has finished. If RIDGE crashes halfway through, only the
    # scratch copy is broken and the old index is still there.
    index_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = index_path.with_suffix(".tmp")

    with open(temp_path, "w", encoding="utf-8") as temp_file:
        json.dump(index, temp_file, indent=2)

    os.replace(temp_path, index_path)  # one step, so never half done


def load_index(index_path):
    # No file means this is the project's first run, so it returns
    # None. That is different from an empty index, which would make
    # every file look new. A damaged file stops the run for the same
    # reason: carrying on would post the whole project history.
    if not index_path.exists():
        return None  # no index yet, so nothing to compare against

    try:
        with open(index_path, "r", encoding="utf-8") as index_file:
            return json.load(index_file)
    except json.JSONDecodeError as error:
        print(f"[ERR] Error reading index file {index_path}: {error}", file=sys.stderr)
        sys.exit(1)


def compare_indexes(old_index, new_index):
    # Returns three lists of files: new, deleted and changed. Each
    # list contains the file's path relative to the project folder.
    old_files = set(old_index.keys())
    new_files = set(new_index.keys())

    new = new_files - old_files
    deleted = old_files - new_files

    changed = []
    renamed = []

    for file_path in old_files & new_files:
        if old_index[file_path]["hash"] != new_index[file_path]["hash"]:
            changed.append(file_path)

    for new_path in sorted(new):
        for old_path in sorted(deleted):
            if old_index[old_path]["hash"] == new_index[new_path]["hash"]:
                renamed.append([old_path, new_path])
                deleted.remove(old_path)
                new.remove(new_path)
                break

    return {
        "new": sorted(new),
        "deleted": sorted(deleted),
        "changed": sorted(changed),
        "renamed": sorted(renamed),
    }


def compare_entries(old_entry, new_entry):

    header_changes = {}
    # Compare the header fields in the old entry to those in the new entry. If a field's value is different, add it to the header_changes dictionary with the old and new values.
    for field in set(old_entry["header"].keys()) | set(new_entry["header"].keys()):
        old_value = old_entry["header"].get(field)
        new_value = new_entry["header"].get(field)
        if old_value != new_value:
            header_changes[field] = [old_value, new_value]

    added_paragraphs = []
    # Compare the paragraphs in the new entry to those in the old entry. If a paragraph's hash is not found in the old entry, it is considered added.
    for position, paragraph_hash in enumerate(new_entry["paragraphs"]):
        if paragraph_hash not in old_entry["paragraphs"]:
            added_paragraphs.append(position)

    removed_paragraph_count = 0

    # Compare the paragraphs in the old entry to those in the new entry. If a paragraph's hash is not found in the new entry, it is considered removed. The count of removed paragraphs is incremented.
    for position, paragraph_hash in enumerate(old_entry["paragraphs"]):
        if paragraph_hash not in new_entry["paragraphs"]:
            # If a paragraph's hash is not found in the new entry, it is considered removed. The count of removed paragraphs is incremented.
            removed_paragraph_count += 1

    return {
        "header_changes": header_changes,
        "added_paragraphs": added_paragraphs,
        "removed_paragraph_count": removed_paragraph_count,
    }
