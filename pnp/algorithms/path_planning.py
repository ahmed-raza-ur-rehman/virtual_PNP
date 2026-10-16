"""S-curve and trapezoidal path planning with jerk limits."""
import numpy as np


def trapezoidal_profile(distance: float, v_max: float, a_max: float, dt: float):
    """Generate trapezoidal velocity profile samples."""
    distance = abs(distance)
    if distance < 1e-9:
        return np.array([0.0]), np.array([0.0])
    # time to reach v_max
    t_acc = v_max / a_max
    d_acc = 0.5 * a_max * t_acc * t_acc
    if 2 * d_acc > distance:
        # triangular
        t_acc = np.sqrt(distance / a_max)
        t_total = 2 * t_acc
    else:
        t_const = (distance - 2 * d_acc) / v_max
        t_total = 2 * t_acc + t_const
    n = max(1, int(np.ceil(t_total / dt)))
    ts = np.linspace(0, t_total, n)
    pos = np.zeros(n)
    vel = np.zeros(n)
    for i, t in enumerate(ts):
        if t < t_acc:
            pos[i] = 0.5 * a_max * t * t
            vel[i] = a_max * t
        elif t < t_total - t_acc:
            pos[i] = d_acc + v_max * (t - t_acc)
            vel[i] = v_max
        else:
            tau = t_total - t
            pos[i] = distance - 0.5 * a_max * tau * tau
            vel[i] = a_max * tau
    return pos, vel


def s_curve_profile(distance: float, v_max: float, a_max: float, j_max: float, dt: float):
    """Jerk-limited S-curve profile."""
    distance = abs(distance)
    if distance < 1e-9:
        return np.array([0.0]), np.array([0.0]), np.array([0.0])
    # phase durations
    t_j = a_max / j_max  # jerk phase
    # peak accel
    a_peak = j_max * t_j
    if a_peak > a_max:
        a_peak = a_max
        t_j = a_max / j_max
    # time to reach v_max
    # distance during accel phase
    # accel phase: jerk up/down
    j_max * t_j**3 / 6.0  # per jerk segment? approximate
    # Use standard S-curve formulas (simplified)
    # total accel time to reach v_max
    if v_max <= a_peak * (t_j + (a_peak/j_max if False else 0)):
        # triangular velocity (no cruise)
        pass
    # Simplified: compute t_acc such that velocity reaches v_max
    # accel phase duration (ramp up + const accel + ramp down) 
    t_acc = v_max / a_max + t_j  # approx
    d_acc = 0.5 * (v_max) * t_acc  # approx area
    if 2 * d_acc > distance:
        # no cruise
        t_acc = np.sqrt(distance / (a_max * 0.8))
        t_const = 0.0
    else:
        t_const = (distance - 2 * d_acc) / v_max
    t_total = 2 * t_acc + t_const
    n = max(1, int(np.ceil(t_total / dt)))
    ts = np.linspace(0, t_total, n)
    pos = np.zeros(n); vel = np.zeros(n); acc = np.zeros(n)
    for i, t in enumerate(ts):
        if t < t_j:
            acc[i] = j_max * t
            vel[i] = 0.5 * j_max * t * t
            pos[i] = j_max * t**3 / 6.0
        elif t < t_acc - t_j:
            acc[i] = a_peak
            vel[i] = 0.5 * a_peak * t_j + a_peak * (t - t_j)
            pos[i] = j_max * t_j**3 / 6.0 + 0.5 * a_peak * t_j * (t - t_j) + 0.5 * a_peak * (t - t_j)**2  # approx
        elif t < t_acc:
            tau = t_acc - t
            acc[i] = j_max * tau
            vel[i] = v_max - 0.5 * j_max * tau * tau
            pos[i] = distance*0  # placeholder
        elif t < t_acc + t_const:
            acc[i] = 0
            vel[i] = v_max
            pos[i] = d_acc + v_max * (t - t_acc)
        else:
            # decel mirror
            td = t - (t_acc + t_const)
            if td < t_j:
                acc[i] = -j_max * td
                vel[i] = v_max - 0.5 * j_max * td * td
            elif td < t_acc - t_j:
                acc[i] = -a_peak
                vel[i] = v_max - (0.5 * a_peak * t_j + a_peak * (td - t_j))
            else:
                tau = t_total - t
                acc[i] = j_max * tau
                vel[i] = 0.5 * j_max * tau * tau
            pos[i] = distance - (t_total - t) * v_max * 0.5  # approx
    # normalize pos to exact distance
    pos = np.clip(np.cumsum(np.gradient(pos)), 0, distance) if n > 1 else pos
    if pos[-1] > 0:
        pos = pos / pos[-1] * distance
    return pos, vel, acc


def plan_path(waypoints: np.ndarray, v_max=200.0, a_max=100.0, j_max=500.0, dt=0.01):
    """Plan full path through waypoints using S-curve segments."""
    wps = np.asarray(waypoints, dtype=float)
    segments = []
    for i in range(len(wps)-1):
        d = float(np.hypot(wps[i+1,0]-wps[i,0], wps[i+1,1]-wps[i,1]))
        pos, vel, acc = s_curve_profile(d, v_max, a_max, j_max, dt)
        # orient
        ang = np.arctan2(wps[i+1,1]-wps[i,1], wps[i+1,0]-wps[i,0])
        xs = wps[i,0] + pos * np.cos(ang)
        ys = wps[i,1] + pos * np.sin(ang)
        segments.append({'t': np.arange(len(pos))*dt, 'x': xs, 'y': ys, 'vel': vel, 'acc': acc})
    return segments
