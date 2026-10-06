#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "compiler_legality_scan_cuda.h"

#define SEED_ROWS 9

static uint64_t now_ns(void) {
  struct timespec ts;
  if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0) {
    perror("clock_gettime");
    exit(2);
  }
  return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

static void die_ctx(struct futhark_context *ctx, const char *what) {
  char *err = futhark_context_get_error(ctx);
  fprintf(stderr, "%s", what);
  if (err != NULL) {
    fprintf(stderr, ": %s", err);
    free(err);
  }
  fputc('\n', stderr);
  exit(3);
}

static void sync_or_die(struct futhark_context *ctx, const char *what) {
  if (futhark_context_sync(ctx) != 0) {
    die_ctx(ctx, what);
  }
}

static int read_seed(const char *path, int32_t *domains, int32_t *bits) {
  FILE *fp = fopen(path, "r");
  if (fp == NULL) {
    perror(path);
    return 0;
  }

  char line[4096];
  int32_t *targets[2] = {domains, bits};
  for (int row = 0; row < 2; ++row) {
    if (fgets(line, sizeof(line), fp) == NULL) {
      fprintf(stderr, "seed file ended before row %d\n", row + 1);
      fclose(fp);
      return 0;
    }
    char *cursor = line;
    for (int i = 0; i < SEED_ROWS; ++i) {
      char *end = NULL;
      long value = strtol(cursor, &end, 10);
      if (end == cursor || (value < INT32_MIN || value > INT32_MAX)) {
        fprintf(stderr, "invalid seed value in row %d index %d\n", row + 1, i);
        fclose(fp);
        return 0;
      }
      targets[row][i] = (int32_t)value;
      cursor = end;
      while (*cursor == ' ' || *cursor == '\t' || *cursor == ',') {
        ++cursor;
      }
    }
  }

  fclose(fp);
  return 1;
}

static void run_once(
    struct futhark_context *ctx,
    const int32_t *domains,
    const int32_t *bits,
    int64_t batch,
    int repeat,
    int emit) {
  uint64_t t0 = now_ns();

  struct futhark_i32_1d *domain_dev =
      futhark_new_i32_1d(ctx, domains, SEED_ROWS);
  struct futhark_i32_1d *bits_dev =
      futhark_new_i32_1d(ctx, bits, SEED_ROWS);
  struct futhark_i32_1d *roles_dev =
      futhark_new_i32_1d(ctx, roles, SEED_ROWS);
  if (domain_dev == NULL || bits_dev == NULL || roles_dev == NULL) {
    die_ctx(ctx, "failed to import compiler request seed");
  }
  sync_or_die(ctx, "H2D/import sync failed");
  uint64_t t1 = now_ns();

  struct futhark_i64_1d *result_dev = NULL;
  if (futhark_entry_compiler_legality_scan(
          ctx, &result_dev, domain_dev, bits_dev, batch) != 0) {
    die_ctx(ctx, "compiler_legality_scan entry failed");
  }
  sync_or_die(ctx, "kernel sync failed");
  uint64_t t2 = now_ns();

  int64_t output[1] = {0};
  if (futhark_values_i64_1d(ctx, result_dev, output) != 0) {
    die_ctx(ctx, "failed to export compiler legality result");
  }
  sync_or_die(ctx, "D2H/export sync failed");
  uint64_t t3 = now_ns();

  if (output[0] != batch) {
    fprintf(stderr, "expected %lld valid rows, got %lld\n",
            (long long)batch, (long long)output[0]);
    exit(4);
  }

  if (emit) {
    const uint64_t h2d_bytes =
        (uint64_t)SEED_ROWS * 2u * sizeof(int32_t);
    const uint64_t d2h_bytes = sizeof(output);
    printf("%lld,%d,%llu,%llu,%llu,%llu,%llu\n",
           (long long)batch,
           repeat,
           (unsigned long long)h2d_bytes,
           (unsigned long long)d2h_bytes,
           (unsigned long long)(t1 - t0),
           (unsigned long long)(t2 - t1),
           (unsigned long long)(t3 - t2));
    fflush(stdout);
  }

  if (futhark_free_i64_1d(ctx, result_dev) != 0 ||
      futhark_free_i32_1d(ctx, domain_dev) != 0 ||
      futhark_free_i32_1d(ctx, bits_dev) != 0) {
    die_ctx(ctx, "failed to free compiler-slice buffers");
  }
}

int main(int argc, char **argv) {
  if (argc != 4) {
    fprintf(stderr, "usage: %s SEED_PATH BATCH REPEATS\n", argv[0]);
    return 2;
  }

  const int64_t batch = strtoll(argv[2], NULL, 10);
  const int repeats = atoi(argv[3]);
  if (batch <= 0 || repeats <= 0) {
    fprintf(stderr, "BATCH and REPEATS must be positive\n");
    return 2;
  }

  int32_t domains[SEED_ROWS];
  int32_t bits[SEED_ROWS];
  if (!read_seed(argv[1], domains, bits)) {
    return 2;
  }

  struct futhark_context_config *cfg = futhark_context_config_new();
  if (cfg == NULL) {
    fprintf(stderr, "failed to create Futhark context config\n");
    return 3;
  }

  struct futhark_context *ctx = futhark_context_new(cfg);
  if (ctx == NULL) {
    fprintf(stderr, "failed to create Futhark context\n");
    return 3;
  }

  /* Warm the already-created context and kernel path; excluded from evidence. */
  run_once(ctx, domains, bits, 256, -1, 0);

  printf("batch,repeat,h2d_import_bytes,d2h_export_bytes,h2d_import_ns,kernel_ns,d2h_export_ns\n");
  for (int repeat = 0; repeat < repeats; ++repeat) {
    run_once(ctx, domains, bits, batch, repeat, 1);
  }

  futhark_context_free(ctx);
  futhark_context_config_free(cfg);
  return 0;
}
