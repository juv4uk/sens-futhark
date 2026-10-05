# #7: межа інтеграції `sens` → `sens-futhark`

**Статус:** затверджений напрям; очікує перевірки специфікації власником перед планом реалізації.

## Мета

`sens-futhark` має перевірно споживати canonical witness fixtures із
`juv4uk/sens`, не стаючи другою реалізацією семантики SENS. Зміна fixture у
`sens` не може непомітно пройти як актуальна fixture у backend.

Ця задача також робить репозиторій авторським і відтворюваним у тому самому
сенсі, що й інші авторські репозиторії власника:

- README пояснює систему українською;
- `LICENSE` є дослівним канонічним текстом ВОЛЬНОСТІ;
- Guix описує execution substrate, а не семантику.

## Межа влади

```text
sens: language contract + canonical fixture source
  │
  │ versioned exported fixture bundle
  │ (schema, source commit, source contract version, SHA-256, vectors)
  ▼
sens-futhark: import verification → CPU witness → optional backend witness
  │
  ▼
host/parity.py: exact observation comparison
```

`sens` володіє значенням доменів, допустимістю і semantic laws.
`sens-futhark` володіє лише механікою: перевіркою transport bundle, запуском
CPU/Futhark substrate та спостереженням паритету. Futhark/GPU не призначає
жодної семантики і не є admission authority.

## Обраний механізм: versioned fixture bundle

Підтримуваний зв'язок — **комітований export bundle**, а не Rust API і не
git-submodule. Bundle має містити щонайменше:

```text
schema version
source repository identity
source commit SHA
SENS language-contract version
fixture payload SHA-256
fixture file(s) with (domain, exact bits, expected observation)
```

`sens-futhark` зберігає import manifest поруч із локальною копією bundle.
Import helper приймає явно заданий source path або archive, перевіряє усі
поля та записує fixture тільки після успішної перевірки. Ручне копіювання
D1–D7 таблиць заборонене.

### Чому не інші варіанти

- Rust library/API створює coupling до host implementation і робить
  незалежний witness менш відтворюваним.
- Git submodule фіксує дерево Git, але сам не визначає export schema, digest
  чи fail-closed import.

Bundle малий, рев'юється як дані, а його provenance і stale-state
перевіряються явно.

## Fail-closed import

Import або witness command повертає non-zero до backend execution, коли є
хоча б одна з умов:

- невідомий schema version;
- відсутній source commit, contract version або payload digest;
- payload SHA-256 не збігається з manifest;
- source repository не є очікуваним `juv4uk/sens`;
- contract version не входить у pinned supported set;
- vector schema malformed, має duplicate identity або не допускається
  чинною backend boundary;
- CPU або backend witness відсутній чи не має того самого bundle provenance.

`D8` лишається research/fail-closed, доки окремий upstream contract цього не
ратифікує. Наявність широкого машинного типу не є причиною прийняти domain.

## Одна відтворювана команда

Планований Make target (назву буде зафіксовано в implementation plan) виконує
послідовність:

1. перевіряє imported bundle;
2. запускає `host/cpu_witness.py` над його vectors;
3. запускає обраний backend лише якщо він явно доступний;
4. передає обидва outputs у `host/parity.py`;
5. друкує source commit, contract version і digests.

За відсутності CUDA/OpenCL command має повідомити `blocked/unavailable` та
non-zero для запитаного backend witness; він не має перетворювати відсутність
пристрою на CPU/GPU success. CPU-only verification лишається окремою
дешевою командою.

## Документація та ліцензія

`README.md` буде українською основною документацією. Вона міститиме:

- призначення та межу substrate/semantic authority;
- current evidence: CUDA witness підтверджений, OpenCL platform на WSL2
  відсутня і не заявляється робочою;
- швидкий Guix запуск;
- чесну межу: GPU parity не оголошується без реального backend witness.

У корені з'являється `LICENSE` як дослівна копія канонічної ВОЛЬНОСТІ.
Жодних пояснень, copyright-дописів або third-party terms до цього файлу не
додається. README пояснює, що ВОЛЬНІСТЬ застосовується до юридично
віддільної авторської роботи; інструменти Futhark та інші сторонні компоненти
зберігають власні умови та provenance.

## Guix substrate

Базовий `manifest.scm` декларативно міститиме тільки потрібні для
CPU/import/tooling інструменти: Bash, coreutils, Git, Python та CA
certificates. Futhark/CUDA — окремий optional capability layer: CUDA runtime
на WSL є host-provided, тому manifest не симулює GPU availability.

`guix/run` буде тонким entrypoint за патерном `sens`: чистий shell, явна
роль, без прихованого успадкування `$PATH`. `guix/README.uk.md` пояснить
ролі, контейнерну/мережеву межу й те, що Guix не задає SENS semantics.

## Перевірка

Focused tests мають довести:

1. валідний exported bundle проходить import та дає стабільний CPU digest;
2. один змінений байт vectors відхиляється за SHA-256;
3. старий або невідомий contract/schema version відхиляється;
4. duplicate або malformed `(domain,bits)` відхиляється;
5. CPU output порівнюється сам із собою через `host/parity.py` успішно;
6. відсутній backend output ніколи не трактується як GPU parity.

GPU test запускається лише у виділеному self-hosted lane після resource
preflight. Він додає evidence про конкретний device/backend/version, а не
семантичну владу.

## Межа реалізації

Ця задача не додає SENS primitive semantics, не переписує upstream contract,
не обіцяє OpenCL support і не вимірює performance. Benchmark lane #5 та
cross-backend lane #6 лишаються окремими.
