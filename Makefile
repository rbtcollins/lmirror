all: check

.PHONY: check doc check-xml test.xml

.testrepository:
	testr init

check: doc .testrepository
	testr run

doc:: $(patsubst %.txt,%.html, $(wildcard doc/*.txt))

doc:: INSTALL.html README.html

%.html: %.txt
	rst2html $< $@

check-xml: doc test.xml

test.xml:
	python -m subunit.run lmirror.tests.test_suite | subunit2junitxml -o test.xml -f | subunit2pyunit
