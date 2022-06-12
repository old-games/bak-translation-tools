

extract:
	cd ./tools && poetry run python3 resources.py extract ../data/original/krondor.rmf ../data/extracted/

.PHONY : extract


archive-modified:
	cd ./tools && poetry run python3 resources.py archive-modified ../data/original/krondor.rmf ../data/modified/ ../data/archived/

.PHONY : archive

play-modified:	archive-modified
	cp ./data/archived/krondor.rmf ./data/archived/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak

play-original:
	cp ./data/original/krondor.rmf ./data/original/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak

.PHONY : archive
