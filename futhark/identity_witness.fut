import "identity"

def equal_pair (a: (i32, i32)) (b: (i32, i32)): bool =
  same_identity a.0 a.1 b.0 b.1

entry validate_samples (domains: []i32) (bits: []i32): []bool =
  map2 validate_current domains bits

entry equal_samples
    (domains_a: []i32) (bits_a: []i32)
    (domains_b: []i32) (bits_b: []i32): []bool =
  map2 equal_pair (zip domains_a bits_a) (zip domains_b bits_b)

-- ==
-- entry: validate_samples
-- input { [1,2,3,4,5,6,7] [1,3,7,15,31,63,127] }
-- output { [true,true,true,true,true,true,true] }

-- ==
-- entry: validate_samples
-- input { [0,8,3,7] [0,0,8,127] }
-- output { [false,false,false,true] }

-- ==
-- entry: equal_samples
-- input { [1,3,3,7] [1,1,7,42] [3,3,3,7] [1,1,7,42] }
-- output { [false,false,true,true] }
