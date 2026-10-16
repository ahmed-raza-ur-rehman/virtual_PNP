import time, numpy as np
from pnp.optimization.placement import optimize_placement

ts = [{"id": i, "type": "0402" if i % 2 == 0 else "0603",
       "x": float(i*3), "z": float((i%5)*4), "placed": False} for i in range(200)]
t0 = time.time()
optimize_placement(ts)
print(f"optimize 200 targets: {(time.time()-t0)*1000:.1f} ms")
