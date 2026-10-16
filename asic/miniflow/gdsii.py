"""Stream writer/reader for GDSII.

Writing GDS is the point where a flow stops being a drawing and starts being a
tape-out artefact, so the writer emits the real binary format (BOUNDARY,
PATH, SREF, TEXT, STRUCTURE, ENDELIB, units) rather than a JSON approximation.
The reader exists so the sign-off steps - and the test suite - verify the file
that was actually produced instead of the in-memory database.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

# record types
HEADER = 0x00
BGNLIB = 0x01
LIBNAME = 0x02
UNITS = 0x03
ENDLIB = 0x04
BGNSTR = 0x05
STRNAME = 0x06
ENDSTR = 0x07
BOUNDARY = 0x08
PATH = 0x09
SREF = 0x0A
TEXT = 0x0C
LAYER = 0x0D
DATATYPE = 0x0E
WIDTH = 0x0F
XY = 0x10
ENDEL = 0x11
SNAME = 0x12
TEXTTYPE = 0x16
PRESENTATION = 0x17
STRING = 0x19
STRANS = 0x1A
MAG = 0x1B
ANGLE = 0x1C

DB_UNIT = 0.001          # user units (um) per database unit


def _record(record_type: int, payload: bytes = b"") -> bytes:
    """One GDSII record: uint16 length (including the header), uint16 type, data.

    Getting this order wrong is the classic GDS writing mistake - the length
    comes first - and the reader below is strict about it so that a malformed
    file fails loudly instead of being read as garbage.
    """
    return struct.pack(">HH", len(payload) + 4, record_type) + payload


def _i2(value: int) -> bytes:
    return struct.pack(">h", value)


def _i4(value: int) -> bytes:
    return struct.pack(">l", value)


def _db(x: float, y: float) -> bytes:
    return _i4(int(round(x / DB_UNIT))) + _i4(int(round(y / DB_UNIT)))


def _name(value: str) -> bytes:
    data = value.encode("ascii", "replace")
    if len(data) % 2:
        data += b"\0"
    return data


def rect(layer: int, x0: float, y0: float, x1: float, y1: float) -> bytes:
    """A filled boundary (rectangle) on one layer."""
    xy = _db(x0, y0) + _db(x1, y0) + _db(x1, y1) + _db(x0, y1) + _db(x0, y0)
    return (
        _record(BOUNDARY)
        + _record(LAYER, _i2(layer))
        + _record(DATATYPE, _i2(0))
        + _record(XY, xy)
        + _record(ENDEL)
    )


def path(layer: int, x0: float, y0: float, x1: float, y1: float, width: float) -> bytes:
    """A wire segment with a width, used for routing runs."""
    xy = _db(x0, y0) + _db(x1, y1)
    return (
        _record(PATH)
        + _record(LAYER, _i2(layer))
        + _record(DATATYPE, _i2(0))
        + _record(WIDTH, _i4(int(round(width / DB_UNIT))))
        + _record(XY, xy)
        + _record(ENDEL)
    )


def text(layer: int, x: float, y: float, string: str) -> bytes:
    return (
        _record(TEXT)
        + _record(LAYER, _i2(layer))
        + _record(TEXTTYPE, _i2(0))
        + _record(PRESENTATION, struct.pack(">H", 5))
        + _record(XY, _db(x, y))
        + _record(STRING, _name(string))
        + _record(ENDEL)
    )


def sref(cell: str, x: float, y: float) -> bytes:
    """A cell reference (instance) at an absolute position."""
    return (
        _record(SREF)
        + _record(SNAME, _name(cell))
        + _record(STRANS, _i2(0))
        + _record(MAG, struct.pack(">d", 1.0))
        + _record(ANGLE, struct.pack(">d", 0.0))
        + _record(XY, _db(x, y))
        + _record(ENDEL)
    )


def _structure(name: str, body: bytes) -> bytes:
    """A GDS structure: BGNSTR, name, elements, ENDSTR."""
    now = struct.pack(">12h", *([2026, 10, 15, 12, 0, 0] * 2))
    return (
        _record(BGNSTR, now)
        + _record(STRNAME, _name(name))
        + body
        + _record(ENDSTR)
    )


@dataclass
class Library:
    """In-memory GDS library: cell structures plus the top-level layout."""

    name: str = "PNP_MINIFLOW"
    cells: dict[str, list[bytes]] = field(default_factory=dict)
    top: list[bytes] = field(default_factory=list)


def write_gds(path: str | Path, library: Library) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = struct.pack(">12h", *([2026, 10, 15, 12, 0, 0] * 2))
    body = _record(HEADER, _i2(600))
    body += _record(BGNLIB, now)
    body += _record(LIBNAME, _name(library.name))
    # UNITS carries two doubles: the size of the database unit in *user* units
    # and the size of the user unit in metres.  For a 1 nm database unit and
    # micron user units that is 0.001 and 1e-6 - the conventional pair, and the
    # pair every GDS reader expects.
    body += _record(UNITS, struct.pack(">d", DB_UNIT) + struct.pack(">d", 1e-6))
    for cell_name, elements in library.cells.items():
        body += _structure(cell_name, b"".join(elements))
    body += _structure(f"{library.name}_TOP", b"".join(library.top))
    body += _record(ENDLIB)
    path.write_bytes(body)
    return path


def read_gds_summary(path: str | Path) -> dict:
    """Read back the structure names and element counts of a GDS file.

    A reader is kept next to the writer on purpose: sign-off should never trust
    the object that produced the file, only the file.
    """
    data = Path(path).read_bytes()
    offset = 0
    structures: dict[str, int] = {}
    units = None
    current = None
    while offset + 4 <= len(data):
        size, rec = struct.unpack(">HH", data[offset:offset + 4])
        if size < 4 or offset + size > len(data):
            raise ValueError(f"malformed GDS record at offset {offset}")
        payload = data[offset + 4:offset + size]
        if rec == STRNAME:
            name = payload.decode("ascii", "replace").rstrip("\0")
            current = name
            structures.setdefault(name, 0)
        elif rec in (BOUNDARY, PATH, SREF, TEXT):
            if current:
                structures[current] += 1
        elif rec == UNITS:
            db_in_user, user_in_m = struct.unpack(">dd", payload)
            units = {
                "db_unit_user_units": db_in_user,
                "user_unit_m": user_in_m,
                "db_unit_m": db_in_user * user_in_m,
            }
        offset += size
    if offset != len(data):
        # trailing bytes mean a truncated or corrupted file; a reader that
        # silently accepts them would hide a broken tape-out artefact
        raise ValueError(f"{len(data) - offset} trailing bytes after the last record")
    return {"structures": structures, "units": units, "bytes": len(data)}
