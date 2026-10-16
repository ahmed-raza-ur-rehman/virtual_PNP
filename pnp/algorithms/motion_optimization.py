"""Motion optimization: velocity profiling, collision avoidance, jerk smoothing."""

import numpy as np


def smooth_velocity(vel: np.ndarray, max_jerk: float, dt: float) -> np.ndarray:
    """Limit jerk in a velocity signal."""
    vel = np.asarray(vel, dtype=float).copy()
    acc = np.gradient(vel, dt)
    jerk = np.gradient(acc, dt)
    # clip jerk
    jerk = np.clip(jerk, -max_jerk, max_jerk)
    # integrate back
    acc = np.cumsum(jerk) * dt
    vel2 = vel[0] + np.cumsum(acc) * dt
    return vel2


def min_time_trajectory(points: np.ndarray, v_max: float, a_max: float) -> np.ndarray:
    """Compute minimum-time traversal using bang-bang acceleration (simplified)."""
    pts = np.asarray(points, dtype=float)
    n = len(pts)
    if n < 2:
        return pts
    # cumulative distance
    segs = np.diff(pts, axis=0)
    dists = np.hypot(segs[:, 0], segs[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(dists)])
    total = cum[-1]
    # bang-bang: accel then decel
    t_acc = v_max / a_max
    d_acc = 0.5 * a_max * t_acc**2
    if 2*d_acc >= total:
        t_total = 2*np.sqrt(total/a_max)
    else:
        t_total = 2*t_acc + (total-2*d_acc)/v_max
    # sample
    N = max(2, int(np.ceil(t_total/0.01)))
    ts = np.linspace(0, t_total, N)
    s = np.zeros(N)
    for i,t in enumerate(ts):
        if t < t_acc:
            s[i] = 0.5*a_max*t*t
        elif t < t_total - t_acc:
            s[i] = d_acc + v_max*(t-t_acc)
        else:
            tau = t_total - t
            s[i] = total - 0.5*a_max*tau*tau
    s = np.clip(s, 0, total)
    # map s to xy via linear interpolation along polyline
    x = np.interp(s, cum, pts[:, 0])
    y = np.interp(s, cum, pts[:, 1])
    return np.column_stack([x, y])


def collision_free(points: np.ndarray, obstacles: list[tuple[float,float,float]]) -> bool:
    """Check if polyline avoids circular obstacles."""
    pts = np.asarray(points, dtype=float)
    for i in range(len(pts)-1):
        for (ox, oy, r) in obstacles:
            # distance from segment to point
            a = pts[i]; b = pts[i+1]
            ab = b-a
            t = np.dot(np.array([ox,oy])-a, ab) / (np.dot(ab,ab)+1e-12)
            t = np.clip(t, 0, 1)
            closest = a + t*ab
            if np.hypot(closest[0]-ox, closest[1]-oy) < r:
                return False
    return True
