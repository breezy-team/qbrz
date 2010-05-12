.PHONY = html

all: html

rst2html := python rst2html.py

%.html: %.txt
	$(rst2html) $< $@

%.html: ../%.txt
	$(rst2html) $< $@

html: index.html gettext_usage.html make_release.html \
	slot-signal-mini-tutorial/slot-signal-mini-tutorial.html \
	exception_reporting.html
