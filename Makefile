FUTHARK ?= .tools/bin/futhark

.PHONY: bootstrap probe check check-identity test-identity-cpu test-identity-cuda smoke-opencl smoke-cuda

bootstrap:
	bash tools/install-futhark.sh

probe:
	bash tools/probe-gpu.sh

check:
	$(FUTHARK) check src/smoke.fut

check-identity:
	$(FUTHARK) check -w futhark/identity_witness.fut

test-identity-cpu:
	$(FUTHARK) test --backend=c futhark/identity_witness.fut

test-identity-cuda:
	$(FUTHARK) test --backend=cuda futhark/identity_witness.fut

smoke-opencl:
	FUTHARK=$(FUTHARK) bash tools/smoke-opencl.sh

smoke-cuda:
	FUTHARK=$(FUTHARK) bash tools/smoke-cuda.sh
