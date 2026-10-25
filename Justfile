# The installed game (version 1.02): KRONDOR.EXE, krondor.rmf, krondor.001, startup.gam
game := "./game"
# DOSBox or DOSBox-X executable for `just play`
dosbox := env("DOSBOX", "dosbox-x")

# Create virtual environment
venv:
	uv venv --python 3.13 ./.venv

# Extract resources of the game to data/extracted (for manual export/import)
extract:
	mkdir -p ./data/original
	cp {{game}}/krondor.rmf {{game}}/krondor.001 ./data/original/
	uv run baktt resources extract ./data/original/krondor.rmf ./data/extracted/

# Export everything to translate: tables (xlsx for the translation system, csv for tests), images with text
export-all out="./translation" format="xlsx":
	uv run baktt export-all {{game}} {{out}} --format {{format}}

# Build the translated game: tables, fonts and images from data/ (see data/README.md) -> data/krondor-ru.zip
patch-game:
	rm -f ./data/krondor.zip
	mkdir -p ./data/build && rm -rf ./data/build/krondor && cp -R {{game}} ./data/build/krondor
	cd ./data/build && zip -qr ../krondor.zip krondor
	rm -rf ./data/build
	uv run baktt patch-game ./data/krondor.zip ./data/krondor-ru.zip

# Unpack the translated game to data/krondor-ru and run it in DOSBox
play: patch-game
	rm -rf ./data/krondor-ru && mkdir -p ./data/krondor-ru
	unzip -q ./data/krondor-ru.zip -d ./data/krondor-ru
	{{dosbox}} -c "mount c ./data/krondor-ru/krondor" -c "c:" -c "KRONDOR.EXE" -c "exit"

# Run the font editor
font-editor:
	uv run baktt gui font-editor

# Format and lint the code
lint:
	uvx ruff format src
	uvx ruff check src
