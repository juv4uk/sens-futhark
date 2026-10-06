import "identity"

-- Mechanical compiler-input legality scan.
-- SENS has already derived and authenticated the compiler role.
-- This GPU stage receives only the exact-domain facts required for the
-- mechanical property scan; it does not encode role meaning or role count.

def as_i64 (ok: bool): i64 =
  if ok then 1i64 else 0i64

entry compiler_legality_scan
    (domains: []i32)
    (bits: []i32)
    (batch: i64): []i64 =
  let seed_len = length domains
  let count =
    if batch <= 0i64 || seed_len == 0i64
    then 0i64
    else
      let checks =
        map
          (\i ->
            let j = i % seed_len
            in as_i64 (validate_current domains[j] bits[j]))
          (iota batch)
      in reduce (+) 0i64 checks
  in [count]

-- ==
-- entry: compiler_legality_scan
-- input { [3,3,3,3,3,3,3,4,4] [1,2,3,4,5,6,7,2,3] 4096i64 }
-- output { [4096i64] }

-- ==
-- entry: compiler_legality_scan
-- input { [3,3,3,3,3,3,3,4,4] [1,2,3,4,5,6,7,2,3] 1048576i64 }
-- output { [1048576i64] }
