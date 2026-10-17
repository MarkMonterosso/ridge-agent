# ============================================================
# records.py
# Reads a project's records: the markdown files in the folders
# its ridge.yml lists under conventions.
#
# read_records() opens every file, works out what type of record
# it is, checks it, and returns two lists: the records it kept
# and the files it rejected, each with a reason. It prints
# nothing, so the setup check can use it too.
#
# discover_records() calls read_records(), prints each rejected
# file, and returns only the kept records. This is what the
# normal run uses.
#
# validate_record() checks one record on its own.
# find_duplicate_records() has to wait until every record is
# read, because it compares them against each other.
# ============================================================
from datetime import date
from pathlib import Path

import frontmatter
import yaml
from frontmatter.default_handlers import YAMLHandler

from file_io import open_utf8_file

# The fields each record type has to have, from the schemas in
# Phase 1 and ADR-0004. A type that isn't listed here only needs
# an id. Kept short on purpose: Phase 1 says to ask for as little
# as possible, since adding a field later is easy and removing
# one means fixing every file already written.
REQUIRED_FIELDS_BY_TYPE = {
    "session": ["id", "date"],
    "decision": ["id", "date"],
    "milestone": ["id", "state"],
}
DEFAULT_REQUIRED_FIELDS = ["id"]


class RecordLoader(yaml.SafeLoader):
    # YAML turns an unquoted id like 0001 into the number 1 and
    # throws away the zeros. Turning it back into text afterward
    # only gives "1", so this keeps the id exactly as it was
    # typed, while the file is being read. People shouldn't have
    # to remember to put quotes around their ids.
    def construct_mapping(self, node, deep=False):
        mapping = super().construct_mapping(node, deep=deep)
        for key_node, value_node in node.value:
            is_id = getattr(key_node, "value", None) == "id"
            # A blank id stays blank, so validate_record() can
            # still reject it.
            is_text_value = isinstance(value_node, yaml.ScalarNode)
            if is_id and is_text_value and mapping.get("id") is not None:
                mapping["id"] = value_node.value
        return mapping


class RecordYAMLHandler(YAMLHandler):
    # Lets python-frontmatter read the header block with
    # RecordLoader instead of its usual one.
    def load(self, fm, **kwargs):
        return yaml.load(fm, Loader=RecordLoader)


def resolve_record_type(metadata, folder_type):
    # Phase 1's type ladder. If the file says what it is, believe
    # the file. If it doesn't, use the type of the folder it was
    # found in. The third step, a built-in default, never comes up
    # here, because every file RIDGE reads comes from a folder
    # listed under conventions.
    file_type = metadata.get("type")
    if file_type:
        return file_type
    return folder_type


def validate_record(metadata):
    required_fields = REQUIRED_FIELDS_BY_TYPE.get(
        metadata.get("type"), DEFAULT_REQUIRED_FIELDS
    )
    for field in required_fields:
        if metadata.get(field) is None:
            return f"Record is missing '{field}' in metadata."
    # A date has to be a real date. YAML turns a proper
    # YYYY-MM-DD into a date object. Anything else, like the text
    # "YYYY-MM-DD" left in an unfilled template, stays text and
    # gets rejected here.
    if "date" in required_fields and not isinstance(metadata.get("date"), date):
        return "Record is missing 'date' in metadata."
    return None


def read_records(project_location, conventions):
    kept_records = []
    rejected_files = []
    for record_type, folder_path in conventions.items():
        folder = Path(project_location) / folder_path
        # A folder that doesn't exist yet is normal for a new
        # project (ADR-0006). There's nothing in it to read.
        if not folder.exists():
            continue
        for record_file in sorted(folder.glob("*.md")):
            with open_utf8_file(record_file, "r") as file:
                try:
                    post = frontmatter.load(file, handler=RecordYAMLHandler())
                except yaml.YAMLError as err:
                    # One broken file shouldn't stop the rest of the
                    # project from being read.
                    # YAML's error message runs over several lines. Squeeze
                    # it onto one so it reads cleanly in a list.
                    yaml_error = " ".join(str(err).split())
                    reason = f"the header block isn't valid YAML: {yaml_error}"
                    rejected_files.append((record_file, reason))
                    continue
            metadata = post.metadata
            metadata["type"] = resolve_record_type(metadata, record_type)
            validation_error = validate_record(metadata)
            if validation_error:
                rejected_files.append((record_file, validation_error))
            else:
                kept_records.append(metadata)
    return kept_records, rejected_files


def discover_records(project_location, conventions):
    kept_records, rejected_files = read_records(project_location, conventions)
    for record_file, reason in rejected_files:
        print(f"[WRN] Skipped {record_file}: {reason}")
    return kept_records


def find_duplicate_records(records):
    all_found_ids = set()
    duplicates = []
    for record in records:
        record_id = record.get("id")
        if record_id in all_found_ids:
            duplicates.append(record)
        else:
            all_found_ids.add(record_id)
    return duplicates
