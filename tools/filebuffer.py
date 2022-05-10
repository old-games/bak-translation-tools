from io import BytesIO
from pathlib import Path
from typing import Optional


class FileBuffer:
    def __init__(self, data: bytes = b""):
        self.io = BytesIO(data)

    def uint8(self) -> int:
        return int.from_bytes(self.io.read(1), signed=False, byteorder="little")

    def put_uint8(self, v: int) -> None:
        self.io.write(v.to_bytes(1, signed=False, byteorder="little"))

    def uint16LE(self) -> int:
        return int.from_bytes(self.io.read(2), signed=False, byteorder="little")

    def put_uint16LE(self, v: int) -> None:
        self.io.write(v.to_bytes(2, signed=False, byteorder="little"))

    def uint32LE(self) -> int:
        return int.from_bytes(self.io.read(4), signed=False, byteorder="little")

    def put_uint32LE(self, v: int) -> None:
        self.io.write(v.to_bytes(4, signed=False, byteorder="little"))

    def string(self, length: int) -> str:
        chars = []
        for b in self.io.read(length):
            if not b:
                break
            chars.append(chr(b))
        return "".join(chars)

    def put_string(self, v: str, length: int) -> None:
        self.io.write(v.encode(encoding="cp1251"))
        self.io.write(bytearray([0] * (length - len(v))))

    @classmethod
    def from_file(cls, path: Path) -> "FileBuffer":
        fb = cls()
        fb.io.write(path.read_bytes())
        fb.io.seek(0)
        return fb

    def to_file(self, path: Path) -> None:
        offset = self.tell()
        self.seek(0)
        path.write_bytes(self.read())
        self.seek(offset)

    def seek(self, offset: int) -> None:
        self.io.seek(offset)

    def read(self, size: Optional[int] = None) -> bytes:
        return self.io.read(size)

    def skip(self, size: int) -> None:
        self.io.read(size)

    def write(self, value: bytes) -> None:
        self.io.write(value)

    def tell(self) -> int:
        return self.io.tell()
