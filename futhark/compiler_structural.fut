-- Target-specific lowering for already-verified structural compiler roles.
-- No SENS identity inference happens here.
--
-- The host/compiler boundary supplies the admitted target mechanism and operands.
-- Futhark only implements the physical data movement/structure required by that
-- mechanism.

entry lower_pair_construct (left: []i32) (right: []i32): ([]i32, []i32) =
  (left, right)

entry lower_selector_head (left: []i32): []i32 =
  left

entry lower_selector_tail (right: []i32): []i32 =
  right

-- ==
-- entry: lower_pair_construct
-- input { [1i32,2i32,3i32] [10i32,20i32,30i32] }
-- output { [1i32,2i32,3i32] [10i32,20i32,30i32] }

-- ==
-- entry: lower_selector_head
-- input { [7i32,8i32,9i32] }
-- output { [7i32,8i32,9i32] }

-- ==
-- entry: lower_selector_tail
-- input { [17i32,18i32,19i32] }
-- output { [17i32,18i32,19i32] }
