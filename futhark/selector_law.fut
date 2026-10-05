-- GENERATED FROM pinned juv4uk/sens selector_law.rs; DO NOT EDIT.
-- SENS_COMMIT=33ba9fcad7e35f4bb4f284e28982501d1e5bcb55
-- Mechanical device projection; SENS remains semantic authority.

let widths : []i32 = [3,3,4,4,4,4,5,5,5,5,5,5,5,5]
let payloads : []i32 = [3,4,8,9,6,7,16,17,18,19,12,13,14,15]
let roles : []i32 = [2,1,1,1,2,2,1,1,1,1,2,2,2,2]

def selector_index (domain: i32) (payload: i32): i32 =
  let matches = map2 (\w p -> w == domain && p == payload) widths payloads
  let idx = filter (\i -> matches[i]) (iota (length matches))
  in if length idx == 1 then idx[0] else -1

entry route_selectors (domains: []i32) (payloads_in: []i32): []i32 =
  map (\p -> let i = selector_index p.0 p.1
             in if i >= 0 then roles[i] else 0) (zip domains payloads_in)

-- D3=2, D4=4, D5=8 admitted selectors; all other identities fail closed.
