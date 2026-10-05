-- Bounded device work-queue primitive for S3.
-- The host still owns launch/relaunch; this module makes each work item
-- explicitly bounded and checkpointable so WDDM/TDR cannot require an
-- unbounded kernel. It is intentionally not an infinite-spin scheduler.

type Work = (i32, i32, i32) -- (work id, remaining steps, accumulator)

def run_bounded (max_steps: i32) (w: Work): Work =
  let budget = if max_steps < 0 then 0 else max_steps
  let steps = if w.1 < budget then w.1 else budget
  let acc = w.2 + steps
  in (w.0, w.1 - steps, acc)

entry dispatch_batch (max_steps: i32) (queue: []Work): []Work =
  map (run_bounded max_steps) queue

entry checkpointed (max_steps: i32) (queue: []Work): []bool =
  map (\w -> w.1 == 0) (dispatch_batch max_steps queue)

-- Work that exceeds the device budget remains queued for a later bounded
-- dispatch. No item is silently dropped and no infinite loop is introduced.
