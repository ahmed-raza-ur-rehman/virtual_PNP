#pragma once
#include <vector>
#include <cmath>
#include <string>

namespace pnp {

struct Point { double x, y; };

struct Target {
    int id;
    std::string type;
    double x, z;
    bool placed = false;
};

std::vector<Target> optimize_placement(const std::vector<Target>& targets, Point start);
std::vector<double> s_curve(double distance, double v_max, double a_max, double j_max, double dt);
double path_length(const std::vector<Point>& pts);

}
