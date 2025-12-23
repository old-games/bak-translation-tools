from pathlib import Path

import _filebuffer


class FileBuffer:
    def __init__(self, size: int) -> None:
        self._fb = _filebuffer.FileBuffer(size)

    def size(self) -> int:
        return self._fb.GetSize()

    def uint8(self) -> int:
        return self._fb.GetUint8()

    def put_uint8(self, v: int) -> None:
        self._fb.PutUint8(v)

    def uint16LE(self) -> int:
        return self._fb.GetUint16LE()

    def put_uint16LE(self, v: int) -> None:
        self._fb.PutUint16LE(v)

    def uint32LE(self) -> int:
        return self._fb.GetUint32LE()

    def put_uint32LE(self, v: int) -> None:
        self._fb.PutUint32LE(v)

    def string(self, length: int) -> str:
        return self.read(length).rstrip(b"\x00").decode("cp1251")

    def put_string(self, v: str, length: int) -> None:
        self.write(v.encode(encoding="cp1251"))
        self.write(bytes(0 for _ in range(length - len(v))))

    @classmethod
    def from_file(cls, path: Path) -> FileBuffer:
        bytes = path.read_bytes()
        fb = cls(len(bytes))
        for b in bytes:
            fb.put_uint8(b)
        fb.seek(0)
        return fb

    def to_file(self, path: Path) -> None:
        offset = self.tell()
        self.seek(0)
        path.write_bytes(self.read())
        self.seek(offset)

    def seek(self, offset: int) -> None:
        self._fb.Seek(offset)

    def read(self, size: int | None = None) -> bytes:
        if size is None:
            size = self._fb.GetBytesLeft()
        assert size is not None
        return bytes(self.uint8() for _ in range(size))

    def skip(self, size: int) -> None:
        self._fb.Skip(size)

    def write(self, value: bytes) -> None:
        for b in value:
            self.put_uint8(b)

    def tell(self) -> int:
        return self._fb.GetBytesDone()

    def at_end(self) -> bool:
        return self._fb.AtEnd()

    def decompressRLE(self, uncompressed_size: int) -> FileBuffer:
        fb = FileBuffer(uncompressed_size)
        self._fb.DecompressRLE(fb._fb)
        return fb

    def compressRLE(self) -> tuple[int, FileBuffer]:
        current = self.tell()
        self.seek(0)
        uncompressed_size = self.size()
        temp = FileBuffer(uncompressed_size)
        compressed_size = self._fb.CompressRLE(temp._fb)
        self.seek(current)
        fb = FileBuffer(compressed_size)
        fb.write(temp.read(compressed_size))
        fb.seek(0)
        return compressed_size, fb

    def decompressLZW(self, uncompressed_size: int) -> FileBuffer:
        fb = FileBuffer(uncompressed_size)
        self._fb.DecompressLZW(fb._fb)
        return fb

    def decompressLZSS(self, uncompressed_size: int) -> FileBuffer:
        fb = FileBuffer(uncompressed_size)
        self._fb.DecompressLZSS(fb._fb)
        return fb
