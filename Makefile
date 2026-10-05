FUTHARK ?= .tools/bin/futhark
CUDA_ROOT ?= /usr/local/cuda-12.6
CUDA_TARGET ?= $(CUDA_ROOT)/targets/x86_64-linux
CUDA_DRIVER_LIB ?= /usr/lib/wsl/lib

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
	test -f "$(CUDA_TARGET)/include/cuda.h"
	CUDA_HOME="$(CUDA_ROOT)" CUDA_PATH="$(CUDA_ROOT)" \
	CPATH="$(CUDA_TARGET)/include$${CPATH:+:$$CPATH}" \
	LIBRARY_PATH="$(CUDA_DRIVER_LIB):$(CUDA_TARGET)/lib$${LIBRARY_PATH:+:$$LIBRARY_PATH}" \
	LD_LIBRARY_PATH="$(CUDA_DRIVER_LIB):$(CUDA_TARGET)/lib$${LD_LIBRARY_PATH:+:$$LD_LIBRARY_PATH}" \
	$(FUTHARK) test --backend=cuda futhark/identity_witness.fut

smoke-opencl:
	FUTHARK=$(FUTHARK) bash tools/smoke-opencl.sh

smoke-cuda:
	FUTHARK=$(FUTHARK) bash tools/smoke-cuda.sh
