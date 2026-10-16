import numpy as np

from pnp.optimization.advanced import genetic_algorithm, nsga2, simulated_annealing


def test_sa():
    def cost(x):
        return float(np.sum(x**2))
    x0 = np.array([5.0, -3.0])
    _x, c = simulated_annealing(cost, x0, iters=200)
    assert c < 40


def test_ga():
    def cost(x):
        return float(np.sum(x**2))
    _x, c = genetic_algorithm(cost, 2, generations=50)
    assert c < 10


def test_nsga2_advanced():
    def f1(x):
        return float(np.sum(x**2))
    def f2(x):
        return float(np.sum((x - 1)**2))
    xs, _fs = nsga2([f1, f2], 2, generations=20)
    assert len(xs) > 0
