-- Exact SENS identity guard.
--
-- This module is intentionally semantic-free: it validates only the
-- mechanical domain-qualified shape received from the canonical SENS layer.
--
-- i32 is a physical carrier here. It is NOT a SENS semantic width.

def limit (domain: i32): i32 =
  if domain == 1 then 2
  else if domain == 2 then 4
  else if domain == 3 then 8
  else if domain == 4 then 16
  else if domain == 5 then 32
  else if domain == 6 then 64
  else if domain == 7 then 128
  else 0

def current_domain (domain: i32): bool =
  domain >= 1 && domain <= 7

entry validate_current (domain: i32) (bits: i32): bool =
  if not (current_domain domain)
  then false
  else bits >= 0 && bits < limit domain

entry same_identity
    (domain_a: i32) (bits_a: i32)
    (domain_b: i32) (bits_b: i32): bool =
  domain_a == domain_b && bits_a == bits_b
