#include "pnp.hpp"
#include <algorithm>
#include <limits>

namespace pnp {

double path_length(const std::vector<Point>& pts) {
    double d = 0;
    for (size_t i = 1; i < pts.size(); ++i) {
        double dx = pts[i].x - pts[i-1].x;
        double dy = pts[i].y - pts[i-1].y;
        d += std::hypot(dx, dy);
    }
    return d;
}

std::vector<Target> optimize_placement(const std::vector<Target>& targets, Point start) {
    std::vector<Target> placed, unplaced;
    for (auto &t : targets) (t.placed ? placed : unplaced).push_back(t);
    if (unplaced.empty()) return targets;
    // nearest neighbor
    std::vector<Target> result;
    std::vector<char> used(unplaced.size(), 0);
    Point cur = start;
    for (size_t step = 0; step < unplaced.size(); ++step) {
        size_t best = 0; double bestd = std::numeric_limits<double>::max();
        for (size_t i = 0; i < unplaced.size(); ++i) {
            if (used[i]) continue;
            double d = std::hypot(unplaced[i].x - cur.x, unplaced[i].z - cur.y);
            if (d < bestd) { bestd = d; best = i; }
        }
        used[best] = 1;
        result.push_back(unplaced[best]);
        cur = {unplaced[best].x, unplaced[best].z};
    }
    // 2-opt
    auto plen = [&](const std::vector<Target>& seq) {
        Point c = start; double d = 0;
        for (auto &t : seq) { d += std::hypot(t.x - c.x, t.z - c.y); c = {t.x, t.z}; }
        return d;
    };
    bool improved = true;
    while (improved) {
        improved = false;
        for (size_t i = 1; i + 1 < result.size(); ++i) {
            for (size_t j = i + 1; j < result.size(); ++j) {
                std::vector<Target> cand = result;
                std::reverse(cand.begin() + i, cand.begin() + j + 1);
                if (plen(cand) < plen(result) - 1e-12) { result = cand; improved = true; }
            }
        }
    }
    placed.insert(placed.end(), result.begin(), result.end());
    return placed;
}

std::vector<double> s_curve(double distance, double v_max, double a_max, double j_max, double dt) {
    std::vector<double> pos;
    if (distance < 1e-9) { pos.push_back(0); return pos; }
    double t_j = a_max / j_max;
    double t_acc = v_max / a_max + t_j;
    double d_acc = 0.5 * v_max * t_acc;
    double t_const = (2*d_acc > distance) ? 0.0 : (distance - 2*d_acc)/v_max;
    if (2*d_acc > distance) t_acc = std::sqrt(distance / a_max);
    double t_total = 2*t_acc + t_const;
    int n = std::max(2, (int)std::ceil(t_total/dt));
    pos.resize(n);
    for (int i = 0; i < n; ++i) {
        double t = i*dt;
        double p;
        if (t < t_acc) p = 0.5*a_max*t*t;
        else if (t < t_acc + t_const) p = d_acc + v_max*(t - t_acc);
        else { double tau = t_total - t; p = distance - 0.5*a_max*tau*tau; }
        pos[i] = std::min(distance, std::max(0.0, p));
    }
    if (pos.back() > 0) for (auto &p : pos) p = p / pos.back() * distance;
    return pos;
}

}
