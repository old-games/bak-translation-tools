# Create virtual environment
venv:
	uv venv --python 3.14 ./.venv

# Extract resources from krondor.rmf
extract:
	uv run baktt resources extract ./data/original/krondor.rmf ./data/extracted/

# Archive modified resourcess
archive-modified:
	uv run baktt resources archive-modified ./data/original/krondor.rmf ./data/modified/ ./data/archived/

# Import book data
import-book:
	uv run baktt book import ./data/extracted ./data/modified ./data/BOK.csv

# Play game with modified resources
play-modified: archive-modified
	cp ./data/archived/krondor.rmf ./data/archived/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak

# Play game with original resources
play-original:
	cp ./data/original/krondor.rmf ./data/original/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak

# Patch game zip file
patch-game:
    uv run baktt patch-game ./data/krondor.zip ./data/krondor-patched.zip
