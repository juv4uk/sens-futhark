# Аудит: GPU на self-hosted runner — стан у `sens-futhark` (2026-10-06)

**Статус:** research / аудит, не авторитет. Не змінює контракт чи рішення.
**Дата:** 2026-10-06. **Джерело даних:** локальний клон на `main` (HEAD `5a17a04`, чисте дерево) і живий стан хоста.

## Походження і межі довіри

Звіт склав агент-дослідник (ephemeral subagent, лише читання, модель не експонується середовищем). Координатор незалежно **не** перевіряв кожне твердження. Мітки: `[SC]` (source-confirmed — прочитано в коді/конфігу), `[EC]` (empirically-confirmed — live-команда або CI-лог; найнижчий щабель «local run / один CI-прогін»), `[NV]` (not-verified).

Це перший прохід по **`main`**. Гілки та відкриті PR охоплюються окремим другим проходом.

## Мета

Щоб self-hosted runner (GTX 1050 Ti 4 ГіБ, CUDA 12.6, WSL2) справді використовував GPU у CI, а не лише мав мітку `gpu`.

## A. Що вже є і працює на GPU

- CI-лог job `112097209386` (run `37410362514`, `main`, success, ~14 год тому) [EC]: `cuda-env.sh json` дає `status=ready`, WSL2, `device_visible=true`, але `device_name`, `compute_capability`, `driver_version` **порожні** — назва GTX 1050 Ti у CI-логу не друкується. Далі `smoke-cuda` (futhark cuda, `add_one`, `[2,3,4,5]`, PASS); `futhark test --backend=cuda`: `identity_witness`, `packed_domain`, `compiler_structural` — у кожному 1/1 passed. Також проходять python-тести `compiler-backend/v1` і «SENS compiler-semantic request: REAL PRODUCER OK» (`vendor/sens@5964c4dd`).
- Що саме йде на CUDA [SC]:
  - `identity.fut`/`identity_witness.fut`: `validate_samples`, `equal_samples` (D1–D7);
  - `packed_domain.fut`: `validate_batch`, `decode_batch`, checksum;
  - `compiler_structural.fut`: `lower_pair_construct`, `lower_selector_head`, `lower_selector_tail` (тотожні функції, identity-lowering);
  - `compiler_legality_scan.fut`: reduce по legality.
- «Паритет» тут = вбудовані вектори `-- == input/output` у Futhark. Це **не** CPU/oracle-паритет проти SENS [SC]. Найвищий щабель — один чистий self-hosted CI-прогін, не незалежна відтворюваність.
- Бенчмарки [SC, з evidence-md, не перезапускались]: 2026-10-05, identity — CUDA ≈ C (0,87–1,0×), холодний старт CUDA ~830–890 мс; 2026-10-06, legality scan — «NO STABLE GPU ADVANTAGE» (виграш 1,41× лише на 8M, на 16M 0,84×).
- Runner [EC]: `actions-runner-sens-futhark.service` active (running) від 17:54, MainPID 951 (`run.sh`). Є також `cml-gpu-worker.service`. `nvidia-smi`: GTX 1050 Ti, 598/4096 МіБ, драйвер 582.78 (WSL-прошарок; `nvidia-smi` показує «CUDA 13.0», toolkit для CI 12.6).

## B. Що є, але без доказу паритету або не end-to-end

- `selector_law.fut`, `work_queue.fut`, `host/arena.py` (S1–S3) у CI-таргетах **відсутні** [SC]: у `Makefile` лише `check` (typecheck), без тестів `-- ==` і без `--backend=cuda`; `arena.py` — чистий numpy-референс, не пристрій. Закриті issues #96/#97/#98 стверджують більше, ніж запускає CI.
- `selector_law.fut` згенеровано з `SENS_COMMIT=33ba9fca`, а pin = `5964c4dd` [SC]: таблиця застаріла відносно pin-у.
- `host/compiler_backend_v1.py` лише вибирає entrypoint за роллю. Шляху «запит → запуск futhark на GPU → порівняння з оракулом SENS» немає [SC].
- `tools/gpu_runner/worker.py` (PyTorch add/mul/matmul, `localhost:8765`) не пов'язаний ні з Futhark, ні з CI, ні з семантикою SENS [SC]; `Makefile` його не викликає.
- OpenCL не заявляється (узгоджено з README).

## C. Що треба доробити (за порядком)

1. Оновити pin SENS (`release/sens-source.pin`, `integration/sens-execution-conformance.lock`, `EXPECTED_SOURCE_COMMIT` у `compiler_backend_v1.py` та `bench/compiler_slice.py`) до коміту, що містить #3845. Залежить від рішення власника: коментар #115 каже не репінити на проміжні SHA, а брати merge-нащадок #3899 (спільний знаменник із CML #634).
2. #85: Futhark-вхід для пакета `SGP\x01` (декодер → allowlist ядер, fail-closed, без CPU-фолбеку). Залежить від п.1 і #3845 (UNBLOCKED, merge `1beb2d76`).
3. Корпус «packet → очікуваний результат» з реальними дайджестами оракула `sens`. Паритет має порівнюватись з оракулом SENS, а не з вбудованими векторами.
4. CUDA-тести для `selector_law`/`work_queue` і перегенерація `selector_law` з поточного pin-у.
5. #88 (VRAM-дескриптори; залежить від #85) і #86 (falsifier Graph Launch на Pascal, незалежний; без змін TDR).
6. Писати в evidence справжні `device_name`/CC/driver; зараз вони порожні, тож «GPU реально використано» у CI іменем пристрою не підтверджено. Також друкувати `admission_wait_ns` у лог (зараз лише в артефакті).

## D. Ризики та суперечності

- **Формат** [SC]: узгоджений контракт існує лише на папері. У коді `sens-futhark` немає жодної згадки `SGP`/`gpu_execution_packet` (лише `docs/compiler-futhark.md:111` посилається на #3802). Сьогодні вхід = JSON `compiler-semantic-input/1` (`host/sens_compiler_request.py`, тести) і сирі масиви i32/i64 (domains/bits, packed bytes). Це не компактний пакет — розрив великий і є головним.
- **Pin** [EC]: pin `5964c4dd`; remote `main` `juv4uk/sens` = `d54ac156` (`git ls-remote`). Pin відстає на 48 комітів, пакетний модуль у pin не входить (`merge-base --is-ancestor`: «не в pin»).
- **Помилка вихідного припущення координатора** [EC]: PID 1035 `Runner.Listener` — це не «ручний listener», а дочірній процес systemd-юніта (`run.sh` 951 → `run-helper` 1016 → 1035). `.manual-runner.pid` містить 5791, процесу немає (застарілий файл). Юніт у `~/.config/systemd/user/` відрізняється від `systemd/` у репо (додає `CML_GPU_WORKER_SOCKET`, `TimeoutStopSec=30` проти 120). #69 фактично виконано на хості, але issue ще open.
- **Інваріант #82/#79 порушено** [EC]: `bash tools/check-gpu-single-lane.sh` падає (exit 2): 2 workflow претендують на GPU (`compiler-slice.yml` і `futhark.yml`); коментар #79 вимагав «рівно один».
- **Замок** [EC]: `/run/cml-gpu-worker/` містить лише `worker.sock`, файлу `gpu-admission.lock` зараз немає. Його створює `flock` при першому запуску; каталог 0700, власник `agents`, проблем із правами немає, але це не доведено сторонній читач.
- **4 ГіБ / TDR** [SC]: профіль задає `tdr_ms=2000`, reserved 1 ГіБ, `display_class`. Партії ≥8M наближаються до ліміту — їх треба обмежувати.
- Переваги GPU над CPU немає ні на identity, ні на legality scan [SC]: «використання GPU» поки доводить коректність, не користь.

## E. Не перевірено / питання власнику

- [NV] порядок виконання між `cml-gpu-worker` і замком допуску; чи читає `flock`-замок сам воркер `cml`.
- [NV] чи #3845 (пакет) уже в remote `main` `d54ac156` (коментар #85 каже merge `1beb2d76`; перевірено лише локально, клон може бути застарілим).
- На який SHA репінити: нащадок #3899 чи свіжий `main`?
- Об'єднати `compiler-slice.yml` у `futhark.yml` (інваріант #82) чи дозволити 2 GPU workflow під одним замком?
- Чи закривати #69 після оновлення юніта в репо та видалення застарілого `.manual-runner.pid`?
- `gh issue view --comments` падає через Projects classic; агент користувався `gh api`.

---

## Другий прохід: усі гілки та відкриті PR (2026-10-06)

Джерело: агент-дослідник (лише читання, модель не експонується), після `git fetch origin`; `origin/main` = `5a17a04`. Мітки як у першому проході; координатор окремо не перевіряв. Відкритий лише один PR (#117); із 17 неузлитих віддалених гілок 16 — залишки вже злитих PR.

### Гілки та PR

| гілка | відст./випер. | PR і CI | що змінює | вердикт |
|---|---|---|---|---|
| `agent/chat-coordinator/115-whole-program` | 23/13 | **#117 OPEN**, MERGEABLE; «CUDA-only witness» pass 56 с, «Compiler GPU slice» pass 1 хв 9 с | 3 файли, +435: `host/sens_compiler_request.py` (+310, парсер і верифікатор артефакта), `tests/test_sens_whole_program_artifact.py`, `Makefile` (+2 рядки в `check-compiler-backend`, +2 в `test-compiler-backend-cuda`); workflow не чіпає | merge-ready як верифікація #115, але див. питання піна нижче |
| `agent/vivaka-hub/98-arena-s1`, `98b-device-packing`, `98c-batch-and-blob` | 126/5…12 | #101/#102/#103 MERGED | `host/arena*.py`, `profile.json` | stale |
| `chatgpt-sol/96-selector-law`, `97-persistent-kernel` | 118/3, 117/2 | #106/#107 MERGED | `selector_law.fut`, `work_queue.fut` (ідентичні `main`) | stale |
| `chatgpt-sol/99-cml-shared-queue-adapter` | 116/1 | #108 MERGED | `futhark.yml` (замок CML) | stale |
| `vivaka-hub/82-gpu-single-lane`, `82b-ci-wire` | 126/3 | #93/#94 MERGED | `check-gpu-single-lane.sh`, `futhark.yml` | stale |
| `chatgpt-sol/91-pin-compiler-main` | 119/1 | #105 MERGED | `release/sens-source.pin` → `33ba9fca` (**старіше** за поточний пін) | stale; **не зливати** — відкотить пін |
| `vivaka-hub/91-pin-pending-note`, `chatgpt-sol/37-pinned-fetch-rebase`, `vivaka-hub/37-vendor-pinned-sens` (PR #76 CLOSED) | — | MERGED/CLOSED | коментар у піні; `fetch-sens-source.sh`; вендоринг SENS | stale |

Ще чотири (`111-upstream-compiler-request` → #112, `81-manifest-from-artifacts` → #87, `83-makefile-gpu-only-labels` → #90, `84-release-guide-gpu-only` → #89) також змерджені й GPU-шляху не стосуються. Родини неузлитих: `chatgpt-sol/*` (7), `vivaka-hub/*` (9), `chat-coordinator/*` (1). Жодна не змінює `runs-on` чи мітки й не додає другий GPU-workflow (`runs-on` у `compiler-slice.yml` і `futhark.yml` ідентичний на `main` і на гілці 115).

### #85 і пін SENS: що вже є на гілках

- Жодна віддалена гілка не містить `SGP`, `gpu_execution_packet` чи `execution-packet` (`git grep` по всіх `origin/*` порожній, EC). Декодера #85 немає ні на `main`, ні на гілках.
- Реальний пакет у `juv4uk/sens` `origin/main` (`d54ac156`): `crates/sens/src/gpu_execution_packet.rs` (428 рядків) і `contracts/compiler-gpu-execution-packet-v1.lisp` (додано `1beb2d76`, #3845). Wire-формат майбутнього декодера [SC]: 4 байти magic `SGP\x01`; 1 байт `width` (1..6 або 8; 7 → fail) і 1 байт `payload`; канонічний varint числа входів (максимум 1024, неканонічний → fail); `count` × u64 LE handles; 1 байт тегу виходу (0 = Materialize; 1 = HandleSlot + u64 LE); 1 байт тегу залежності (0 = немає; 1 = + u64 LE); 32 байти provenance (рекомендований ключ — `semantic-request-sha256`); залишок байтів → fail. Допускаються лише ролі `PairConstruct`, `SelectorHead`, `SelectorTail` — ті самі три, що вже є в `futhark/compiler_structural.fut`.
- #117 пакет **не** споживає: вона верифікує `compiler-compilation-artifact/1` (текстовий S-expression зі `schema`, `artifact-kind=whole-program`, sha256 програми та semantic-requests, 5 значень `authority-provenance`) — це інший формат. Перше реальне розходження буде між `input_handles`/`output`/`dependency` пакета (u64) і поточними масивами i32 у `lower_*`.
- Пін-розбіжність (EC): пін у репо = `5964c4dd`, він не містить `1beb2d76`. #117 вшиває `EXPECTED_SENS_REVISION = c66d4743…` (merge #3901) і sha ядра `ce12207e…`. `c66d4743` — нащадок піна (21 коміт) і предок `sens` main (ще 30 комітів до `d54ac156`); містить `1beb2d76`. Після злиття #117 у репо будуть два різні SHA SENS (`5964c4dd` для піна й `c66d4743` для артефакта) — семантична невідповідність, питання власнику.

### Оновлений список робіт

- **В польоті:** #115/#117 — верифікатор whole-program артефакта, CI зелений, лишається питання піна.
- **Уже зроблено й злито, вилучити зі списку:** арена S1 (#101–#103), `selector_law`/`work_queue` як файли (#106/#107), адаптер черги CML (#108), guard single-lane як скрипт (#93/#94). Лишаються CUDA-тест і перегенерація `selector_law`.
- **Не розпочато (жодної гілки чи PR):** (1) оновлення піна SENS у 4 місцях до нащадка #3901/#3899 або свіжого `d54ac156`; (2) декодер `SGP\x01` + allowlist ядер (#85); (3) корпус «packet → очікуваний результат» з дайджестами оракула; (4) CUDA-тести `selector_law`/`work_queue` і регенерація `selector_law` з піна (зараз від `33ba9fca`); (5) #88 і #86; (6) запис `device_name`/CC/driver в evidence та друк `admission_wait_ns` у лог; (7) виправлення інваріанта single-lane (об'єднати два workflow або змінити guard).

### Рекомендований порядок (лише рекомендація)

1. Власник вирішує, який SHA SENS є пін. 2. Злити #117, лише якщо рішення допускає тимчасово два SHA; інакше узгодити `EXPECTED_SENS_REVISION` з вибраним SHA і злити разом із пін-бампом. 3. Окремий PR піна (4 місця) із тестами CI. 4. #85 — декодер `SGP\x01` на новому піні, з тестами на вектори з `gpu_execution_packet.rs`. 5. Об'єднати `compiler-slice.yml` у `futhark.yml` (або змінити guard). 6. CUDA-тести для `selector_law`/`work_queue`, evidence-поля, потім #88, #86. Усі 16 stale-гілок не потребують дій; видалення — лише з явного дозволу власника.

### Не перевірено

- Чи 23 коміти, на які #117 відстає від `main`, дають конфлікт (`gh` каже MERGEABLE, локально merge не робили); чи `d54ac156` — справжній remote HEAD `sens` (взято з локального `origin/main`); чи 16 stale-гілок видалені на GitHub автоматично.

---

## Стан після виконаних змін (2026-10-06, вечір)

Розділи вище — знімок на момент аудиту. Далі зафіксовано, що змінилось відтоді:

- **Перевірка спільного воркера додана** (#118, злито): у `futhark.yml` після кроку з `flock` (замок уже відпущено) виконується `.github/scripts/gpu-worker-parity.py` — копія канонічного скрипта з `juv4uk/sens`. Новий workflow не додано, тож інваріант single-lane (#82) не змінився. Прогін: `GPU_WORKER_PARITY_GREEN`, GTX 1050 Ti, CC 6.1, `cuda_ns ≈ 5,3 мс`; обидва workflow зелені. Свідчення з іменем пристрою (`gpu-worker-parity.json`) входить в артефакт.
- **Хост:** зайвий user-воркер і user-listener `cml` вимкнено, системний воркер замінено на нову збірку (див. аудит `cml`).
- **Не змінилось:** `tools/check-gpu-single-lane.sh` досі падає (два workflow: `compiler-slice.yml` і `futhark.yml`); декодер `SGP\x01` (#85), #88, #86, оновлення піна SENS (`5964c4dd` проти `c66d4743`/`d54ac156`), CUDA-тести `selector_law`/`work_queue`; поля `device_name`/CC/driver у `cuda-capability.json` усе ще порожні (ім'я пристрою тепер лише у JSON перевірки воркера).

---

## English mirror (short)

First-pass audit of `sens-futhark` on `main` (HEAD `5a17a04`) by a read-only subagent; not independently re-verified by the coordinator. CUDA kernels for identity, packed_domain and compiler_structural pass `futhark test --backend=cuda` on the self-hosted runner, but "parity" means built-in Futhark vectors, not the SENS oracle, and CI evidence lacks device name/CC/driver. `selector_law`/`work_queue`/arena are not run in CI. The input is still `compiler-semantic-input/1` JSON and raw arrays — no `SGP\x01` consumer exists (#85). The SENS pin is 48 commits stale. The single-GPU-lane invariant check currently fails (two workflows). The runner is systemd-managed, so #69 is effectively done on the host.
