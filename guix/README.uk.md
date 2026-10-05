# Guix як execution substrate

`manifest.scm` описує мінімальне чисте середовище для Python importer-а та CPU
witness: Python, Bash, coreutils, Git і CA certificates. Воно не визначає
SENS semantics, domains або admission.

`./guix/run dev -- команда` запускає таке середовище. Роль `futhark` має той
самий базовий profile і лише позначає, що команда може шукати repo-local
Futhark toolchain.

Futhark compiler, CUDA toolkit, WSL `/dev/dxg` і driver library є
**optional host-provided** capability. Їхня присутність не гарантується Guix,
а відсутність GPU/OpenCL platform не може бути інтерпретована як semantic
success. GPU evidence завжди називає конкретний device, backend і версію.
