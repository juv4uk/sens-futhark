# Канонічний entrypoint SENS (#39)

## Правило

Мову виконує **лише** pinned `juv4uk/sens` (`cargo run -p sens-cli`).  
`sens-futhark` не містить власного evaluator.

## Підготовка checkout

```bash
bash tools/verify-sens-source-pin.sh
# клон (один раз):
git clone https://github.com/juv4uk/sens.git vendor/sens
git -C vendor/sens fetch --depth 1 origin a4a83f2a879797bd431bd9896a52b707d7df7d53
git -C vendor/sens checkout a4a83f2a879797bd431bd9896a52b707d7df7d53
```

## Запуск

```bash
bash tools/sens-cli.sh path/to/file.lisp
# або
make sens-cli ARGS='path/to/file.lisp'
```

Аргументи передаються **без** трансформації.

## Parity smoke

```bash
bash tools/smoke-sens-cli-parity.sh
```

Порівнює wrapper і прямий `cargo run -p sens-cli` на `release/smoke/hello.lisp`:  
stdout, stderr, exit — byte-identical. Без checkout — skip (не false green).

## Межі

- CUDA/OpenCL/Futhark **не** потрібні для базового запуску мови.
- Відсутній або інший SHA checkout → fail-closed.
