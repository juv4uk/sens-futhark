-- Infrastructure-only smoke test for issue #1.
-- This file deliberately contains no SENS semantics.

entry add_one (xs: []i32) : []i32 =
  map (\x -> x + 1) xs
