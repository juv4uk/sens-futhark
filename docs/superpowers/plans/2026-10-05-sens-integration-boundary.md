# SENS fixture-boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Зробити `sens-futhark` українським, відтворюваним Guix-substrate та fail-closed consumer-ом versioned SENS witness bundle.

**Architecture:** Python importer перевіряє schema, provenance та SHA-256 до того, як fixture потрапляє до CPU/Futhark runner-ів. Backend зберігає тільки imported snapshot і manifest, не копіює domain table як semantic source. Make targets з'єднують import, CPU witness і вже-окремий parity runner; GPU є optional execution lane, не semantic admission.

**Tech Stack:** Python 3 standard library, CSV, SHA-256, GNU Make, Bash, Guix manifests, Futhark 0.27.1 (optional GPU capability).

**Spec:** `docs/superpowers/specs/2026-10-05-sens-integration-boundary-design.md`

## Global Constraints

- `juv4uk/sens` володіє semantic contract, admitted domains та canonical fixture source.
- Bundle містить `schema`, source repository, source commit, contract version, payload SHA-256 і vectors.
- Unknown/stale/malformed provenance, digest mismatch та duplicate identity — fail-closed до backend execution.
- D8 лишається research/fail-closed; physical carrier width не створює semantic admission.
- README і Guix documentation — українською; `LICENSE` — дослівний канонічний текст ВОЛЬНОСТІ без дописів.
- CUDA/OpenCL availability не є semantic success; live GPU parity не заявляється без фактичного backend witness.
- `host/parity.py` належить issue #18; не копіювати його до #7.

## Review Focus

- Payload з правильними rows, але зміненим байтом: Task 1 перевіряє SHA-256 mismatch.
- Bundle з валідним SHA-256, але unknown schema або contract: Task 1 відхиляє його до CSV copy.
- Дві однакові `(domain,bits)` rows: Task 1 відхиляє duplicate identity.
- Відсутній upstream bundle: Task 2 залишає live import blocked, а не підміняє його local CSV.
- Відсутній GPU/backend output: Task 4 повертає failure/blocked, не CPU↔GPU success.

## File Structure

| Path | Responsibility |
|---|---|
| `host/import_sens_fixture.py` | Parse and fail-closed verification of a supplied bundle; copies accepted payload and writes local provenance manifest. |
| `tests/test_import_sens_fixture.py` | Pure-Python focused tests for valid and rejected bundle variants. |
| `fixtures/imported/` | Gitignored runtime destination for imported upstream payloads; never an authority source. |
| `fixtures/example/` | Small synthetic protocol fixture for tests and documentation only, visibly non-canonical. |
| `Makefile` | Explicit `import-fixture`, `witness-cpu`, and parity orchestration targets. |
| `manifest.scm`, `guix/run`, `guix/README.uk.md` | Reproducible environment roles and thin Guix entrypoint. |
| `README.md`, `LICENSE`, `docs/integration-boundary.md` | Ukrainian public contract, licensing scope, and integration authority/provenance explanation. |

### Task 1: Fail-closed fixture-bundle importer

**Files:**
- Create: `host/import_sens_fixture.py`
- Create: `tests/test_import_sens_fixture.py`
- Create: `fixtures/example/manifest.json`
- Create: `fixtures/example/identity_vectors.csv`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: directory with `manifest.json` and manifest-named CSV payload.
- Produces: `python3 host/import_sens_fixture.py --source DIR --destination DIR`, exit 0 only after verification; destination contains `manifest.json` and payload.
- Used by: Task 4 Make target.

- [ ] **Step 1: Write failing tests for accepted synthetic bundle and each rejected provenance case**

Cover: valid copy; payload SHA-256 mismatch; schema other than `sens-fixture-bundle/1`; source repository other than `juv4uk/sens`; absent commit/contract/digest; duplicate `(domain,bits)`; malformed CSV header.

- [ ] **Step 2: Run the importer test module before implementation**

Run: `python3 -m unittest tests/test_import_sens_fixture.py -v`
Expected: FAIL because `host.import_sens_fixture` does not exist.

- [ ] **Step 3: Implement `import_bundle(source: Path, destination: Path) -> ImportResult`**

Use only `argparse`, `csv`, `hashlib`, `json`, `pathlib`, `shutil`, and `tempfile`. Validate all manifest fields and rows before atomically replacing destination. Require exact CSV header `domain,width,bits,exact_text`; reject duplicate `(domain,bits)` but do not independently allocate SENS domain semantics.

- [ ] **Step 4: Run focused importer tests**

Run: `python3 -m unittest tests/test_import_sens_fixture.py -v`
Expected: PASS; every malformed/stale case exits non-zero without destination update.

- [ ] **Step 5: Commit the importer slice**

```bash
git add host/import_sens_fixture.py tests/test_import_sens_fixture.py fixtures/example .gitignore
git commit -m "feat(#7): add fail-closed SENS fixture importer"
```

### Task 2: Make orchestration and honest blocked/live states

**Files:**
- Modify: `Makefile`
- Modify: `README.md`
- Create: `docs/integration-boundary.md`

**Interfaces:**
- Consumes: Task 1 importer and a caller-provided `SENS_FIXTURE_SOURCE` directory.
- Produces: `make import-fixture SENS_FIXTURE_SOURCE=/path`; `make witness-cpu`; `make witness-parity BACKEND_WITNESS=/path` after #18 lands.
- Depends on: issue #18/PR #20 for `host/parity.py`; if absent, parity target exits with explicit dependency message.

- [ ] **Step 1: Write failing command-level tests for missing source and missing parity runner**

Use a Python test or shell fixture that asserts `make import-fixture` without `SENS_FIXTURE_SOURCE` exits non-zero and names the missing variable; assert `make witness-parity` without `host/parity.py` exits non-zero and names #18.

- [ ] **Step 2: Run command-level tests before Makefile implementation**

Run: `python3 -m unittest tests/test_make_targets.py -v`
Expected: FAIL because target behavior is absent.

- [ ] **Step 3: Add explicit Make targets and integration document**

`import-fixture` calls only Task 1. `witness-cpu` consumes `fixtures/imported/identity_vectors.csv` and refuses if missing. `witness-parity` first confirms `host/parity.py` and `BACKEND_WITNESS`, then invokes CPU witness and parity runner. Document source manifest fields, source-SHA reporting, blocked condition until upstream `sens` publishes a bundle, and no GPU-parity claim.

- [ ] **Step 4: Run focused orchestration tests**

Run: `python3 -m unittest tests/test_make_targets.py -v`
Expected: PASS; unavailable dependencies are named failures, never silent fallback.

- [ ] **Step 5: Commit the orchestration slice**

```bash
git add Makefile README.md docs/integration-boundary.md tests/test_make_targets.py
git commit -m "feat(#7): add explicit SENS fixture witness path"
```

### Task 3: Ukrainian public surface, ВОЛЬНІСТЬ, and Guix roles

**Files:**
- Modify: `README.md`
- Create: `LICENSE`
- Create: `manifest.scm`
- Create: `guix/run`
- Create: `guix/README.uk.md`
- Test: `tests/test_repo_surface.py`

**Interfaces:**
- Consumes: canonical license text from `juv4uk/sens/LICENSE` without alteration.
- Produces: `./guix/run dev -- команда` and `./guix/run futhark -- команда` roles; no claim that the role exposes a GPU.

- [ ] **Step 1: Write repository-surface tests**

Assert byte equality of `LICENSE` and `sens/LICENSE`; assert README Ukrainian authority wording includes `sens` as semantic owner and names OpenCL as unavailable rather than working; assert `manifest.scm` declares Python, Bash, coreutils, Git and `nss-certs`; assert Guix documentation calls CUDA host-provided/optional.

- [ ] **Step 2: Run repository-surface tests before documentation/environment implementation**

Run: `python3 -m unittest tests/test_repo_surface.py -v`
Expected: FAIL because files and required wording do not yet exist.

- [ ] **Step 3: Implement the owned public and execution-substrate files**

Copy `LICENSE` byte-for-byte; explain scope only in README. Model `guix/run` after `sens/guix/run`, using the project manifest and explicit roles. Keep Futhark/CUDA as optional host capability and never encode SENS domains in Guix.

- [ ] **Step 4: Run surface tests and shell syntax check**

Run: `python3 -m unittest tests/test_repo_surface.py -v && bash -n guix/run`
Expected: PASS.

- [ ] **Step 5: Commit the public-surface slice**

```bash
git add README.md LICENSE manifest.scm guix tests/test_repo_surface.py
git commit -m "docs(#7): add Ukrainian Guix and license surface"
```

### Task 4: Integrated CPU witness evidence and conditional backend parity

**Files:**
- Modify: `tests/test_import_sens_fixture.py`
- Modify: `tests/test_make_targets.py`
- Modify: `README.md`
- Modify: `docs/integration-boundary.md`

**Interfaces:**
- Consumes: accepted imported bundle from Task 1 and `host/parity.py` once #18 merges.
- Produces: provenance-bearing CPU witness evidence; backend comparison only with explicit backend witness input.

- [ ] **Step 1: Add integration tests using only the synthetic fixture**

Assert import → CPU witness emits a stable digest and provenance. Assert `witness-parity` with a missing backend witness fails; when `host/parity.py` exists, use CPU output copied to a temporary backend witness for the identity-only comparison test.

- [ ] **Step 2: Run the integration tests before final target wiring**

Run: `python3 -m unittest tests/test_import_sens_fixture.py tests/test_make_targets.py -v`
Expected: FAIL until provenance and target wiring are complete.

- [ ] **Step 3: Wire provenance into emitted evidence without semantic reinterpretation**

Print source repository, source commit, contract version and payload digest before the CPU witness. Do not label a synthetic fixture or CPU self-comparison as GPU parity.

- [ ] **Step 4: Run proportionate verification**

Run: `python3 -m unittest discover -s tests -v && python3 host/cpu_witness.py --self-test && bash -n guix/run`
Expected: PASS. Run `make witness-parity` only if #18 is merged and no resource preflight blocks the small CPU command; do not launch Futhark/GPU benchmark or OpenCL probe in this task.

- [ ] **Step 5: Commit, push, and request review**

```bash
git add tests README.md docs Makefile host
git commit -m "test(#7): verify fixture provenance witness path"
timeout 45s git fetch origin
timeout 45s git push
```

Open a PR that says `Closes #7`, links `sens#3560`, distinguishes synthetic protocol proof from canonical live import, and records any unmerged #18 prerequisite.

## Plan Review

Spec coverage is complete: authority/provenance (Tasks 1–2), local public and Guix requirements (Task 3), and witness evidence (Task 4). The only intentionally external dependency is the upstream `sens` export; it is surfaced as BLOCKED rather than manufactured here. Interface names are consistent across tasks. The five Review Focus cases are each covered by Tasks 1, 2, and 4. The plan excludes benchmarks, primitive semantics, and GPU/OpenCL claims.
