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
-- input { [1i32,2i32,3i32,4i32,5i32,6i32,7i32] [1i32,3i32,7i32,15i32,31i32,63i32,127i32] }
-- output { [true,true,true,true,true,true,true] }

-- ==
-- entry: validate_samples
-- input { [0i32,8i32,3i32,7i32] [0i32,0i32,8i32,127i32] }
-- output { [false,false,false,true] }

-- ==
-- entry: equal_samples
-- input { [1i32,3i32,3i32,7i32] [1i32,1i32,7i32,42i32] [3i32,3i32,3i32,7i32] [1i32,1i32,7i32,42i32] }
-- output { [false,false,true,true] }
