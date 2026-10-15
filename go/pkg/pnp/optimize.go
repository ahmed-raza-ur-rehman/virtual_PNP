package pnp

import "math"

type Target struct {
    ID     int
    Type   string
    X, Z   float64
    Placed bool
}

type Point struct{ X, Y float64 }

func OptimizePlacement(targets []Target, start Point) []Target {
    var placed, unplaced []Target
    for _, t := range targets {
        if t.Placed {
            placed = append(placed, t)
        } else {
            unplaced = append(unplaced, t)
        }
    }
    if len(unplaced) == 0 {
        return targets
    }
    used := make([]bool, len(unplaced))
    result := make([]Target, 0, len(unplaced))
    cur := start
    for step := 0; step < len(unplaced); step++ {
        best := 0
        bestd := math.MaxFloat64
        for i, t := range unplaced {
            if used[i] {
                continue
            }
            d := math.Hypot(t.X-cur.X, t.Z-cur.Y)
            if d < bestd {
                bestd = d
                best = i
            }
        }
        used[best] = true
        result = append(result, unplaced[best])
        cur = Point{unplaced[best].X, unplaced[best].Z}
    }
    placed = append(placed, result...)
    return placed
}

func SCurve(distance, vMax, aMax, dt float64) []float64 {
    if math.Abs(distance) < 1e-9 {
        return []float64{0}
    }
    tAcc := vMax / aMax
    dAcc := 0.5 * vMax * tAcc
    tConst := 0.0
    if 2*dAcc <= distance {
        tConst = (distance - 2*dAcc) / vMax
    } else {
        tAcc = math.Sqrt(distance / aMax)
    }
    tTotal := 2*tAcc + tConst
    n := int(math.Ceil(tTotal / dt))
    if n < 2 {
        n = 2
    }
    out := make([]float64, n)
    for i := 0; i < n; i++ {
        t := float64(i) * dt
        var p float64
        if t < tAcc {
            p = 0.5 * aMax * t * t
        } else if t < tAcc+tConst {
            p = dAcc + vMax*(t-tAcc)
        } else {
            tau := tTotal - t
            p = distance - 0.5*aMax*tau*tau
        }
        if p < 0 {
            p = 0
        }
        if p > distance {
            p = distance
        }
        out[i] = p
    }
    if out[n-1] > 0 {
        scale := distance / out[n-1]
        for i := range out {
            out[i] *= scale
        }
    }
    return out
}
