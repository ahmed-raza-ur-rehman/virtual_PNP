use nalgebra::Vector2;

#[derive(Clone, Copy, Debug)]
pub struct Target { pub id: usize, pub x: f64, pub z: f64, pub placed: bool }

pub fn optimize_placement(targets: &[Target], start: (f64, f64)) -> Vec<Target> {
    let mut unplaced: Vec<Target> = targets.iter().filter(|t| !t.placed).cloned().collect();
    let mut placed: Vec<Target> = targets.iter().filter(|t| t.placed).cloned().collect();
    if unplaced.is_empty() { return targets.to_vec(); }
    // nearest neighbor
    let mut result = Vec::with_capacity(unplaced.len());
    let mut used = vec![false; unplaced.len()];
    let mut cur = Vector2::new(start.0, start.1);
    for _ in 0..unplaced.len() {
        let mut best = 0; let mut bestd = f64::MAX;
        for (i, t) in unplaced.iter().enumerate() {
            if used[i] { continue; }
            let d = (Vector2::new(t.x, t.z) - cur).norm();
            if d < bestd { bestd = d; best = i; }
        }
        used[best] = true;
        result.push(unplaced[best]);
        cur = Vector2::new(unplaced[best].x, unplaced[best].z);
    }
    // 2-opt
    // (omitted for brevity; see python/cpp)
    placed.extend(result);
    placed
}

pub fn s_curve(distance: f64, v_max: f64, a_max: f64, dt: f64) -> Vec<f64> {
    if distance.abs() < 1e-9 { return vec![0.0]; }
    let t_acc = v_max / a_max;
    let d_acc = 0.5 * v_max * t_acc;
    let t_const = if 2.0 * d_acc > distance { 0.0 } else { (distance - 2.0 * d_acc) / v_max };
    let t_total = 2.0 * t_acc + t_const;
    let n = (t_total / dt).ceil().max(2.0) as usize;
    (0..n).map(|i| {
        let t = i as f64 * dt;
        let p = if t < t_acc { 0.5 * a_max * t * t }
        else if t < t_acc + t_const { d_acc + v_max * (t - t_acc) }
        else { let tau = t_total - t; distance - 0.5 * a_max * tau * tau };
        p.clamp(0.0, distance)
    }).collect()
}
