

extract:
	cd ./tools && poetry run python3 resources.py extract ../data/original/krondor.rmf ../data/extracted/

.PHONY : extract


archive-modified:
	find ./data/modified -type f | xargs -I{} cp {} ./data/extracted/
	cd ./tools && poetry run python3 resources.py archive ../data/extracted/_resources.csv ../data/archived

.PHONY : archive

play-modified:	archive-modified
	cp ./data/archived/krondor.rmf ./data/archived/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak

play-original:
	cp ./data/original/krondor.rmf ./data/original/krondor.001 ./xbak/krondor/
	cd ./xbak && ./xbak

.PHONY : archive
