# CPU/GPU identity witness

This lane intentionally uses the same Futhark source and the same embedded test specifications for every backend.

Sequential CPU:

```sh
futhark test --backend=c futhark/identity_witness.fut
```

GPU (when a CUDA-capable environment is available):

```sh
futhark test --backend=cuda futhark/identity_witness.fut
```

The expected observations are backend-independent booleans:

- every valid D1-D7 exact identity is accepted;
- D0 and D8 are rejected;
- bits outside a domain's exact capacity are rejected;
- equal packed payloads remain unequal when domains differ.

A future host witness must consume the same corpus rather than copying expected outputs from one backend. Any divergence is reported by the input `(domain,bits)` pair.

Futhark supports embedded `futhark test` specifications and separate backend execution, so the same test program can serve as the CPU/GPU parity witness. citeturn863582search0turn863582search5
