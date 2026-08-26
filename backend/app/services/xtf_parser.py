"""
Lightweight XTF (eXtended Triton Format) navigation header parser.

Parses only the navigation fields from XTF binary files — no full sonar data decoding.
XTF is the standard format for side-scan sonar data from most survey-grade systems
(EdgeTech, Klein, Edgetech, Marine Sonic, etc.).

Reference: XTF File Format Specification (public domain).
This implementation reads only the file header and first ping header for nav data.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Optional

# XTF format identifier byte (0x7B = 123 decimal)
XTF_FORMAT_BYTE = 0x7B

# Known XTF header offsets (XTF v3.x standard)
# These are from the public XTF specification
_XTF_FILE_HDR_SIZE = 1024

# Navigation in the first XTFPINGHEADER after the file header
# Ping packet header fields (little-endian):
# Offset 0: MagicNumber (uint16) = 0xFACE
# Offset 12: SensorXcoordinate (double) = longitude
# Offset 20: SensorYcoordinate (double) = latitude
# Offset 28: SensorHeadingDegrees (float)
_PING_MAGIC = 0xFACE
_CHAN_HDR_SIZE = 64  # XTF channel info block size


def parse_xtf_navigation(filepath: str | Path) -> Optional[dict]:
    """
    Attempts to extract navigation fields from an XTF binary file.

    Reads the XTF file header to validate format, then reads the first
    ping packet header to extract latitude, longitude, and heading.

    Args:
        filepath: Path to the XTF file.

    Returns:
        dict with keys: latitude, longitude, heading (float), source ('xtf')
        Returns None if the file is not a valid XTF file or nav data is absent.
    """
    try:
        path = Path(filepath)
        if not path.is_file():
            return None

        file_size = path.stat().st_size
        if file_size < _XTF_FILE_HDR_SIZE + 64:
            return None

        with open(path, "rb") as f:
            file_header = f.read(_XTF_FILE_HDR_SIZE)

        # Validate XTF format byte
        if len(file_header) < 4 or file_header[0] != XTF_FORMAT_BYTE:
            return None

        # Read NumberOfSonarChannels from file header (offset 32, uint16)
        if len(file_header) >= 34:
            n_channels = struct.unpack_from("<H", file_header, 32)[0]
            n_channels = min(n_channels, 6)  # sanity cap
        else:
            n_channels = 0

        # First ping header starts after file header + channel headers
        ping_offset = _XTF_FILE_HDR_SIZE + n_channels * _CHAN_HDR_SIZE

        with open(path, "rb") as f:
            f.seek(ping_offset)
            ping_header = f.read(128)

        if len(ping_header) < 40:
            return None

        # Validate ping magic number (uint16 at offset 0)
        magic = struct.unpack_from("<H", ping_header, 0)[0]
        if magic != _PING_MAGIC:
            # Try next alignment
            return None

        # Extract longitude (double, offset 12), latitude (double, offset 20)
        lon = struct.unpack_from("<d", ping_header, 12)[0]
        lat = struct.unpack_from("<d", ping_header, 20)[0]

        # Extract heading (float, offset 28)
        heading = struct.unpack_from("<f", ping_header, 28)[0]

        # Validate coordinate ranges
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None
        if lat == 0.0 and lon == 0.0:
            return None  # Likely no fix

        result = {
            "latitude": round(float(lat), 8),
            "longitude": round(float(lon), 8),
            "source": "xtf",
        }
        if 0.0 <= heading <= 360.0:
            result["heading"] = round(float(heading), 2)

        return result

    except Exception:
        return None


def is_xtf_file(filepath: str | Path) -> bool:
    """Quick check: is this file an XTF binary?"""
    try:
        path = Path(filepath)
        if not path.is_file() or path.stat().st_size < 4:
            return False
        with open(path, "rb") as f:
            b = f.read(1)
        return len(b) == 1 and b[0] == XTF_FORMAT_BYTE
    except Exception:
        return False
