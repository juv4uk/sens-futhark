FUTHARK ?= .tools/bin/futhark

.PHONY: bootstrap probe check smoke-opencl

bootstrap:
	bash tools/install-futhark.sh

probe:
	bash tools/probe-gpu.sh

check:
	$(FUTHARK) check src/smoke.fut

smoke-opencl:
	FUTHARK=$(FUTHARK) bash tools/smoke-opencl.sh
