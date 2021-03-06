all: check

.PHONY: check doc check-xml test.xml

.testrepository:
	testr init

check: doc .testrepository
	testr run --parallel

clean:
	-find -name '*.html' -exec rm -f {} \;
	-find -name '*.pyo' -exec rm -f {} \;
	-rm -rf .testrepository
	-rm -rf build
	-rm -rf dist

doc:: $(patsubst %.txt,%.html, $(wildcard doc/*.txt))

doc:: INSTALL.html README.html

%.html: %.txt
	rst2html $< $@

check-xml: doc test.xml

test.xml:
	python -m subunit.run l_mirror.tests.test_suite | subunit2junitxml -o test.xml -f | subunit2pyunit

install: check
	python ./setup.py install --prefix=$(DESTDIR)/usr
