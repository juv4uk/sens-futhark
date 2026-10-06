import "identity"

-- Mechanical compiler-input legality scan.
-- The role tag is already derived by SENS; Futhark only validates the
-- backend-neutral transport shape and executes the batch mechanically.
def role_tag_valid (role: i32): bool =
  role >= 0 && role < 9

def request_valid (domain: i32) (bits: i32) (role: i32): bool =
  validate_current domain bits && role_tag_valid role

def as_i64 (ok: bool): i64 =
  if ok then 1i64 else 0i64

entry compiler_legality_scan
    (domains: []i32)
    (bits: []i32)
    (roles: []i32)
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
            in as_i64 (request_valid domains[j] bits[j] roles[j]))
          (iota batch)
      in reduce (+) 0i64 checks
  in [count]

-- ==
-- entry: compiler_legality_scan
-- input { [3,3,3,3,3,3,3,4,4] [1,2,3,4,5,6,7,2,3] [0,1,2,3,4,5,6,7,8] 4096i64 }
-- output { [4096i64] }

-- ==
-- entry: compiler_legality_scan
-- input { [3,3,3,3,3,3,3,4,4] [1,2,3,4,5,6,7,2,3] [0,1,2,3,4,5,6,7,8] 1048576i64 }
-- output { [1048576i64] }
