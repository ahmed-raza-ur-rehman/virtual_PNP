#include "pnp.hpp"
#include <cassert>
#include <iostream>

int main() {
    using namespace pnp;
    std::vector<Target> ts;
    for (int i = 0; i < 10; ++i) ts.push_back({i, "0402", i*5.0, 0.0, false});
    auto opt = optimize_placement(ts, {0,0});
    assert(opt.size() == 10);
    auto sc = s_curve(100, 200, 100, 500, 0.01);
    assert(sc.size() > 1);
    assert(std::abs(sc.back() - 100.0) < 1e-6);
    std::cout << "C++ tests passed\n";
    return 0;
}
