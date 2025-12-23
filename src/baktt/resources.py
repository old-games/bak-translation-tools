#!/bin/env python3
import csv
import os
import shutil
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp

from cyclopts import App
from filebuffer import FileBuffer

app = App(name="resources", help="Operations on the resource archive")


RES_FILENAME_LEN = 13
RESOURCE_LIST_NAME = "_resources.csv"


def main() -> None:
    app()


@app.command(name="list")
def list_command(resource_map_path: Path) -> None:
    """List resources in the specified resource map file."""
    list_resources(resource_map_path)


@app.command(name="extract")
def extract_command(resource_map_path: Path, extract_to: Path) -> None:
    """Extract resources based on the specified resource map file."""
    extract_resources(resource_map_path, extract_to)


@app.command(name="archive")
def archive_command(resource_list_path: Path, save_to: Path) -> None:
    """Archive resources listed in the specified resources list file."""
    archive_resources(resource_list_path, save_to)


@app.command(name="archive-modified")
def archive_modified_command(
    resource_map_path: Path, modified_dir: Path, save_to: Path
) -> None:
    """Archive the modified resources."""
    archive_modified_resources(resource_map_path, modified_dir, save_to)


def list_resources(resource_map_path: Path) -> None:
    archive_name, resources = _load_resources(resource_map_path)
    print("Archive:", archive_name)
    for resource in resources:
        print(resource)


def extract_resources(resource_map_path: Path, extract_to: Path) -> None:
    extract_to.mkdir(parents=True, exist_ok=True)
    resource_list_path = extract_to / RESOURCE_LIST_NAME
    resource_map_name = resource_map_path.name

    with open(resource_list_path, "w") as resource_list_file:
        resource_list_writer = csv.writer(resource_list_file)
        resource_archive_name, resources = _load_resources(resource_map_path)
        resource_list_writer.writerow(
            (
                resource_map_name,
                resource_archive_name,
            )
        )
        for resource in resources:
            resource_path = extract_to / resource.name
            resource_path.write_bytes(resource.data)
            resource_list_writer.writerow((resource.name, str(resource.hashkey)))


def archive_resources(resource_list_path: Path, save_to: Path) -> None:
    if not resource_list_path.exists():
        raise ValueError(f"{resource_list_path} does not exist")

    resource_dir_path = resource_list_path.parent

    # Save `krondor.001`
    offsets_and_hashes: list[tuple[int, int]] = []
    resource_archive_size = 0
    with open(resource_list_path) as resource_list_file:
        resource_list_reader = csv.reader(resource_list_file)
        next(resource_list_reader)
        for resource_name, _hashkey in resource_list_reader:
            resource_path = resource_dir_path / resource_name
            if not resource_path.exists():
                raise ValueError(f"{resource_path} does not exist")
            resource_archive_size += RES_FILENAME_LEN
            resource_archive_size += 4  # resource size
            resource_archive_size += resource_path.stat().st_size

    resource_archive_buffer = FileBuffer(resource_archive_size)
    with open(resource_list_path) as resource_list_file:
        resource_list_reader = csv.reader(resource_list_file)
        resource_map_name, resource_archive_name = next(resource_list_reader)
        for resource_name, hashkey in resource_list_reader:
            resource_path = resource_dir_path / resource_name
            resource = Resource(
                name=resource_name,
                hashkey=int(hashkey),
                data=resource_path.read_bytes(),
            )
            offset = _save_resource_to_archive(resource_archive_buffer, resource)
            offsets_and_hashes.append((offset, int(hashkey)))
    save_to.mkdir(parents=True, exist_ok=True)
    resource_archive_buffer.to_file(save_to / resource_archive_name)

    # Save `krondor.rmf`
    resource_map_size = 4 + 2 + RES_FILENAME_LEN + 2 + 8 * len(offsets_and_hashes)
    resource_map_buffer = FileBuffer(resource_map_size)
    resource_map_buffer.put_uint32LE(1)
    resource_map_buffer.put_uint16LE(4)
    resource_map_buffer.put_string(resource_archive_name, RES_FILENAME_LEN)
    resource_map_buffer.put_uint16LE(len(offsets_and_hashes))
    for offset, hashnum in offsets_and_hashes:
        resource_map_buffer.put_uint32LE(hashnum)
        resource_map_buffer.put_uint32LE(offset)
    resource_map_buffer.to_file(save_to / resource_map_name)


def archive_modified_resources(
    resource_map_path: Path, modified_dir: Path, save_to: Path
) -> None:
    tmpdir = Path(mkdtemp())
    extract_resources(resource_map_path, tmpdir)
    for filename in os.listdir(modified_dir):
        shutil.copy(modified_dir / filename, tmpdir)
    archive_resources(tmpdir / "_resources.csv", save_to)
    shutil.rmtree(tmpdir)


@dataclass
class Resource:
    hashkey: int
    name: str
    data: bytes

    def __str__(self) -> str:
        return f"{self.name}\t{len(self.data)} bytes"


def _load_resources(resource_map_path: Path) -> tuple[str, Iterable[Resource]]:
    rmf = FileBuffer.from_file(resource_map_path)
    if rmf.uint32LE() != 1 or rmf.uint16LE() != 4:
        raise ValueError("Data corruption")

    resource_archive_filename = rmf.string(RES_FILENAME_LEN)
    num_resources = rmf.uint16LE()

    resources_archive_path = resource_map_path.parent / resource_archive_filename
    if not resources_archive_path.exists():
        raise ValueError(f"{resource_archive_filename} is missing")

    rf = FileBuffer.from_file(resources_archive_path)

    def iter_resources() -> Generator[Resource]:
        for _ in range(num_resources):
            hashkey = rmf.uint32LE()
            offset = rmf.uint32LE()
            rf.seek(offset)
            yield _load_resource(rf, offset, hashkey)

    return resource_archive_filename, iter_resources()


def _load_resource(rf: FileBuffer, offset: int, hashkey: int) -> Resource:
    rf.seek(offset)
    name = rf.string(RES_FILENAME_LEN)
    size = rf.uint32LE()
    data = rf.read(size)
    return Resource(
        hashkey=hashkey,
        name=name,
        data=data,
    )


def _save_resource_to_archive(rf: FileBuffer, res: Resource) -> int:
    offset = rf.tell()
    rf.put_string(res.name, RES_FILENAME_LEN)
    rf.put_uint32LE(len(res.data))
    rf.write(res.data)
    return offset


if __name__ == "__main__":
    main()
