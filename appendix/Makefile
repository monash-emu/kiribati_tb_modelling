# --- Config ---
TEX     := appendix.tex
PDF     := appendix.pdf
LOG     := appendix.log
TAB     := tab-params.tex
TABSENS := tab-screening-sens.tex
PARAM   := parameterisation.tex
SCRIPT  := scripts/build_tab_params.py
DATA    := ../data/parameters.xlsx
FIGS    := $(wildcard figures/*)

# Default target
all: $(PDF)

# Generate the LaTeX tables from Excel using pixi's Python
$(TAB) $(TABSENS): $(DATA) $(SCRIPT)
	@echo ">>> Generating $(TAB) and $(TABSENS) (using pixi environment)"
	pixi run python $(SCRIPT) --xlsx $(DATA) --out $(TAB) --out-sens $(TABSENS) --caption "Model parameters" --label tab-params

# Build the PDF using pixi's environment (assuming latexmk is available system-wide)
$(PDF): $(TEX) $(TAB) $(TABSENS) $(PARAM) $(FIGS)
	@echo ">>> Building PDF (via pixi environment)"
	pixi run latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX)

# Clean auxiliary files (still via pixi so latexmk is the same binary)
clean:
	pixi run latexmk -C
	@rm -f $(TAB) $(TABSENS)

# Full rebuild from scratch, failing on anything latexmk only warns about
check:
	@$(MAKE) clean
	@$(MAKE) all
	@test -f $(PDF) || { echo "FAIL: $(PDF) was not produced"; exit 1; }
	@grep -aq 'Output written on $(PDF)' $(LOG) || { echo "FAIL: no PDF output recorded in $(LOG)"; exit 1; }
	@if grep -aq 'undefined' $(LOG); then echo "FAIL: unresolved references:"; grep -a 'undefined' $(LOG); exit 1; fi
	@if grep -aq 'not found' $(LOG); then echo "FAIL: missing input file:"; grep -a 'not found' $(LOG); exit 1; fi
	@echo "OK: $$(grep -a 'Output written on' $(LOG) | tail -1)"

.PHONY: all clean check