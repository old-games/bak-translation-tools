#include <pybind11/pybind11.h>
#include "FileBuffer.h"

namespace py = pybind11;

PYBIND11_MODULE(_filebuffer, m)
{
    py::class_<FileBuffer>(m, "FileBuffer")
        .def(py::init<const unsigned int>())
        .def("Seek", &FileBuffer::Seek)
        .def("Skip", &FileBuffer::Skip)
        .def("GetBytesDone", &FileBuffer::GetBytesDone)
        .def("GetBytesLeft", &FileBuffer::GetBytesLeft)
        .def("AtEnd", &FileBuffer::AtEnd)
        .def("GetSize", &FileBuffer::GetSize)

        .def("GetUint8", &FileBuffer::GetUint8)
        .def("GetUint16LE", &FileBuffer::GetUint16LE)
        .def("GetUint16BE", &FileBuffer::GetUint16BE)
        .def("GetUint32LE", &FileBuffer::GetUint32LE)
        .def("GetUint32BE", &FileBuffer::GetUint32BE)
        .def("GetSint8", &FileBuffer::GetSint8)
        .def("GetSint16LE", &FileBuffer::GetSint16LE)
        .def("GetSint16BE", &FileBuffer::GetSint16BE)
        .def("GetSint32LE", &FileBuffer::GetSint32LE)
        .def("GetSint32BE", &FileBuffer::GetSint32BE)

        .def("PutUint8", &FileBuffer::PutUint8)
        .def("PutUint16LE", &FileBuffer::PutUint16LE)
        .def("PutUint16BE", &FileBuffer::PutUint16BE)
        .def("PutUint32LE", &FileBuffer::PutUint32LE)
        .def("PutUint32BE", &FileBuffer::PutUint32BE)
        .def("PutSint8", &FileBuffer::PutSint8)
        .def("PutSint16LE", &FileBuffer::PutSint16LE)
        .def("PutSint16BE", &FileBuffer::PutSint16BE)
        .def("PutSint32LE", &FileBuffer::PutSint32LE)
        .def("PutSint32BE", &FileBuffer::PutSint32BE)

        .def("DecompressRLE", [](FileBuffer &b, FileBuffer &result)
             { b.DecompressRLE(&result); })
        .def("CompressRLE", [](FileBuffer &b, FileBuffer &result)
             { return b.CompressRLE(&result); })

        ;
}
