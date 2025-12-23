{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python 3.13 with tkinter support
    python313
    python313Packages.tkinter

    # Additional tools
    uv
    just
  ];
}
