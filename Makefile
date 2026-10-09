FUTHARK ?= .tools/bin/futhark
CUDA_ENV ?= tools/cuda-env.sh
SENS_FIXTURE_SOURCE ?=
FIXTURE_DESTINATION ?= fixtures/imported
CPU_WITNESS ?= host/cpu_witness.py
PARITY_RUNNER ?= host/parity.py
BACKEND_WITNESS ?=
ARGS ?=

# GPU-only policy (#79): automatic CI runs only the CUDA targets below.
# Targets marked 'reference-only' execute the C backend on the host; they are an
# internal semantic reference and must never be treated as a release/CI path.
.PHONY: bootstrap probe probe-cuda-json check check-identity test-identity-cpu test-identity-cuda check-packed-domain test-packed-domain test-packed-domain-cuda check-compiler-backend test-compiler-backend-cuda benchmark-compiler-slice benchmark-compiler-slice-cuda smoke-opencl smoke-cuda import-fixture witness-cpu witness-parity sens-fetch sens-cli sens-cli-parity verify-sens-pin release-evidence

bootstrap:
	bash tools/install-futhark.sh

probe:
	bash tools/probe-gpu.sh

probe-cuda-json:
	bash "$(CUDA_ENV)" json

check:
	$(FUTHARK) check src/smoke.fut

check-identity:
	$(FUTHARK) check -w futhark/identity_witness.fut

# reference-only: local semantic reference, NOT a CI lane (GPU-only policy #79).
test-identity-cpu:
	$(FUTHARK) test --backend=c futhark/identity_witness.fut

# Fail-closed: cuda-env.sh run refuses (exit 4) when the CUDA host is unavailable.
test-identity-cuda:
	bash "$(CUDA_ENV)" run "$(FUTHARK)" test --backend=cuda futhark/identity_witness.fut

export-selector-law: sens-fetch
	python3 tools/export-selector-law.py

check-selector-law:
	$(FUTHARK) check -w futhark/selector_law.fut

check-work-queue:
	$(FUTHARK) check -w futhark/work_queue.fut

check-packed-domain:
	$(FUTHARK) check -w futhark/packed_domain.fut
	python3 tools/validate-packed-domain-vectors.py

# reference-only (mixed): C backend as a reference, then CUDA; not a CI lane (#79).
test-packed-domain:
	$(FUTHARK) test --backend=c futhark/packed_domain.fut
	bash "$(CUDA_ENV)" run "$(FUTHARK)" test --backend=cuda futhark/packed_domain.fut

# Automatic GPU-only CI must use this target so it can never execute backend=c.
test-packed-domain-cuda:
	bash "$(CUDA_ENV)" run "$(FUTHARK)" test --backend=cuda futhark/packed_domain.fut

check-compiler-backend: sens-fetch
	python3 tests/test_compiler_backend_v1.py
	python3 tests/test_sens_compiler_request.py
	python3 tests/test_sens_compiler_artifact.py
	python3 tests/test_sens_whole_program_artifact.py
	$(FUTHARK) check -w futhark/compiler_structural.fut

# No CPU fallback: GPU admission is an input fact and CUDA is the only execution backend.
test-compiler-backend-cuda: sens-fetch
	python3 tests/test_compiler_backend_v1.py
	python3 tests/test_sens_compiler_request.py
	python3 tests/test_sens_compiler_artifact.py
	python3 tests/test_sens_whole_program_artifact.py
	bash "$(CUDA_ENV)" run "$(FUTHARK)" test --backend=cuda futhark/compiler_structural.fut

# Manual research lane for #113: real SENS producer -> compiler legality scan -> CPU/CUDA evidence.
# This is intentionally separate from the fast compiler CI gate.
benchmark-compiler-slice: sens-fetch
	bash "$(CUDA_ENV)" run python3 bench/compiler_slice.py --futhark "$(FUTHARK)"

# Automatic/local GPU lane: do not spend host CPU on the large C reference batches.
# The SENS producer bootstrap remains CPU control-plane work; all measured batches run on CUDA.
benchmark-compiler-slice-cuda: sens-fetch
	bash "$(CUDA_ENV)" run python3 bench/compiler_slice.py --cuda-only --futhark "$(FUTHARK)"

smoke-opencl:
	FUTHARK=$(FUTHARK) bash tools/smoke-opencl.sh

# Fail-closed: smoke-cuda.sh requires the CUDA host (cuda_env_require).
smoke-cuda:
	FUTHARK=$(FUTHARK) bash tools/smoke-cuda.sh

import-fixture:
	@test -n "$(SENS_FIXTURE_SOURCE)" || { echo "SENS_FIXTURE_SOURCE is required; no local fixture fallback exists." >&2; exit 2; }
	python3 host/import_sens_fixture.py --source "$(SENS_FIXTURE_SOURCE)" --destination "$(FIXTURE_DESTINATION)"

# reference-only: CPU witness over the imported fixture; NOT a CI lane (#79).
witness-cpu:
	@test -f "$(FIXTURE_DESTINATION)/identity_vectors.csv" || { echo "Imported fixture missing; run make import-fixture SENS_FIXTURE_SOURCE=/path/to/sens-bundle first." >&2; exit 2; }
	@python3 -c 'import json; m=json.load(open("$(FIXTURE_DESTINATION)/manifest.json", encoding="utf-8")); print("(provenance (source {}) (commit {}) (contract {}) (sha256 {}))".format(m["source_repository"], m["source_commit"], m["contract_version"], m["payload_sha256"]))'
	python3 "$(CPU_WITNESS)" --fixture "$(FIXTURE_DESTINATION)/identity_vectors.csv"

witness-parity:
	@test -f "$(PARITY_RUNNER)" || { echo "Parity runner missing (#18); backend equality cannot be claimed." >&2; exit 2; }
	@test -n "$(BACKEND_WITNESS)" || { echo "BACKEND_WITNESS is required; absent backend output is not GPU parity." >&2; exit 2; }
	@test -f "$(BACKEND_WITNESS)" || { echo "BACKEND_WITNESS does not exist: $(BACKEND_WITNESS)" >&2; exit 2; }
	@reference=$$(mktemp); trap 'rm -f "$$reference"' EXIT; python3 "$(CPU_WITNESS)" --fixture "$(FIXTURE_DESTINATION)/identity_vectors.csv" > "$$reference" && python3 "$(PARITY_RUNNER)" --reference "$$reference" --backend "$(BACKEND_WITNESS)"

verify-sens-pin:
	bash tools/verify-sens-source-pin.sh

sens-fetch:
	bash tools/fetch-sens-source.sh

sens-cli: sens-fetch
	bash tools/sens-cli.sh $(ARGS)

sens-cli-parity: sens-fetch
	bash tools/smoke-sens-cli-parity.sh

release-evidence:
	bash tools/release-evidence.sh
