import logging
from typing import Literal, Optional

from filebuffer import FileBuffer

COMPRESSION_LZW = 0
COMPRESSION_LZSS = 1
COMPRESSION_RLE = 2


Compression = Literal[0, 1, 2]


class DecompressionError(Exception):
    pass


def decompress(
    compressed: FileBuffer,
    compression: Compression,
    decompressed_size: Optional[int] = None,
) -> FileBuffer:
    if compression == COMPRESSION_RLE:
        return decompressRLE(compressed, decompressed_size)
    else:
        raise AssertionError()


def decompressRLE(
    compressed: FileBuffer, decompressed_size: Optional[int] = None
) -> FileBuffer:
    decompressed = FileBuffer()

    control = compressed.read(1)
    while control or (
        decompressed_size is not None and decompressed.tell() < decompressed_size
    ):
        control = ord(control)
        if control & 0x80:
            num_bytes = control & 0x7F
            value = compressed.read(1)
            decompressed.write(value * num_bytes)
        else:
            decompressed.write(compressed.read(control))

        control = compressed.read(1)

    if decompressed_size is not None and decompressed.tell() != decompressed_size:
        logging.error(
            f"Expected size: {decompressed_size}, actual size: {decompressed.tell()}"
        )
        # raise DecompressionError(
        #     f"Expected size: {decompressed_size}, actual size: {decompressed.tell()}"
        # )

    decompressed.seek(0)

    return decompressed
