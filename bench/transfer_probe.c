#define _POSIX_C_SOURCE 200809L

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "identity_cuda.h"

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

static void check_sync(struct futhark_context *ctx, const char *what) {
  if (futhark_context_sync(ctx) != 0) {
    die_ctx(ctx, what);
  }
}

static void run_phase(
    struct futhark_context *ctx,
    const int32_t *domains,
    const int32_t *bits,
    bool *host_out,
    int64_t n,
    int rep,
    bool emit) {
  uint64_t t0 = now_ns();

  struct futhark_i32_1d *domain_dev = futhark_new_i32_1d(ctx, domains, n);
  struct futhark_i32_1d *bits_dev = futhark_new_i32_1d(ctx, bits, n);
  if (domain_dev == NULL || bits_dev == NULL) {
    die_ctx(ctx, "failed to import input arrays");
  }
  check_sync(ctx, "H2D/import sync failed");
  uint64_t t1 = now_ns();

  struct futhark_bool_1d *result_dev = NULL;
  if (futhark_entry_validate_samples(ctx, &result_dev, domain_dev, bits_dev) != 0) {
    die_ctx(ctx, "validate_samples entry failed");
  }
  check_sync(ctx, "kernel sync failed");
  uint64_t t2 = now_ns();

  if (futhark_values_bool_1d(ctx, result_dev, host_out) != 0) {
    die_ctx(ctx, "failed to export result array");
  }
  check_sync(ctx, "D2H/export sync failed");
  uint64_t t3 = now_ns();

  for (int64_t i = 0; i < n; i++) {
    if (!host_out[i]) {
      fprintf(stderr, "unexpected false result at index %lld\n", (long long)i);
      exit(4);
    }
  }

  if (emit) {
    const uint64_t h2d_bytes = (uint64_t)n * sizeof(int32_t) * 2u;
    const uint64_t d2h_bytes = (uint64_t)n * sizeof(bool);
    printf(
        "%lld,%d,%llu,%llu,%llu,%llu,%llu\n",
        (long long)n,
        rep,
        (unsigned long long)h2d_bytes,
        (unsigned long long)d2h_bytes,
        (unsigned long long)(t1 - t0),
        (unsigned long long)(t2 - t1),
        (unsigned long long)(t3 - t2));
    fflush(stdout);
  }

  if (futhark_free_bool_1d(ctx, result_dev) != 0 ||
      futhark_free_i32_1d(ctx, domain_dev) != 0 ||
      futhark_free_i32_1d(ctx, bits_dev) != 0) {
    die_ctx(ctx, "failed to free Futhark arrays");
  }
}

int main(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s ELEMENTS REPEATS\n", argv[0]);
    return 2;
  }

  const int64_t n = strtoll(argv[1], NULL, 10);
  const int repeats = atoi(argv[2]);
  if (n <= 0 || repeats <= 0) {
    fprintf(stderr, "ELEMENTS and REPEATS must be positive\n");
    return 2;
  }

  int32_t *domains = malloc((size_t)n * sizeof(int32_t));
  int32_t *bits = malloc((size_t)n * sizeof(int32_t));
  bool *host_out = malloc((size_t)n * sizeof(bool));
  if (domains == NULL || bits == NULL || host_out == NULL) {
    fprintf(stderr, "host allocation failed\n");
    return 2;
  }

  for (int64_t i = 0; i < n; i++) {
    domains[i] = 7;
    bits[i] = (int32_t)(i & 127);
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
  char *ctx_error = futhark_context_get_error(ctx);
  if (ctx_error != NULL) {
    fprintf(stderr, "Futhark context error: %s\n", ctx_error);
    free(ctx_error);
    return 3;
  }

  /* Warm the already-created context and kernel path. Not part of evidence. */
  const int64_t warm_n = n < 256 ? n : 256;
  run_phase(ctx, domains, bits, host_out, warm_n, -1, false);

  printf("elements,repeat,h2d_import_bytes,d2h_export_bytes,h2d_import_ns,kernel_ns,d2h_export_ns\n");
  for (int rep = 0; rep < repeats; rep++) {
    run_phase(ctx, domains, bits, host_out, n, rep, true);
  }

  if (futhark_context_free(ctx) != 0) {
    fprintf(stderr, "failed to free Futhark context\n");
    return 3;
  }
  futhark_context_config_free(cfg);
  free(domains);
  free(bits);
  free(host_out);
  return 0;
}
