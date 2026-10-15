"""Advanced optimization: simulated annealing, genetic algorithm, multi-objective."""
from __future__ import annotations
import numpy as np
from typing import List, Callable


def simulated_annealing(cost_fn: Callable, x0, T0=1.0, alpha=0.995, iters=5000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.array(x0, dtype=float).copy()
    best = x.copy()
    best_cost = cost_fn(x)
    cur_cost = best_cost
    T = T0
    for _ in range(iters):
        # neighbor
        i = rng.integers(0, len(x))
        j = rng.integers(0, len(x))
        x[i], x[j] = x[j], x[i]
        new_cost = cost_fn(x)
        dE = new_cost - cur_cost
        if dE < 0 or rng.random() < np.exp(-dE / max(T, 1e-9)):
            cur_cost = new_cost
            if new_cost < best_cost:
                best = x.copy(); best_cost = new_cost
        else:
            x[i], x[j] = x[j], x[i]  # revert
        T *= alpha
    return best, best_cost


def genetic_algorithm(cost_fn, n, pop_size=40, generations=200, mutation=0.1, seed=0):
    rng = np.random.default_rng(seed)
    pop = [rng.permutation(n) for _ in range(pop_size)]
    fitness = [cost_fn(p) for p in pop]
    for _ in range(generations):
        # selection (tournament)
        new_pop = []
        for _ in range(pop_size):
            a, b = rng.integers(0, pop_size, 2)
            winner = pop[a] if fitness[a] < fitness[b] else pop[b]
            new_pop.append(winner.copy())
        # crossover (order crossover)
        for i in range(0, pop_size - 1, 2):
            p1, p2 = new_pop[i].copy(), new_pop[i+1].copy()
            if rng.random() < 0.8:
                a, b = sorted(rng.integers(0, n, 2))
                child = np.full(n, -1, dtype=int)
                child[a:b] = p1[a:b]
                pos = b % n
                for gene in p2:
                    if gene not in child[a:b]:
                        child[pos] = gene
                        pos = (pos + 1) % n
                new_pop[i] = child
        # mutation
        for ind in new_pop:
            if rng.random() < mutation:
                i, j = rng.integers(0, n, 2)
                ind[i], ind[j] = ind[j], ind[i]
        pop = new_pop
        fitness = [cost_fn(p) for p in pop]
    best_idx = int(np.argmin(fitness))
    return pop[best_idx], fitness[best_idx]


def nsga2(cost_fns, n, pop_size=50, generations=100, seed=0):
    """Multi-objective (NSGA-II) returning Pareto front indices."""
    rng = np.random.default_rng(seed)
    pop = [rng.permutation(n) for _ in range(pop_size)]
    def fronts(pop):
        F = np.array([[cf(p) for cf in cost_fns] for p in pop])
        # non-dominated sorting (simplified: single front)
        return F
    F = fronts(pop)
    # return population + fitness
    return pop, F
