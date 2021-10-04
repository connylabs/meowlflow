SRC := $(shell find . -type f -name '*.py')

README.md: $(SRC)
	perl -i -n0e 'while(/(.*?)^(\[replace\]:\s*#\s*\(([^\n]*)\)\n```[^\n]*\n).*?^(```)$$(.*?)/smg){print "$$1$$2"; open (FILE, "<", "$$3") or die "could not open the log file $$3\n";print <FILE>;close (FILE); print "$$4\n$$5"}' $@
