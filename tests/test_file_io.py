# ============================================================
# test_file_io.py
# Tests for open_utf8_file in file_io.py. Covers a missing file
# and the happy path, including a non-ASCII character, to confirm
# UTF-8 decoding is actually happening, not just assumed.
# ============================================================
import pytest

from file_io import open_utf8_file


# open_utf8_file should stop the program if the file it's given
# doesn't exist, rather than crashing with an unhandled error.
def test_open_utf8_file_missing_file():
    with pytest.raises(SystemExit):
        open_utf8_file("nonexistent_file.txt")


# The content should come back decoded correctly, including a
# non-ASCII character. This is the exact bug (an em dash coming
# out as garbage) the encoding fix exists to catch.
def test_open_utf8_file_reads_utf8_content(tmp_path):
    test_file = tmp_path / "utf8_test.txt"
    test_file.write_text("Phase 1 — inputs", encoding="utf-8")

    with open_utf8_file(test_file) as f:
        content = f.read()

    assert content == "Phase 1 — inputs"


# What open_utf8_file returns has to behave like a file — usable
# in a "with" block, readable with .read() — even though it's
# really an in-memory StringIO, not the file on disk.
def test_open_utf8_file_returns_file_like_object(tmp_path):
    test_file = tmp_path / "plain.txt"
    test_file.write_text("hello", encoding="utf-8")

    with open_utf8_file(test_file) as f:
        assert hasattr(f, "read")
        assert f.read() == "hello"
