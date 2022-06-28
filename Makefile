venv:
	python3 -m virtualenv ./tools/venv

.PHONY : venv


extract:
	./tools/venv/bin/python3 -m baktt.resources extract ./data/original/krondor.rmf ./data/extracted/

.PHONY : extract


archive-modified:
	./tools/venv/bin/python3 -m baktt.resources archive-modified ./data/original/krondor.rmf ./data/modified/ ./data/archived/

.PHONY : archive-modified

import-book:
	./tools/venv/bin/python3 -m baktt.book import ./data/extracted ./data/modified ./data/BOK.csv

.PHONY : import-book

play-modified:	archive-modified
	cp ./data/archived/krondor.rmf ./data/archived/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak

play-original:
	cp ./data/original/krondor.rmf ./data/original/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak
