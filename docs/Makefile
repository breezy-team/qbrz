.PHONY = html

all: html

# rst2html := python rst2html.py
RST2HTML := rst2html5.py --initial-header-level=2 --footnote-references=superscript --smart-quotes=yes -g -d -t

%.html: %.txt
	$(RST2HTML) $< $@

%.html: ../%.txt
	$(RST2HTML) $< $@

html: index.html gettext_usage.html make_release.html \
	slot-signal-mini-tutorial/slot-signal-mini-tutorial.html \
	exception_reporting.html
