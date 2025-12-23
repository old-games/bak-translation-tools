import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, NamedTuple

from cyclopts import App
from filebuffer import FileBuffer
from PIL import Image as PILImage
from PIL import ImageDraw

app = App(name="images", help="Operations on the image files")


def main() -> None:
    app()


@app.command(name="copy_bmx")
def copy_bmx_command(src_path: Path, dest_path: Path) -> None:
    """Copy a BMX file."""
    copy_bmx_resource(src_path, dest_path)


@app.command(name="display_palette")
def display_palette_command(src_path: Path) -> None:
    """Display a palette."""
    display_palette(src_path)


@app.command(name="palette_to_png")
def palette_to_png_command(src_path: Path, dest_path: Path) -> None:
    """Save a palette to a PNG file."""
    palette_to_png(src_path, dest_path)


@app.command(name="scx_to_png")
def scx_to_png_command(scx_path: Path, dest_dir: Path) -> None:
    """Save SCX to a PNG file."""
    scx_to_png(scx_path, dest_dir)


@app.command(name="all_scx_to_png")
def all_scx_to_png_command(src_dir: Path, dest_dir: Path) -> None:
    """Convert all SCX in a dir to PNG files."""
    all_scx_to_png(src_dir, dest_dir)


@app.command(name="bmx_to_png")
def bmx_to_png_command(bmx_path: Path, dest_dir: Path) -> None:
    """Save BMX to a PNG file."""
    bmx_to_png(bmx_path, dest_dir, guess_palette=True)


@app.command(name="all_bmx_to_png")
def all_bmx_to_png_command(src_dir: Path, dest_dir: Path) -> None:
    """Convert all BMX in a dir to PNG files."""
    all_bmx_to_png(src_dir, dest_dir)


@dataclass
class Image:
    FLAG_XYSWAPPED = 0x20
    FLAG_UNKNOWN = 0x40
    FLAG_COMPRESSED = 0x80

    width: int
    height: int
    flags: int
    hires_locol: bool
    pixels: list[int]

    @property
    def size(self) -> int:
        return self.width * self.height

    def to_png(self, path: Path, palette: Palette) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        img = PILImage.new("RGB", (self.width, self.height))
        for x in range(self.width):
            for y in range(self.height):
                pixel = self.pixels[x + self.width * y]
                color = palette.colors[pixel]
                img.putpixel((x, y), color)
        img.save(path)

    @classmethod
    def from_buf(
        cls,
        buf: FileBuffer,
        width: int,
        height: int,
        flags: int = 0,
        hires_locol: bool = False,
    ) -> Image:
        if flags & cls.FLAG_COMPRESSED:
            buf = buf.decompressRLE(width * height)

        if flags & cls.FLAG_XYSWAPPED:
            pixels = [0] * width * height
            for x in range(width):
                for y in range(height):
                    pixels[x + width * y] = buf.uint8()
        else:
            if hires_locol:
                pixels = []
                for _y in range(height):
                    for _x in range(width // 2):
                        c = buf.uint8()
                        pixels.append((c & 0xF0) >> 4)
                        pixels.append(c & 0x0F)
            else:
                pixels = [buf.uint8() for _ in range(width * height)]

        assert len(pixels) == width * height

        return Image(
            width=width,
            height=height,
            flags=flags,
            hires_locol=hires_locol,
            pixels=pixels,
        )

    def to_buf(self, buf: FileBuffer) -> None:
        raise NotImplementedError


@dataclass
class BMXResource:
    # noinspection SpellCheckingInspection
    PALETTES: ClassVar[dict[str, str]] = {
        "ACT001.BMX": "ACT001.PAL",
        "ACT001A.BMX": "ACT001.PAL",
        "ACT002.BMX": "ACT002.PAL",
        "ACT002A.BMX": "ACT002.PAL",
        "ACT003.BMX": "ACT003.PAL",
        "ACT003A.BMX": "ACT003.PAL",
        "ACT004.BMX": "ACT004.PAL",
        "ACT004A.BMX": "ACT004.PAL",
        "ACT005.BMX": "ACT005.PAL",
        "ACT005A.BMX": "ACT005.PAL",
        "ACT006.BMX": "ACT006.PAL",
        "ACT006A.BMX": "ACT006.PAL",
        "ACT007.BMX": "ACT007.PAL",
        "ACT008.BMX": "ACT008.PAL",
        "ACT009A.BMX": "ACT009.PAL",
        "ACT010.BMX": "ACT010.PAL",
        "ACT011.BMX": "ACT011.PAL",
        "ACT012A.BMX": "ACT012.PAL",
        "ACT013.BMX": "ACT013.PAL",
        "ACT014.BMX": "ACT014.PAL",
        "ACT015.BMX": "ACT015.PAL",
        "ACT016.BMX": "ACT016.PAL",
        "ACT017.BMX": "ACT017.PAL",
        "ACT018A.BMX": "ACT018.PAL",
        "ACT019.BMX": "ACT019.PAL",
        "ACT020.BMX": "ACT020.PAL",
        "ACT021.BMX": "ACT021.PAL",
        "ACT022.BMX": "ACT022.PAL",
        "ACT023.BMX": "ACT023.PAL",
        "ACT024.BMX": "ACT024.PAL",
        "ACT025.BMX": "ACT025.PAL",
        "ACT026.BMX": "ACT026.PAL",
        "ACT027.BMX": "ACT027.PAL",
        "ACT028.BMX": "ACT028.PAL",
        "ACT029.BMX": "ACT029.PAL",
        "ACT030A.BMX": "ACT030.PAL",
        "ACT031.BMX": "ACT031.PAL",
        "ACT032.BMX": "ACT032.PAL",
        "ACT033.BMX": "ACT033.PAL",
        "ACT034.BMX": "ACT034.PAL",
        "ACT035.BMX": "ACT035.PAL",
        "ACT036.BMX": "ACT036.PAL",
        "ACT037.BMX": "ACT037.PAL",
        "ACT038.BMX": "ACT038.PAL",
        "ACT039.BMX": "ACT039.PAL",
        "ACT040.BMX": "ACT040.PAL",
        "ACT041.BMX": "ACT041.PAL",
        "ACT042.BMX": "ACT042.PAL",
        "ACT043.BMX": "ACT043.PAL",
        "ACT044.BMX": "ACT044.PAL",
        "ACT045.BMX": "ACT045.PAL",
        "ACT046.BMX": "ACT046.PAL",
        "ACT047.BMX": "ACT047.PAL",
        "ACT048.BMX": "ACT048.PAL",
        "ACT049.BMX": "ACT049.PAL",
        "ACT050.BMX": "ACT050.PAL",
        "ACT051.BMX": "ACT051.PAL",
        "ACT052.BMX": "ACT052.PAL",
        "ACT053.BMX": "ACT053.PAL",
        "AIR1.BMX": "Z01.PAL",
        "AIR2.BMX": "Z01.PAL",
        "AIR3.BMX": "Z01.PAL",
        "BICONS1.BMX": "OPTIONS.PAL",
        "BICONS2.BMX": "OPTIONS.PAL",
        "BOOK.BMX": "Z01.PAL",
        "BOOM.BMX": "Z01.PAL",
        "BRK1.BMX": "Z01.PAL",
        "BRK2.BMX": "Z01.PAL",
        "BRK3.BMX": "Z01.PAL",
        "BSY1.BMX": "Z01.PAL",
        "BSY2.BMX": "Z01.PAL",
        "BSY3.BMX": "Z01.PAL",
        "C11A1.BMX": "C11A.PAL",
        "C11A2.BMX": "C11A.PAL",
        "C11B.BMX": "C11B.PAL",
        "C12A.BMX": "C12A.PAL",
        "C12A_BAK.BMX": "C12A.PAL",
        "C12A_MAG.BMX": "C12A.PAL",
        "C12A_PUG.BMX": "C12A.PAL",
        "C12B_ARC.BMX": "C12B.PAL",
        "C12B_GOR.BMX": "C12B.PAL",
        "C12B_SRL.BMX": "C12A.PAL",
        "C21A.BMX": "C21.PAL",
        "C21A_BAK.BMX": "C21.PAL",
        "C21B1.BMX": "C21.PAL",
        "C21C.BMX": "C21.PAL",
        "C21_MAK.BMX": "C21.PAL",
        "C22.BMX": "C22.PAL",
        "C31A_BAK.BMX": "C31.PAL",
        "C31A_JIM.BMX": "C31.PAL",
        "C31A_PYR.BMX": "C31.PAL",
        "C31B_BAK.BMX": "C31.PAL",
        "C31B_GOR.BMX": "C31.PAL",
        "C32A_BAK.BMX": "C32A.PAL",
        "C32A_WLK.BMX": "C32A.PAL",
        "C32B_BAK.BMX": "C32B.PAL",
        "C41A_BAK.BMX": "C41A.PAL",
        "C41A_DEL.BMX": "C41A.PAL",
        "C41A_DOR.BMX": "C41A.PAL",
        "C41A_OWD.BMX": "C41A.PAL",
        "C41A_OWO.BMX": "C41A.PAL",
        "C41B_BAK.BMX": "C41B.PAL",
        "C41B_DEL.BMX": "C41B.PAL",
        "C41B_GOR.BMX": "C41B.PAL",
        "C42_PNTR.BMX": "C42.PAL",
        "C42_WNDW.BMX": "C42.PAL",
        "C51A_BAK.BMX": "C51.PAL",
        "C51A_MOR.BMX": "C51.PAL",
        "C51A_PTR.BMX": "C51.PAL",
        "C51B_BAK.BMX": "C51.PAL",
        "C51B_JNL.BMX": "C51.PAL",
        "C52A_BAK.BMX": "C52A.PAL",
        "C52A_JIM.BMX": "C52A.PAL",
        "C52A_MOR.BMX": "C52A.PAL",
        "C52B_ARU.BMX": "C52B.PAL",
        "C52B_BAK.BMX": "C52B.PAL",
        "C52B_JIM.BMX": "C52B.PAL",
        "C61A_BAK.BMX": "C61A.PAL",
        "C61A_CHS.BMX": "C61A.PAL",
        "C61A_GAT.BMX": "C61A.PAL",
        "C61A_MAK.BMX": "C61A.PAL",
        "C61A_TLK.BMX": "C61B.PAL",
        "C61B_BAK.BMX": "C61B.PAL",
        "C61B_MAK.BMX": "C61B.PAL",
        "C61C_BAK.BMX": "C61C.PAL",
        "C61C_PUG.BMX": "C61C.PAL",
        "C61C_TLK.BMX": "C61C.PAL",
        "C61D_BAK.BMX": "C61D.PAL",
        "C61D_BLA.BMX": "C61D.PAL",
        "C61D_MAC.BMX": "C61D.PAL",
        "C62A.BMX": "C62A.PAL",
        "C62B_BG1.BMX": "C62B.PAL",
        "C62B_BG2.BMX": "C62B.PAL",
        "C62B_BOK.BMX": "C62B.PAL",
        "C62B_BRU.BMX": "C62B.PAL",
        "C62B_QUE.BMX": "C62B.PAL",
        "C62B_TOM.BMX": "C62B.PAL",
        "C71A_AR1.BMX": "C71A.PAL",
        "C71A_AR2.BMX": "C71A.PAL",
        "C71A_BG.BMX": "C71A.PAL",
        "C71B.BMX": "C71B.PAL",
        "C71B_BG.BMX": "C71B.PAL",
        "C71C.BMX": "C71C.PAL",
        "C71C_BG.BMX": "C71C.PAL",
        "C72A_BG.BMX": "C72A.PAL",
        "C72A_LEA.BMX": "C72A.PAL",
        "C72A_PAT.BMX": "C72A.PAL",
        "C72B_BG.BMX": "C72B.PAL",
        "C72B_HLD.BMX": "C72B.PAL",
        "C72B_PAT.BMX": "C72B.PAL",
        "C72C_BG.BMX": "C72C.PAL",
        "C72C_PTY.BMX": "C72C.PAL",
        "C81.BMX": "C81.PAL",
        "C82A.BMX": "C82A.PAL",
        "C82A_CEL.BMX": "C82A.PAL",
        "C82B.BMX": "C82B.PAL",
        "C82B_GOR.BMX": "C82B.PAL",
        "C82C.BMX": "C82C.PAL",
        "C82C_GAM.BMX": "C82C.PAL",
        "C91_BG.BMX": "C91.PAL",
        "C91_GOR.BMX": "C91_GOR.PAL",
        "C91_JIM.BMX": "C91_JIM.PAL",
        "C91_PRTY.BMX": "C91.PAL",
        "C91_PUG.BMX": "C91_PUG.PAL",
        "C92.BMX": "C92.PAL",
        "C93A.BMX": "C93A.PAL",
        "C93A_1.BMX": "C93A.PAL",
        "C93B.BMX": "C93B.PAL",
        "C93B_1.BMX": "C93B.PAL",
        "C93B_2.BMX": "C93B.PAL",
        "C93C.BMX": "C93C.PAL",
        "C93C_1A.BMX": "C93C.PAL",
        "C93C_1B.BMX": "C93C.PAL",
        "C93C_1C.BMX": "C93C.PAL",
        "C93D.BMX": "C93D.PAL",
        "C93D_1.BMX": "C93D.PAL",
        "CAST.BMX": "Z01.PAL",
        "CASTFACE.BMX": "Z01.PAL",
        "CHAPTER.BMX": "CHAPTER.PAL",
        "COMPASS.BMX": "Z01.PAL",
        "DOG1.BMX": "Z01.PAL",
        "DOG2.BMX": "Z01.PAL",
        "DOG3.BMX": "Z01.PAL",
        "DRE1.BMX": "Z01.PAL",
        "DRE2.BMX": "Z01.PAL",
        "DRE3.BMX": "Z01.PAL",
        "ENCAMP.BMX": "Z01.PAL",
        "FIGS.BMX": "Z01.PAL",
        "FMAP_ICN.BMX": "Z01.PAL",
        "GNT1.BMX": "Z01.PAL",
        "GNT2.BMX": "Z01.PAL",
        "GNT3.BMX": "Z01.PAL",
        "GOB1.BMX": "Z01.PAL",
        "GOB2.BMX": "Z01.PAL",
        "GOB3.BMX": "Z01.PAL",
        "GOR1.BMX": "Z01.PAL",
        "GOR2.BMX": "Z01.PAL",
        "GOR3.BMX": "Z01.PAL",
        "G_ARMANG.BMX": "G_ARMANG.PAL",
        "G_BKBAR1.BMX": "G_BKBAR1.PAL",
        "G_BKBAR2.BMX": "G_BKBAR2.PAL",
        "G_BKCAVE.BMX": "G_BKCAVE.PAL",
        "G_BKCULL.BMX": "G_BKCULL.PAL",
        "G_BKDRAG.BMX": "G_BKDRAG.PAL",
        "G_BKEORT.BMX": "G_BKEORT.PAL",
        "G_BKFALL.BMX": "G_BKFALL.PAL",
        "G_BKFRST.BMX": "G_BKFRST.PAL",
        "G_BKLIBR.BMX": "G_BKLIBR.PAL",
        "G_BKSEWR.BMX": "G_BKSEWR.PAL",
        "G_BKSTAT.BMX": "G_BKSTAT.PAL",
        "G_BKSTON.BMX": "G_BKSTON.PAL",
        "G_BKTHRO.BMX": "G_BKTHRO.PAL",
        "G_BKTMPL.BMX": "G_BKTMPL.PAL",
        "G_BKTUNL.BMX": "G_BKTUNL.PAL",
        "G_BKWOOD.BMX": "G_BKWOOD.PAL",
        "G_CAVALL.BMX": "G_CAVALL.PAL",
        "G_CHEAM.BMX": "G_CHEAM.PAL",
        "G_HICAST.BMX": "G_HICAST.PAL",
        "G_KRONDO.BMX": "G_KRONDO.PAL",
        "G_LAMUT.BMX": "G_LAMUT.PAL",
        "G_LAMUT2.BMX": "G_LAMUT2.PAL",
        "G_MALACS.BMX": "G_MALACS.PAL",
        "G_NORTHW.BMX": "G_NORTHW.PAL",
        "G_ROMNEY.BMX": "G_ROMNEY.PAL",
        "G_SARSAR.BMX": "G_SARSAR.PAL",
        "G_SARTH.BMX": "G_SARTH.PAL",
        "G_SETHAN.BMX": "G_SETHAN.PAL",
        "HEADS.BMX": "Z01.PAL",
        "INT_BOOK.BMX": "INT_TITL.PAL",
        "INT_BUNT.BMX": "INT_DYN.PAL",
        "INT_DYN.BMX": "INT_DYN.PAL",
        "INT_LGHT.BMX": "INT_DYN.PAL",
        "INT_TITL.BMX": "INT_TITL.PAL",
        "INVLOCK.BMX": "INVENTOR.PAL",
        "INVMISC.BMX": "Z01.PAL",
        "INVSHP1.BMX": "INVENTOR.PAL",
        "INVSHP2.BMX": "INVENTOR.PAL",
        "JIM1.BMX": "Z01.PAL",
        "JIM2.BMX": "Z01.PAL",
        "JIM3.BMX": "Z01.PAL",
        "LOK1.BMX": "Z01.PAL",
        "LOK2.BMX": "Z01.PAL",
        "LOK3.BMX": "Z01.PAL",
        "MAK1.BMX": "Z01.PAL",
        "MAK2.BMX": "Z01.PAL",
        "MAK3.BMX": "Z01.PAL",
        "MAPICONS.BMX": "OPTIONS.PAL",
        "MOR1.BMX": "Z01.PAL",
        "MOR2.BMX": "Z01.PAL",
        "MOR3.BMX": "Z01.PAL",
        "MOR4.BMX": "Z01.PAL",
        "NHK1.BMX": "Z01.PAL",
        "NHK2.BMX": "Z01.PAL",
        "NHK3.BMX": "Z01.PAL",
        "NTH1.BMX": "Z01.PAL",
        "NTH2.BMX": "Z01.PAL",
        "NTH3.BMX": "Z01.PAL",
        "OGR1.BMX": "Z01.PAL",
        "OGR2.BMX": "Z01.PAL",
        "OGR3.BMX": "Z01.PAL",
        "OGR4.BMX": "Z01.PAL",
        "OWN1.BMX": "Z01.PAL",
        "OWN2.BMX": "Z01.PAL",
        "OWN3.BMX": "Z01.PAL",
        "PAI1.BMX": "Z01.PAL",
        "PAI2.BMX": "Z01.PAL",
        "PAI3.BMX": "Z01.PAL",
        "PAN1.BMX": "Z01.PAL",
        "PAN2.BMX": "Z01.PAL",
        "PAN3.BMX": "Z01.PAL",
        "PARCH.BMX": "Z01.PAL",
        "PAT.BMX": "Z01.PAL",
        "PAT1.BMX": "Z01.PAL",
        "PAT2.BMX": "Z01.PAL",
        "PAT3.BMX": "Z01.PAL",
        "POINTER.BMX": "OPTIONS.PAL",
        "POINTERG.BMX": "OPTIONS.PAL",
        "PUG1.BMX": "Z01.PAL",
        "PUG2.BMX": "Z01.PAL",
        "PUG3.BMX": "Z01.PAL",
        "PUZZLE.BMX": "PUZZLE.PAL",
        "QUE1.BMX": "Z01.PAL",
        "QUE2.BMX": "Z01.PAL",
        "QUE3.BMX": "Z01.PAL",
        "ROG1.BMX": "Z01.PAL",
        "ROG2.BMX": "Z01.PAL",
        "ROG3.BMX": "Z01.PAL",
        "ROG4.BMX": "Z01.PAL",
        "RUS1.BMX": "Z01.PAL",
        "RUS2.BMX": "Z01.PAL",
        "RUS3.BMX": "Z01.PAL",
        "SCP1.BMX": "Z01.PAL",
        "SCP2.BMX": "Z01.PAL",
        "SCP3.BMX": "Z01.PAL",
        "SER1.BMX": "Z01.PAL",
        "SER2.BMX": "Z01.PAL",
        "SER3.BMX": "Z01.PAL",
        "SHA1.BMX": "Z01.PAL",
        "SHA2.BMX": "Z01.PAL",
        "SHA3.BMX": "Z01.PAL",
        "SHOP1.BMX": "SHOP1.PAL",
        "SHOP1ARM.BMX": "SHOP1.PAL",
        "SHOP1BAK.BMX": "SHOP1.PAL",
        "SHOP2.BMX": "SHOP2.PAL",
        "SHOP2ARM.BMX": "SHOP2.PAL",
        "SHOP2BAK.BMX": "SHOP2.PAL",
        "SHOP3.BMX": "SHOP3.PAL",
        "SHOP3ARM.BMX": "SHOP3.PAL",
        "SHOP3BAK.BMX": "SHOP3.PAL",
        "SHOP4.BMX": "SHOP4.PAL",
        "SPI1.BMX": "Z01.PAL",
        "SPI2.BMX": "Z01.PAL",
        "SPI3.BMX": "Z01.PAL",
        "SPL1.BMX": "Z01.PAL",
        "SPL2.BMX": "Z01.PAL",
        "SPL3.BMX": "Z01.PAL",
        "TELEPORT.BMX": "TELEPORT.PAL",
        "TEMPLE.BMX": "TEMPLE.PAL",
        "TRO1.BMX": "Z01.PAL",
        "TRO2.BMX": "Z01.PAL",
        "TRO3.BMX": "Z01.PAL",
        "TVRN1.BMX": "TVRN1.PAL",
        "TVRN1BAK.BMX": "TVRN1.PAL",
        "TVRN1PPL.BMX": "TVRN1.PAL",
        "TVRN2.BMX": "TVRN2.PAL",
        "TVRN2BAK.BMX": "TVRN2.PAL",
        "TVRN2PPL.BMX": "TVRN2.PAL",
        "TVRN3.BMX": "TVRN3.PAL",
        "TVRN3BAK.BMX": "TVRN3.PAL",
        "TVRN3PPL.BMX": "TVRN3.PAL",
        "TVRN4.BMX": "TVRN4.PAL",
        "TVRN4BAK.BMX": "TVRN4.PAL",
        "TVRN4PPL.BMX": "TVRN4.PAL",
        "TVRN5.BMX": "TVRN5.PAL",
        "TVRN5BAK.BMX": "TVRN5.PAL",
        "TVRN5PPL.BMX": "TVRN5.PAL",
        "WIT1.BMX": "Z01.PAL",
        "WIT2.BMX": "Z01.PAL",
        "WIT3.BMX": "Z01.PAL",
        "WYV1.BMX": "Z01.PAL",
        "WYV2.BMX": "Z01.PAL",
        "WYV3.BMX": "Z01.PAL",
        "Z01H.BMX": "Z01.PAL",
        "Z01SLOT0.BMX": "Z01.PAL",
        "Z01SLOT1.BMX": "Z01.PAL",
        "Z01SLOT2.BMX": "Z01.PAL",
        "Z01SLOT3.BMX": "Z01.PAL",
        "Z01SLOT4.BMX": "Z01.PAL",
        "Z02H.BMX": "Z02.PAL",
        "Z02SLOT0.BMX": "Z02.PAL",
        "Z02SLOT1.BMX": "Z02.PAL",
        "Z02SLOT2.BMX": "Z02.PAL",
        "Z02SLOT3.BMX": "Z02.PAL",
        "Z02SLOT4.BMX": "Z02.PAL",
        "Z03H.BMX": "Z03.PAL",
        "Z03SLOT0.BMX": "Z03.PAL",
        "Z03SLOT1.BMX": "Z03.PAL",
        "Z03SLOT2.BMX": "Z03.PAL",
        "Z03SLOT3.BMX": "Z03.PAL",
        "Z03SLOT4.BMX": "Z03.PAL",
        "Z04H.BMX": "Z04.PAL",
        "Z04SLOT0.BMX": "Z04.PAL",
        "Z04SLOT1.BMX": "Z04.PAL",
        "Z04SLOT2.BMX": "Z04.PAL",
        "Z04SLOT3.BMX": "Z04.PAL",
        "Z04SLOT4.BMX": "Z04.PAL",
        "Z05H.BMX": "Z05.PAL",
        "Z05SLOT0.BMX": "Z05.PAL",
        "Z05SLOT1.BMX": "Z05.PAL",
        "Z05SLOT2.BMX": "Z05.PAL",
        "Z05SLOT3.BMX": "Z05.PAL",
        "Z05SLOT4.BMX": "Z05.PAL",
        "Z06H.BMX": "Z06.PAL",
        "Z06SLOT0.BMX": "Z06.PAL",
        "Z06SLOT1.BMX": "Z06.PAL",
        "Z06SLOT2.BMX": "Z06.PAL",
        "Z06SLOT3.BMX": "Z06.PAL",
        "Z06SLOT4.BMX": "Z06.PAL",
        "Z07H.BMX": "Z07.PAL",
        "Z07SLOT0.BMX": "Z07.PAL",
        "Z07SLOT1.BMX": "Z07.PAL",
        "Z07SLOT2.BMX": "Z07.PAL",
        "Z07SLOT3.BMX": "Z07.PAL",
        "Z07SLOT4.BMX": "Z07.PAL",
        "Z08SLOT0.BMX": "Z08.PAL",
        "Z08SLOT1.BMX": "Z08.PAL",
        "Z08SLOT2.BMX": "Z08.PAL",
        "Z08SLOT3.BMX": "Z08.PAL",
        "Z08SLOT4.BMX": "Z08.PAL",
        "Z09SLOT0.BMX": "Z09.PAL",
        "Z09SLOT1.BMX": "Z09.PAL",
        "Z09SLOT2.BMX": "Z09.PAL",
        "Z09SLOT3.BMX": "Z09.PAL",
        "Z09SLOT4.BMX": "Z09.PAL",
        "Z10SLOT0.BMX": "Z10.PAL",
        "Z10SLOT1.BMX": "Z10.PAL",
        "Z10SLOT2.BMX": "Z10.PAL",
        "Z10SLOT3.BMX": "Z10.PAL",
        "Z10SLOT4.BMX": "Z10.PAL",
        "Z10SLOT5.BMX": "Z10.PAL",
        "Z11SLOT0.BMX": "Z11.PAL",
        "Z11SLOT1.BMX": "Z11.PAL",
        "Z11SLOT2.BMX": "Z11.PAL",
        "Z11SLOT3.BMX": "Z11.PAL",
        "Z11SLOT4.BMX": "Z11.PAL",
        "Z11SLOT5.BMX": "Z11.PAL",
        "Z11SLOT6.BMX": "Z11.PAL",
        "Z12SLOT0.BMX": "Z12.PAL",
        "Z12SLOT1.BMX": "Z12.PAL",
        "Z12SLOT2.BMX": "Z12.PAL",
        "Z12SLOT3.BMX": "Z12.PAL",
        "Z12SLOT4.BMX": "Z12.PAL",
        "Z12SLOT5.BMX": "Z12.PAL",
        "Z12SLOT6.BMX": "Z12.PAL",
    }

    COMPRESSION_LZW = 0
    COMPRESSION_LZSS = 1
    COMPRESSION_RLE = 2

    compression: int
    images: list[Image]
    skips: list[bytes]

    def to_file(self, path: Path) -> None:
        uncompressed_size = sum(i.size for i in self.images)
        uncompressed_buf = FileBuffer(uncompressed_size)
        for image in self.images:
            image.to_buf(uncompressed_buf)

        if self.compression == self.COMPRESSION_LZW:
            raise NotImplementedError("LZW compression is not supported yet")
        elif self.compression == self.COMPRESSION_LZSS:
            raise NotImplementedError("LZSS compression is not supported yet")
        elif self.compression == self.COMPRESSION_RLE:
            compressed_size, compressed_buf = uncompressed_buf.compressRLE()
        else:
            raise AssertionError()

        size = (
            2
            + 2  # data validation
            + 2  # compression
            + len(self.skips[0])  # num images
            + 4  # first skip
            + 2 * 4 * len(self.images)  # uncompressed size
            + compressed_size  # image attributes
        )
        if self.compression == self.COMPRESSION_LZW:
            size += 5

        buf = FileBuffer(size)
        buf.put_uint16LE(0x1066)
        buf.put_uint16LE(self.compression)
        buf.put_uint16LE(len(self.images))
        buf.write(self.skips[0])
        buf.put_uint32LE(uncompressed_size)

        for image in self.images:
            buf.put_uint16LE(image.size)
            buf.put_uint16LE(image.flags)
            buf.put_uint16LE(image.width)
            buf.put_uint16LE(image.height)

        if self.compression == self.COMPRESSION_LZW:
            buf.put_uint8(0x02)
            buf.put_uint32LE(uncompressed_size)

        buf.write(compressed_buf.read())

        buf.to_file(path)

    @classmethod
    def from_file(cls, path: Path) -> BMXResource:
        buf = FileBuffer.from_file(path)
        if buf.uint16LE() != 0x1066:
            raise ValueError("Data corruption")
        compression = buf.uint16LE()
        num_images = buf.uint16LE()
        skips: list[bytes] = [buf.read(2)]
        uncompressed_size = buf.uint32LE()

        image_attrs = []
        for _ in range(num_images):
            data_size = buf.uint16LE()
            flags = buf.uint16LE()
            width = buf.uint16LE()
            height = buf.uint16LE()
            image_attrs.append((data_size, flags, width, height))

        if compression == cls.COMPRESSION_LZW:
            if buf.uint8() != 0x02:
                raise ValueError("Data corruption")
            if buf.uint32LE() != uncompressed_size:
                raise ValueError("Data corruption")
            decompressed_buf = buf.decompressLZW(uncompressed_size)
        elif compression == cls.COMPRESSION_LZSS:
            decompressed_buf = buf.decompressLZSS(uncompressed_size)
        elif compression == cls.COMPRESSION_RLE:
            decompressed_buf = buf.decompressRLE(uncompressed_size)
        else:
            raise ValueError(f"Unknown compression type: {compression}")

        images: list[Image] = []
        for data_size, flags, width, height in image_attrs:
            image_buf = FileBuffer(data_size)
            image_buf.write(decompressed_buf.read(data_size))
            image_buf.seek(0)
            images.append(Image.from_buf(image_buf, width, height, flags=flags))

        return BMXResource(
            compression=compression,
            images=images,
            skips=skips,
        )


class UnknownPaletteError(Exception):
    pass


@dataclass
class SCXResource:
    SCREEN_WIDTH = 320
    SCREEN_HEIGHT = 200
    BOOK_SCREEN_WIDTH = 640
    BOOK_SCREEN_HEIGHT = 350

    # noinspection SpellCheckingInspection
    PALETTES: ClassVar[dict[str, str]] = {
        "BLANK.SCX": "CREDITS.PAL",
        "BOOK.SCX": "BOOK.PAL",
        "C11.SCX": "C11A.PAL",
        "C42.SCX": "C42.PAL",
        "CAST.SCX": "OPTIONS.PAL",
        "CFRAME.SCX": "OPTIONS.PAL",
        "CHAPTER.SCX": "CHAPTER.PAL",
        "CONT2.SCX": "CONTENTS.PAL",
        "CONTENTS.SCX": "CONTENTS.PAL",
        "CREDITS.SCX": "CREDITS.PAL",
        "DIALOG.SCX": "BOOK.PAL",
        "ENCAMP.SCX": "OPTIONS.PAL",
        "FCOMBAT.SCX": "OPTIONS.PAL",
        "FRAME.SCX": "OPTIONS.PAL",
        "FULLMAP.SCX": "FULLMAP.PAL",
        "INT_BORD.SCX": "INT_TITL.PAL",
        "INT_MENU.SCX": "INT_MENU.PAL",
        "INVENTOR.SCX": "INVENTOR.PAL",
        "OPTIONS0.SCX": "OPTIONS.PAL",
        "OPTIONS1.SCX": "OPTIONS.PAL",
        "OPTIONS2.SCX": "OPTIONS.PAL",
        "PUZZLE.SCX": "PUZZLE.PAL",
        "RIFTMAP.SCX": "Z01.PAL",
        "Z01L.SCX": "Z01.PAL",
        "Z02L.SCX": "Z02.PAL",
        "Z03L.SCX": "Z03.PAL",
        "Z04L.SCX": "Z04.PAL",
        "Z05L.SCX": "Z05.PAL",
        "Z06L.SCX": "Z06.PAL",
        "Z07L.SCX": "Z07.PAL",
        "Z08L.SCX": "Z08.PAL",
        "Z09L.SCX": "Z09.PAL",
        "Z10L.SCX": "Z10.PAL",
        "Z11L.SCX": "Z11.PAL",
        "Z12L.SCX": "Z12.PAL",
    }

    image: Image

    @classmethod
    def from_file(cls, path: Path) -> SCXResource:
        buf = FileBuffer.from_file(path)
        is_book_screen = False
        if buf.uint16LE() != 0x27B6:
            is_book_screen = True
            buf.seek(0)
        if buf.uint8() != 0x02:
            raise ValueError("Data corruption")
        decompressed_size = buf.uint32LE()
        decompressed_buf = buf.decompressLZW(decompressed_size)
        if is_book_screen:
            width = cls.BOOK_SCREEN_WIDTH
            height = cls.BOOK_SCREEN_HEIGHT
            hires_locol = True
        else:
            width = cls.SCREEN_WIDTH
            height = cls.SCREEN_HEIGHT
            hires_locol = False
        image = Image.from_buf(decompressed_buf, width, height, hires_locol=hires_locol)
        return SCXResource(image=image)

    def to_file(self, path: Path) -> None:
        raise NotImplementedError


class Color(NamedTuple):
    r: int
    g: int
    b: int
    a: int

    @property
    def hex(self) -> str:
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"


@dataclass
class Palette:
    name: str

    colors: list[Color]

    TAG_PAL = 0x3A4C4150
    TAG_VGA = 0x3A414756

    _palettes_by_name: ClassVar[dict[str, Palette] | None] = None

    @classmethod
    def from_file(cls, path: Path) -> Palette:
        buf = FileBuffer.from_file(path)
        if buf.uint32LE() != cls.TAG_PAL:
            raise ValueError("Data corruption")
        buf.skip(4)
        if buf.uint32LE() != cls.TAG_VGA:
            raise ValueError("Data corruption")
        buf.skip(4)
        palette = Palette(colors=[], name=path.name)
        while not buf.at_end():
            palette.colors.append(
                Color(
                    r=buf.uint8() << 2,
                    g=buf.uint8() << 2,
                    b=buf.uint8() << 2,
                    a=0,
                )
            )
        return palette

    @classmethod
    def get_by_name(cls, src_dir: Path, name: str) -> Palette:
        if cls._palettes_by_name is None:
            cls._palettes_by_name = {}
            for filename in os.listdir(src_dir):
                filename: str
                if not filename.endswith(".PAL"):
                    continue
                palette = cls.from_file(src_dir / filename)
                cls._palettes_by_name[palette.name] = palette
        return cls._palettes_by_name[name]

    def to_png(self, dest_path: Path) -> None:
        rect_size = 32
        img = PILImage.new("RGB", (rect_size * 16, rect_size * 16))
        draw = ImageDraw.Draw(img)
        for i, color in enumerate(self.colors):
            row = i // 16
            col = i % 16
            x = col * rect_size
            y = row * rect_size
            draw.rectangle((x, y, x + rect_size, y + rect_size), fill=color.hex)
        img.save(dest_path)


def copy_bmx_resource(src_path: Path, dest_path: Path) -> None:
    bmx_resource = BMXResource.from_file(src_path)
    print(bmx_resource)
    bmx_resource.to_file(dest_path)


def display_palette(path: Path) -> None:
    palette = Palette.from_file(path)
    for i, color in enumerate(palette.colors):
        print(f"{i}:\t{color.hex}")


def palette_to_png(src_path: Path, dest_path: Path) -> None:
    palette = Palette.from_file(src_path)
    palette.to_png(dest_path)


def scx_to_png(
    scx_path: Path,
    dest_dir: Path,
    pal_name: str | None = None,
    png_name: str | None = None,
) -> None:
    scx_filename = scx_path.name
    dest_dir.mkdir(parents=True, exist_ok=True)
    pal_name = pal_name or SCXResource.PALETTES.get(scx_filename)
    if pal_name is None:
        print(f"Could not determine the palette file for {scx_filename}")
        if input("Do you want to guess the palette? ") in ("yes", "y"):
            for filename in sorted(os.listdir(scx_path.parent)):
                filename: str
                if not filename.endswith(".PAL"):
                    continue
                pal_name = filename
                scx_to_png(
                    scx_path,
                    dest_dir / "guessed_palette" / scx_filename,
                    pal_name=pal_name,
                    png_name=f"{pal_name}.png",
                )
        return
    scx_resource = SCXResource.from_file(scx_path)
    palette = Palette.get_by_name(scx_path.parent, pal_name)
    png_path = dest_dir / (png_name or f"{scx_filename}.png")
    scx_resource.image.to_png(png_path, palette)


def all_scx_to_png(src_dir: Path, dest_dir: Path) -> None:
    assert src_dir.is_dir()
    for filename in sorted(os.listdir(src_dir)):
        filename: str
        if not filename.endswith(".SCX"):
            continue
        scx_path = src_dir / filename
        scx_to_png(scx_path, dest_dir)


def bmx_to_png(
    bmx_path: Path,
    dest_dir: Path,
    pal_name: str | None = None,
    guess_palette: bool = False,
) -> None:
    bmx_filename = bmx_path.name
    pal_name = pal_name or BMXResource.PALETTES.get(bmx_filename)
    if pal_name is None:
        print(f"Could not determine the palette file for {bmx_filename}")
        if guess_palette and input("Do you want to guess the palette? ") in (
            "yes",
            "y",
        ):
            for filename in sorted(os.listdir(bmx_path.parent)):
                filename: str
                if not filename.endswith(".PAL"):
                    continue
                pal_name = filename
                bmx_to_png(
                    bmx_path,
                    dest_dir / "guessed_palette" / bmx_filename / pal_name,
                    pal_name=pal_name,
                )
        return
    try:
        bmx_resource = BMXResource.from_file(bmx_path)
    except Exception as e:
        print(bmx_filename, e)
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    palette = Palette.get_by_name(bmx_path.parent, pal_name)
    for i, image in enumerate(bmx_resource.images):
        png_path = dest_dir / f"{bmx_filename}_{i}.png"
        image.to_png(png_path, palette)


def all_bmx_to_png(src_dir: Path, dest_dir: Path) -> None:
    assert src_dir.is_dir()
    for filename in sorted(os.listdir(src_dir)):
        filename: str
        if not filename.endswith(".BMX"):
            continue
        bmx_path = src_dir / filename
        bmx_to_png(bmx_path, dest_dir)


if __name__ == "__main__":
    main()
