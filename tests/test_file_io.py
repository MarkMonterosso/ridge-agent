# ============================================================
# test_file_io.py
# Tests for open_utf8_file in file_io.py: a missing file, and a
# normal file with a character outside plain English in it, which
# proves the file is really being read as UTF-8.
# ============================================================
import pytest

from file_io import open_utf8_file


# open_utf8_file should stop the program if the file it's given
# doesn't exist, rather than crashing with an unhandled error.
def test_open_utf8_file_missing_file():
    with pytest.raises(SystemExit):
        open_utf8_file("nonexistent_file.txt")


# The content should come back decoded correctly, including a
# character outside plain English. A dash like the one in the test
# text used to come out as garbage, which is the bug the UTF-8 fix
# solved.
def test_open_utf8_file_reads_utf8_content(tmp_path):
    test_file = tmp_path / "utf8_test.txt"
    test_file.write_text("Phase 1 — inputs", encoding="utf-8")

    with open_utf8_file(test_file) as opened_file:
        content = opened_file.read()

    assert content == "Phase 1 — inputs"


# What open_utf8_file returns has to work like a file: in a "with"
# block, and with .read(). It's really a copy of the text held in
# memory (a StringIO), with the file on disk already closed.
def test_open_utf8_file_returns_file_like_object(tmp_path):
    test_file = tmp_path / "plain.txt"
    test_file.write_text("hello", encoding="utf-8")

    with open_utf8_file(test_file) as opened_file:
        assert hasattr(opened_file, "read")
        assert opened_file.read() == "hello"
