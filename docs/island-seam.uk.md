# Common execution seam (SENS-BRIDGE)

Цей репозиторій — **власник backend/mechanism**, а не семантики. Він приймає
спільний execution seam і **не** карбує Core-ідентичності з нативних операцій.

## Шість Core-значень шва

`ISLAND-CALL`, `EXECUTION-WITNESS`, `NATIVE-OBSERVATION`, `RESULT-COUNT`,
`BRIDGE`, `MISSING-CAPABILITY`.

## Що належить backend-у

- прийняти семантичну ідентичність + **непрозорий** нативний payload на межі;
- зберегти producer-native observation і його multiplicity;
- видати execution witness, що описує **реалізований механізм**;
- відсутнє ядро/міст → типізований `MISSING-CAPABILITY(kind)`;
- тримати нативні opcode/register/ABI/kernel/MMIO/driver/IR ідентичності локально;
- **ніколи** не перенумеровувати Core-семантику через відсутню здатність.

## Похідне на Core-рівні (не окремі residents тут)

- `ZERO/ONE/MANY` → `RESULT-COUNT` (обчислюється з multiplicity);
- `MISSING-KERNEL` / `MISSING-BRIDGE` → `MISSING-CAPABILITY(kind)`;
- `EXPLICIT-PROJECTION` → звичайна явна проєкція / `APPLY`;
- provenance → наявний нижчий `PROVENANCE`.

## Реалізація тут

`host/island_seam.py` — `Backend` з `register_kernel` / `register_bridge` і
`island_call(semantic_identity, payload, kernel_id, bridge_id=None)`.
Семантична ідентичність **відлунюється, не інтерпретується**.

Приклади (machine-readable): `examples/island-witness.success.json`,
`examples/island-witness.missing.json`.

## Межі

Це **шов**, а не семантика: модуль не містить жодної Core-coordinate таблиці
(це перевіряє окремий тест). Реальні нативні ядра (CUDA/Futhark) сюди не
підключені — лише контракт і його перевірка на CPU.

Зворотні лінки: juv4uk/sens#4094, juv4uk/sens#4126 (інтегрований D10 seam; #4112 superseded).
