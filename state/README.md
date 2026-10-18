# state

RIDGE's memory. After each approved post, RIDGE saves one file here
per project it tracks, listing every file it saw and a fingerprint of
each one. On the next run it compares against these files to find
what changed.

This folder is part of RIDGE and stays where it is. The memory files
inside it are never committed, because they belong to your machine.
Don't edit them by hand.
