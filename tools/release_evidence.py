#!/usr/bin/env python3
"""Release only from a live, successful, GitHub-hosted CUDA job and its artifact.

A green workflow with a skipped CUDA job is NOT release evidence. Any supplied
run URL is verified against the live GitHub API; local artifacts are not trusted.
"""
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def gh(*args):
    result = subprocess.run(
        ["gh", *args], check=True, text=True, capture_output=True, timeout=120
    )
    return result.stdout


def gh_json(*args):
    return json.loads(gh(*args))


def validate_run(run, repo, sha, workflow_file, branch, run_id):
    require(run.get("id") == run_id, "RUN_ID_MISMATCH")
    require(run.get("head_sha") == sha, "RUN_SHA_MISMATCH")
    require(run.get("head_branch") == branch, "RUN_NOT_ON_RELEASE_BRANCH")
    require(run.get("event") in ("push", "workflow_dispatch"), "RUN_WRONG_EVENT")
    require(run.get("status") == "completed", "RUN_INCOMPLETE")
    require(run.get("conclusion") == "success", "RUN_NOT_SUCCESS")
    require(
        run.get("path") == ".github/workflows/" + workflow_file,
        "RUN_WRONG_WORKFLOW",
    )
    require(
        run.get("repository", {}).get("full_name") == repo,
        "RUN_WRONG_REPOSITORY",
    )
    require(
        run.get("html_url") == f"https://github.com/{repo}/actions/runs/{run_id}",
        "RUN_URL_MISMATCH",
    )


def validate_jobs(jobs):
    matching = [j for j in jobs if j.get("name") == "CUDA-only witness"]
    require(len(matching) == 1, "CUDA_JOB_MISSING_OR_DUPLICATED")
    job = matching[0]
    require(job.get("status") == "completed", "CUDA_JOB_INCOMPLETE")
    require(job.get("conclusion") == "success", "CUDA_SKIPPED_OR_FAILED")
    require(job.get("runner_group_name") == "GitHub Actions", "CUDA_RUNNER_NOT_GITHUB_OWNED")
    require(
        str(job.get("runner_name") or "").startswith("GitHub Actions "),
        "CUDA_RUNNER_NOT_GITHUB_OWNED",
    )
    require("ubuntu-24.04" in (job.get("labels") or []), "CUDA_RUNNER_LABEL_MISMATCH")
    # Job success must include execution of real hardware and parity steps.
    names = {
        step.get("name") for step in job.get("steps", ())
        if step.get("conclusion") == "success"
    }
    for name in (
        "Prove CUDA device contract",
        "Run CUDA-only workloads through CML admission",
        "Shared CUDA worker parity (CPU reference vs worker)",
        "Publish CUDA evidence metadata",
    ):
        require(name in names, f"CUDA_STEP_NOT_SUCCESS: {name}")
    return job


def parse_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        require("=" in line, "BAD_CUDA_ENV_LINE")
        key, value = line.split("=", 1)
        require(key and key not in values, "DUPLICATE_CUDA_ENV_FIELD")
        values[key] = value
    return values


def one_file(root, name):
    matches = [p for p in root.rglob(name) if p.is_file()]
    require(len(matches) == 1, f"ARTIFACT_MISSING_OR_DUPLICATED: {name}")
    return matches[0]


def validate_artifact(root, sha, run_id, job):
    cuda = parse_env(one_file(root, "cuda.env"))
    require(cuda.get("backend") == "cuda", "CUDA_BACKEND_NOT_ATTESTED")
    require(cuda.get("repository_sha") == sha, "CUDA_ARTIFACT_SHA_MISMATCH")
    require(cuda.get("runner") == job["runner_name"], "CUDA_ARTIFACT_RUNNER_MISMATCH")
    require(cuda.get("policy") == "gpu-only", "CUDA_ARTIFACT_POLICY_MISMATCH")
    if "run_id" in cuda:
        require(cuda["run_id"] == str(run_id), "CUDA_ARTIFACT_RUN_MISMATCH")
    version = cuda.get("futhark_version", "")
    require(version and version.lower() != "unknown", "FUTHARK_VERSION_MISSING")
    require(
        bool(HEX64_RE.fullmatch(cuda.get("futhark_sha256", ""))),
        "FUTHARK_TOOLCHAIN_DIGEST_MISSING",
    )

    capability = json.loads(one_file(root, "cuda-capability.json").read_text(encoding="utf-8"))
    require(capability.get("status") == "ready", "CUDA_CAPABILITY_NOT_READY")
    for field in ("device_visible", "driver_present", "header_present"):
        require(capability.get(field) is True, f"CUDA_CAPABILITY_MISSING: {field}")
    require(capability.get("host_kind") == "native-linux", "CUDA_LOCAL_WSL_FORBIDDEN")
    require(bool(capability.get("device_name")), "CUDA_DEVICE_NAME_MISSING")
    require(bool(capability.get("driver_version")), "CUDA_DRIVER_VERSION_MISSING")
    require(bool(capability.get("compute_capability")), "CUDA_COMPUTE_CAP_MISSING")

    parity = json.loads(
        one_file(root, "gpu-worker-parity.json").read_text(encoding="utf-8")
    )
    require(parity.get("schema") == "gpu-worker-parity/1", "PARITY_SCHEMA_MISSING")
    require(parity.get("elements") == 1048576, "PARITY_WORKLOAD_MISMATCH")
    require(parity.get("chain", {}).get("cuda_ns", 0) > 0, "CUDA_NOT_EXECUTED")
    require(bool(parity.get("negative_control")), "CUDA_NEGATIVE_CONTROL_MISSING")
    require(bool(parity.get("device", {}).get("name")), "CUDA_PARITY_DEVICE_MISSING")
    return cuda, capability


def pin_sha():
    pin = REPO_ROOT / "release" / "sens-source.pin"
    values = {}
    for line in pin.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value.strip()
    sha = values.get("SENS_COMMIT", "")
    require(bool(SHA_RE.fullmatch(sha)), "SENS_PIN_MISSING")
    return sha


def main():
    repo = os.environ.get("RELEASE_REPO", "juv4uk/sens-futhark")
    workflow = os.environ.get("RELEASE_WORKFLOW_FILE", "futhark.yml")
    branch = os.environ.get("RELEASE_BRANCH", "main")
    prefix = os.environ.get("RELEASE_ARTIFACT_PREFIX", "futhark-cuda-evidence-")
    sha = os.environ.get("RELEASE_SHA") or subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)), "INVALID_REPOSITORY")
    require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+\.ya?ml", workflow)), "INVALID_WORKFLOW")
    require(bool(SHA_RE.fullmatch(sha)), "INVALID_RELEASE_SHA")
    require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+", branch)), "INVALID_RELEASE_BRANCH")
    require(bool(re.fullmatch(r"[A-Za-z0-9_.-]+", prefix)), "INVALID_ARTIFACT_PREFIX")

    supplied = os.environ.get("RELEASE_RUN_URL", "")
    if supplied:
        url_re = re.fullmatch(
            rf"https://github\.com/{re.escape(repo)}/actions/runs/([0-9]+)",
            supplied,
        )
        require(url_re is not None, "RUN_URL_NOT_CANONICAL")
        run_id = int(url_re.group(1))
    else:
        candidates = gh_json(
            "run", "list", "--repo", repo, "--workflow", workflow,
            "--commit", sha, "--status", "success", "--limit", "20",
            "--json", "databaseId",
        )
        require(bool(candidates), "NO_SUCCESSFUL_RUN_AT_EXACT_SHA")
        run_id = int(candidates[0]["databaseId"])

    # A caller-supplied URL, SHA or local directory can never establish success.
    run = gh_json("api", f"repos/{repo}/actions/runs/{run_id}")
    validate_run(run, repo, sha, workflow, branch, run_id)
    jobs_data = gh_json("api", f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")
    require(jobs_data.get("total_count", 0) <= 100, "TOO_MANY_JOBS_TO_ATTEST")
    job = validate_jobs(jobs_data.get("jobs", ()))

    with tempfile.TemporaryDirectory(prefix="release-cuda-evidence-") as directory:
        gh(
            "run", "download", str(run_id), "--repo", repo,
            "--name", prefix + sha, "--dir", directory,
        )
        cuda, device = validate_artifact(Path(directory), sha, run_id, job)

    sens_pin = pin_sha()
    url = run["html_url"]
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    manifest = {
        "repo": repo,
        "repo_sha": sha,
        "sens_pin": sens_pin,
        "futhark_version": cuda["futhark_version"],
        "cuda_toolkit": device.get("nvcc_version") or "unknown",
        "cuda_root": device.get("cuda_root") or "unknown",
        "device": device["device_name"],
        "driver_version": device["driver_version"],
        "compute_capability": device["compute_capability"],
        "policy": "github-hosted-gpu-only",
        "cpu_witness": "N/A",
        "cuda_witness": "CONFIRMED",
        "run_url": url,
        "run_id": str(run_id),
        "runner": job["runner_name"],
        "date": when,
    }
    print("\n".join(f"{key}={value}" for key, value in manifest.items()))


if __name__ == "__main__":
    try:
        main()
    except (EvidenceError, OSError, subprocess.SubprocessError, KeyError, TypeError, ValueError) as exc:
        print(f"release-evidence: FAIL-CLOSED: {exc}", file=sys.stderr)
        sys.exit(2)
