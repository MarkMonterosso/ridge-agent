# ============================================================
# file_io.py
# Opens files for every other module, the same way each time.
#
# open_utf8_file() opens a file the same way everywhere: always
# as UTF-8, and hands back the file's contents wrapped in an
# in-memory buffer, so the real file on disk closes immediately
# instead of staying open for the caller to manage. If it can't
# open the file at all, it stops the program with a clear
# message instead of a raw traceback.
# ============================================================
import sys
from io import StringIO


def open_utf8_file(file_path, mode="r"):
    try:
        # Always read as UTF-8. Without it, open() uses the computer's
        # default (often cp1252 on Windows), which garbles characters
        # outside plain English, like accented letters.
        with open(file_path, mode, encoding="utf-8") as file:
            # Read the content now, while the real file is still open,
            # and hand back an in-memory copy instead. The real file
            # closes the moment this "with" block ends; the caller
            # gets something that behaves like a file without holding
            # the real one open past this function's return.
            return StringIO(file.read())
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        sys.exit(1)
    except PermissionError:
        print(f"Permission denied when trying to read file: {file_path}")
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"File is not valid UTF-8: {file_path}")
        sys.exit(1)
