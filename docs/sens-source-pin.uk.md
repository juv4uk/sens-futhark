# Pin канонічного джерела SENS (#38)

## Правило

`juv4uk/sens` — єдина семантична й runtime-влада. `sens-futhark` **не** копіює parser/evaluator/laws.

## Файл pin

`release/sens-source.pin` фіксує:

- URL репозиторію;
- повний SHA коміту (`a4a83f2a879797bd431bd9896a52b707d7df7d53`);
- очікуваний шлях checkout: `vendor/sens`.

## Перевірка

```bash
bash tools/verify-sens-source-pin.sh
```

- відсутній або битий pin → fail-closed;
- відсутній checkout → pin валідний, runtime (#39) ще не готовий;
- checkout з іншим SHA → fail-closed.

## Оновлення pin

1. Обрати новий upstream commit у `juv4uk/sens`.
2. Змінити лише `SENS_COMMIT` у `release/sens-source.pin`.
3. Прогнати `verify-sens-source-pin.sh` і smoke entrypoint (#39).
4. Ніколи не «плавати» на `main` без явного bump.

## Submodule (опційно)

Повний `git submodule` на той самий SHA — прийнятний наступний крок; цей pin уже auditable без копіювання коду.
