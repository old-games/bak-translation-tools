from filebuffer import FileBuffer


def test_rle():

    buf = FileBuffer(10)
    buf.put_string("aaaaa12345", 10)
    buf.seek(0)

    _, compressed_buf = buf.compressRLE()

    uncompressed = compressed_buf.decompressRLE(10)
    assert uncompressed.string(10) == "aaaaa12345"
