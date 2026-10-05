FUTHARK ?= .tools/bin/futhark
CUDA_ROOT ?= /usr/local/cuda-12.6
CUDA_TARGET ?= $(CUDA_ROOT)/targets/x86_64-linux

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
	test -f "$(CUDA_TARGET)/include/cuda.h" || { echo "cuda.h not found under $(CUDA_TARGET)/include" >&2; exit 4; }
	CPATH="$(CUDA_TARGET)/include$${CPATH:+:$$CPATH}" \
	LIBRARY_PATH="/usr/lib/wsl/lib:$(CUDA_TARGET)/lib$${LIBRARY_PATH:+:$$LIBRARY_PATH}" \
	LD_LIBRARY_PATH="/usr/lib/wsl/lib:$(CUDA_TARGET)/lib$${LD_LIBRARY_PATH:+:$$LD_LIBRARY_PATH}" \
	$(FUTHARK) test --backend=cuda futhark/identity_witness.fut

smoke-opencl:
	FUTHARK=$(FUTHARK) bash tools/smoke-opencl.sh

smoke-cuda:
	FUTHARK=$(FUTHARK) bash tools/smoke-cuda.sh
