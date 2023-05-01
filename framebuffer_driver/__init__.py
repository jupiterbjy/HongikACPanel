"""
Pygame Framebuffer driver primarily intended for Raspberry Pi B+

Primarily intended for weak devices like 1B+ where even mere x server is too heavy.

Uses trio to await for extra stability & safety.
"""

from driver import *
