"""A request's process (contain.py): `python -m simwaves.child`. It reads one request on stdin
and writes its result on stdout. Nothing else is imported before contain.child_main() has taken
its first steps (on Linux: die with the parent)."""
from simwaves.contain import child_main

child_main()
