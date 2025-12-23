from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import find_packages, setup

__version__ = "0.0.1"

ext_modules = [
    Pybind11Extension(
        "_filebuffer",
        ["src/Exception.cpp", "src/FileBuffer.cpp", "src/pybind.cpp"],
    ),
]

setup(
    name="filebuffer",
    version=__version__,
    author="Andrey Fedoseev",
    author_email="andrey@andreyfedoseev.com",
    description="filebuffer",
    long_description="",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.6",
    packages=find_packages("src"),
    package_dir={"": "src"},
)
