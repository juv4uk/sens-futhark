FUTHARK ?= .tools/bin/futhark

.PHONY: bootstrap probe check smoke-opencl smoke-cuda

bootstrap:
	bash tools/install-futhark.sh

probe:
	bash tools/probe-gpu.sh

check:
	$(FUTHARK) check src/smoke.fut

smoke-opencl:
	FUTHARK=$(FUTHARK) bash tools/smoke-opencl.sh

smoke-cuda:
	FUTHARK=$(FUTHARK) bash tools/smoke-cuda.sh
