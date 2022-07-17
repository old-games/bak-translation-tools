from filebuffer import FileBuffer


def test_rle():

    buf = FileBuffer(10)
    buf.write(b"aaaaa12345")
    buf.seek(0)

    _, compressed_buf = buf.compressRLE()

    uncompressed = compressed_buf.decompressRLE(10)
    assert uncompressed.read() == b"aaaaa12345"
