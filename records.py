# ============================================================
# records.py
# Walks a project archive's conventions-mapped folders, reads
# every markdown record's frontmatter, and validates each one.
#
# validate_record() checks a single record in isolation (does it
# have an id, is its date a real date). discover_records() walks
# the archive folders and collects every record that passes.
# Each function only knows its own job on purpose, so either one
# can be tested and reasoned about without the other.
#
# find_duplicate_records() is a different kind of check: it can
# only run after discover_records() has returned the whole set,
# since spotting two records sharing one id means comparing every
# record against every other one, not checking one file at a time.
# ============================================================
from datetime import date
from pathlib import Path

import frontmatter
import yaml

from file_io import open_utf8_file


def validate_record(metadata):
    try:
        # No id means the record can never be referenced or checked
        # for duplicates later, so it's rejected rather than guessed.
        if 'id' not in metadata or metadata.get('id') is None:
            return ("Record is missing 'id' in metadata.")
        # The date has to be a real date, not just present. YAML
        # auto-parses a valid YYYY-MM-DD into an actual date object;
        # anything else, including a literal "YYYY-MM-DD" left over
        # in an unfilled template, stays plain text and fails here.
        if isinstance(metadata.get('date'), date) is False:
            return ("Record is missing 'date' in metadata.")
    except AttributeError as err:
        return (f"Error validating record metadata: {err}")
    return None


def discover_records(project_location, conventions):
    valid_records = []
    for convention in conventions.items():
        print(f"Discovering records for convention: {convention}")
        folder = Path(project_location) / convention[1]
        if not folder.exists():
            # Not fatal — a project may simply not have any
            # records of this type yet (no decisions made yet).
            print(f"Folder does not exist: {folder}")
            continue
        for record_file in folder.glob("*.md"):
            with open_utf8_file(record_file, 'r') as file:
                try:
                    post = frontmatter.load(file)
                except yaml.YAMLError as err:
                    # One malformed record shouldn't take down the
                    # whole archive read. Skip it, but loudly — this
                    # is a data problem worth someone's attention,
                    # not something to bury in the regular output.
                    print(f"!!! SKIPPING {record_file} — malformed YAML frontmatter: {err}")
                    continue
                validation_error = validate_record(post.metadata)
                if validation_error:
                    # Log it and move on — one bad record shouldn't
                    # stop the rest of the archive from being read.
                    print(f"Validation error in {record_file}: {validation_error}")
                else:
                    valid_records.append(post.metadata)

    return valid_records


def find_duplicate_records(records):
    # This only makes sense after discover_records() has returned the
    # whole set — spotting a shared id means comparing every record
    # against every other one, not checking one file in isolation.
    all_found_ids = set()
    duplicates = []
    for record in records:
        record_id = record.get('id')
        if record_id in all_found_ids:
            duplicates.append(record)
        else:
            all_found_ids.add(record_id)
    return duplicates
