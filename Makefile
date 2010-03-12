all: check

.PHONY: check doc

check: doc

doc:: $(patsubst %.txt,%.html, $(wildcard doc/*.txt))

doc:: INSTALL.html README.html

%.html: %.txt
	rst2html $< $@
