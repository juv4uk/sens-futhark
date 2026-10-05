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

entry synthetic_256_bytes: []i64 =
  decode_batch byte_batch 2048i64 byte_offsets byte_widths

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
-- D8 is mechanically decodable, but current-domain admission remains false.
-- entry: validate_batch
-- input { [170i64] 8i64 [0i64] [8i64] }
-- output { [false] }

-- ==
-- entry: decode_batch
-- input { [170i64] 8i64 [0i64] [8i64] }
-- output { [170i64] }

-- ==
-- Non-zero low tail bits are not canonical payload.
-- entry: validate_batch
-- input { [139i64] 7i64 [0i64] [7i64] }
-- output { [false] }

-- ==
-- Out-of-range word request is rejected.
-- entry: validate_batch
-- input { [138i64] 7i64 [5i64] [3i64] }
-- output { [false] }

-- ==
-- 256 independent byte-width requests: parallel batch decode.
-- entry: synthetic_256_bytes
-- output { [0i64,1i64,2i64,3i64,4i64,5i64,6i64,7i64,8i64,9i64,10i64,11i64,12i64,13i64,14i64,15i64,16i64,17i64,18i64,19i64,20i64,21i64,22i64,23i64,24i64,25i64,26i64,27i64,28i64,29i64,30i64,31i64,32i64,33i64,34i64,35i64,36i64,37i64,38i64,39i64,40i64,41i64,42i64,43i64,44i64,45i64,46i64,47i64,48i64,49i64,50i64,51i64,52i64,53i64,54i64,55i64,56i64,57i64,58i64,59i64,60i64,61i64,62i64,63i64,64i64,65i64,66i64,67i64,68i64,69i64,70i64,71i64,72i64,73i64,74i64,75i64,76i64,77i64,78i64,79i64,80i64,81i64,82i64,83i64,84i64,85i64,86i64,87i64,88i64,89i64,90i64,91i64,92i64,93i64,94i64,95i64,96i64,97i64,98i64,99i64,100i64,101i64,102i64,103i64,104i64,105i64,106i64,107i64,108i64,109i64,110i64,111i64,112i64,113i64,114i64,115i64,116i64,117i64,118i64,119i64,120i64,121i64,122i64,123i64,124i64,125i64,126i64,127i64,128i64,129i64,130i64,131i64,132i64,133i64,134i64,135i64,136i64,137i64,138i64,139i64,140i64,141i64,142i64,143i64,144i64,145i64,146i64,147i64,148i64,149i64,150i64,151i64,152i64,153i64,154i64,155i64,156i64,157i64,158i64,159i64,160i64,161i64,162i64,163i64,164i64,165i64,166i64,167i64,168i64,169i64,170i64,171i64,172i64,173i64,174i64,175i64,176i64,177i64,178i64,179i64,180i64,181i64,182i64,183i64,184i64,185i64,186i64,187i64,188i64,189i64,190i64,191i64,192i64,193i64,194i64,195i64,196i64,197i64,198i64,199i64,200i64,201i64,202i64,203i64,204i64,205i64,206i64,207i64,208i64,209i64,210i64,211i64,212i64,213i64,214i64,215i64,216i64,217i64,218i64,219i64,220i64,221i64,222i64,223i64,224i64,225i64,226i64,227i64,228i64,229i64,230i64,231i64,232i64,233i64,234i64,235i64,236i64,237i64,238i64,239i64,240i64,241i64,242i64,243i64,244i64,245i64,246i64,247i64,248i64,249i64,250i64,251i64,252i64,253i64,254i64,255i64] }