"""Multi-objective optimization (NSGA-II style) for speed vs accuracy."""
from __future__ import annotations

from collections.abc import Callable

import numpy as np


def dominates(a, b):
    # a, b are objective vectors (minimize all)
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def nsga2(population: list, objectives: Callable, generations: int = 50) -> list:
    """Simple NSGA-II: returns Pareto front."""
    pop = list(population)
    for _ in range(generations):
        # evaluate
        objs = [objectives(ind) for ind in pop]
        # non-dominated sort
        fronts = [[]]
        for i in range(len(pop)):
            dom_count = 0
            for j in range(len(pop)):
                if dominates(objs[j], objs[i]):
                    dom_count += 1
            if dom_count == 0:
                fronts[0].append(i)
        # keep only first front (Pareto)
        new_pop = [pop[i] for i in fronts[0]]
        # mutation: small perturbation
        for ind in list(new_pop):
            mut = mutate(ind)
            new_pop.append(mut)
        # trim
        if len(new_pop) > len(population):
            new_pop = new_pop[:len(population)]
        pop = new_pop
    # final pareto
    objs = [objectives(ind) for ind in pop]
    pareto = [pop[i] for i in range(len(pop)) if not any(dominates(objs[j], objs[i]) for j in range(len(pop)) if j != i)]
    return pareto


def mutate(ind):
    if isinstance(ind, np.ndarray):
        return ind + np.random.normal(0, 0.1, ind.shape)
    return ind
