-- Batch exact-width validation and decode for the L1 packed payload.
--
-- This module is mechanical backend code only.
-- The caller supplies bit_len plus exact (offset,width) schedule.
-- Physical i64 storage does NOT define SENS semantic width.

def payload_fits (bytes: []i64) (bit_len: i64): bool =
  bit_len >= 0 && bit_len <= (length bytes) * 8i64

def tail_is_canonical (bytes: []i64) (bit_len: i64): bool =
  if not (payload_fits bytes bit_len)
  then false
  else
    let remainder = bit_len % 8i64
    in if remainder == 0i64
       then true
       else
         let unused = 8i64 - remainder
         let mask = (1i64 << unused) - 1i64
         let last = bytes[(length bytes) - 1i64]
         in last >= 0i64 && last <= 255i64 && (last & mask) == 0i64

def request_valid (bytes: []i64) (bit_len: i64) (offset: i64) (width: i64): bool =
  payload_fits bytes bit_len
  && tail_is_canonical bytes bit_len
  && offset >= 0i64
  && width >= 1i64
  && width <= 8i64
  && offset <= bit_len - width
  && bytes[offset / 8i64] >= 0i64
  && bytes[offset / 8i64] <= 255i64
  && bytes[(offset + width - 1i64) / 8i64] >= 0i64
  && bytes[(offset + width - 1i64) / 8i64] <= 255i64

def read_exact (bytes: []i64) (offset: i64) (width: i64): i64 =
  loop value = 0i64 for i < width do
    let position = offset + i
    let byte_index = position / 8i64
    let bit_index = position % 8i64
    let byte_value = bytes[byte_index]
    let bit = (byte_value >> (7i64 - bit_index)) & 1i64
    in (value << 1i64) | bit

def current_request_valid (bytes: []i64) (bit_len: i64) (offset: i64) (width: i64): bool =
  request_valid bytes bit_len offset width && width <= 7i64

def decode_one (bytes: []i64) (bit_len: i64) (offset: i64) (width: i64): i64 =
  if request_valid bytes bit_len offset width
  then read_exact bytes offset width
  else -1i64

entry validate_batch
    (bytes: []i64) (bit_len: i64)
    (offsets: []i64) (widths: []i64): []bool =
  map (\p -> current_request_valid bytes bit_len p.0 p.1) (zip offsets widths)

entry decode_batch
    (bytes: []i64) (bit_len: i64)
    (offsets: []i64) (widths: []i64): []i64 =
  map (\p -> decode_one bytes bit_len p.0 p.1) (zip offsets widths)

-- A full byte-aligned batch is a useful large synthetic witness.
def byte_batch : []i64 = iota 256
def byte_offsets : []i64 = map (\i -> i * 8i64) (iota 256)
def byte_widths : []i64 = replicate 256 8i64

entry synthetic_256_checksum: i64 =
  let decoded = decode_batch byte_batch 2048i64 byte_offsets byte_widths
  let weighted = map2 (*) byte_batch decoded
  in reduce (+) 0i64 weighted

-- ==
-- entry: validate_batch
-- input { [138i64] 7i64 [0i64,2i64,5i64] [2i64,3i64,2i64] }
-- output { [true,true,true] }

-- ==
-- entry: decode_batch
-- input { [138i64] 7i64 [0i64,2i64,5i64] [2i64,3i64,2i64] }
-- output { [2i64,1i64,1i64] }

-- ==
-- entry: validate_batch
-- input { [0i64] 3i64 [0i64,1i64] [1i64,2i64] }
-- output { [true,true] }

-- ==
-- entry: decode_batch
-- input { [0i64] 3i64 [0i64,1i64] [1i64,2i64] }
-- output { [0i64,0i64] }

-- ==
-- entry: validate_batch
-- input { [170i64] 8i64 [0i64] [8i64] }
-- output { [false] }

-- ==
-- entry: decode_batch
-- input { [170i64] 8i64 [0i64] [8i64] }
-- output { [170i64] }

-- ==
-- entry: validate_batch
-- input { [139i64] 7i64 [0i64] [7i64] }
-- output { [false] }

-- ==
-- entry: validate_batch
-- input { [138i64] 7i64 [5i64] [3i64] }
-- output { [false] }

-- ==
-- entry: synthetic_256_checksum
-- input { }
-- output 5559680i64