"""Metaheuristic optimization algorithms."""
from __future__ import annotations

import math
import random
from collections.abc import Callable
from typing import Any

import numpy as np


class GeneticAlgorithm:
    def __init__(self, fitness: Callable, gene_length: int, pop_size: int = 50, mutation_rate: float = 0.01, crossover_rate: float = 0.8):
        self.fitness = fitness
        self.gene_length = gene_length
        self.pop_size = pop_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.population: list[np.ndarray] = []
        self.best = None
        self.best_fitness = float("-inf")
        self.history: list[float] = []

    def init_population(self):
        self.population = [np.random.randint(0, 2, self.gene_length).astype(float) for _ in range(self.pop_size)]

    def evaluate(self) -> list[float]:
        return [self.fitness(ind) for ind in self.population]

    def select(self, fitnesses: list[float]) -> np.ndarray:
        # tournament selection
        i, j = random.sample(range(self.pop_size), 2)
        return self.population[i] if fitnesses[i] > fitnesses[j] else self.population[j]

    def crossover(self, p1: np.ndarray, p2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if random.random() > self.crossover_rate:
            return p1.copy(), p2.copy()
        point = random.randint(1, self.gene_length - 1)
        c1 = np.concatenate([p1[:point], p2[point:]])
        c2 = np.concatenate([p2[:point], p1[point:]])
        return c1, c2

    def mutate(self, ind: np.ndarray) -> np.ndarray:
        for i in range(self.gene_length):
            if random.random() < self.mutation_rate:
                ind[i] = 1 - ind[i]
        return ind

    def run(self, generations: int = 100) -> np.ndarray:
        self.init_population()
        for gen in range(generations):
            fitnesses = self.evaluate()
            for ind, f in zip(self.population, fitnesses):
                if f > self.best_fitness:
                    self.best_fitness = f
                    self.best = ind.copy()
            self.history.append(self.best_fitness)
            new_pop = []
            while len(new_pop) < self.pop_size:
                p1 = self.select(fitnesses)
                p2 = self.select(fitnesses)
                c1, c2 = self.crossover(p1, p2)
                new_pop.append(self.mutate(c1))
                if len(new_pop) < self.pop_size:
                    new_pop.append(self.mutate(c2))
            self.population = new_pop
        return self.best


class SimulatedAnnealing:
    def __init__(self, cost: Callable, neighbor: Callable, T0: float = 100.0, alpha: float = 0.99, max_iters: int = 10000):
        self.cost = cost
        self.neighbor = neighbor
        self.T0 = T0
        self.alpha = alpha
        self.max_iters = max_iters
        self.best = None
        self.best_cost = float("inf")
        self.history: list[float] = []

    def run(self, x0: Any) -> Any:
        x = x0
        cur_cost = self.cost(x)
        self.best = x
        self.best_cost = cur_cost
        T = self.T0
        for it in range(self.max_iters):
            xn = self.neighbor(x)
            cn = self.cost(xn)
            delta = cn - cur_cost
            if delta < 0 or random.random() < math.exp(-delta / max(T, 1e-9)):
                x = xn
                cur_cost = cn
                if cn < self.best_cost:
                    self.best = xn
                    self.best_cost = cn
            T *= self.alpha
            self.history.append(self.best_cost)
        return self.best


class ParticleSwarm:
    def __init__(self, cost: Callable, dim: int, num_particles: int = 30, w: float = 0.7, c1: float = 1.5, c2: float = 1.5, max_iters: int = 100):
        self.cost = cost
        self.dim = dim
        self.num_particles = num_particles
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.max_iters = max_iters
        self.best_global = None
        self.best_global_cost = float("inf")
        self.history: list[float] = []

    def run(self, bounds: tuple[float, float] = (-5, 5)) -> np.ndarray:
        lo, hi = bounds
        X = np.random.uniform(lo, hi, (self.num_particles, self.dim))
        V = np.random.uniform(-1, 1, (self.num_particles, self.dim))
        pbest = X.copy()
        pbest_cost = np.array([self.cost(x) for x in X])
        gbest_idx = np.argmin(pbest_cost)
        gbest = X[gbest_idx].copy()
        gbest_cost = pbest_cost[gbest_idx]
        for it in range(self.max_iters):
            for i in range(self.num_particles):
                r1, r2 = random.random(), random.random()
                V[i] = self.w * V[i] + self.c1 * r1 * (pbest[i] - X[i]) + self.c2 * r2 * (gbest - X[i])
                X[i] += V[i]
                X[i] = np.clip(X[i], lo, hi)
                c = self.cost(X[i])
                if c < pbest_cost[i]:
                    pbest[i] = X[i].copy()
                    pbest_cost[i] = c
                    if c < gbest_cost:
                        gbest = X[i].copy()
                        gbest_cost = c
            self.history.append(gbest_cost)
        self.best_global = gbest
        self.best_global_cost = gbest_cost
        return gbest


class AntColony:
    def __init__(self, dist_matrix: np.ndarray, num_ants: int = 20, alpha: float = 1.0, beta: float = 2.0, rho: float = 0.5, Q: float = 100.0, max_iters: int = 100):
        self.dist = dist_matrix
        self.n = len(dist_matrix)
        self.num_ants = num_ants
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.Q = Q
        self.max_iters = max_iters
        self.pheromone = np.ones((self.n, self.n))
        self.best_tour = None
        self.best_length = float("inf")
        self.history: list[float] = []

    def _tour_length(self, tour: list[int]) -> float:
        total = 0.0
        for i in range(len(tour)):
            total += self.dist[tour[i], tour[(i+1) % len(tour)]]
        return total

    def run(self) -> list[int]:
        for it in range(self.max_iters):
            tours = []
            for _ in range(self.num_ants):
                tour = self._construct_tour()
                tours.append(tour)
                L = self._tour_length(tour)
                if L < self.best_length:
                    self.best_length = L
                    self.best_tour = tour.copy()
            # update pheromones
            self.pheromone *= (1 - self.rho)
            for tour in tours:
                L = self._tour_length(tour)
                for i in range(len(tour)):
                    a, b = tour[i], tour[(i+1) % len(tour)]
                    self.pheromone[a, b] += self.Q / L
                    self.pheromone[b, a] += self.Q / L
            self.history.append(self.best_length)
        return self.best_tour

    def _construct_tour(self) -> list[int]:
        tour = [random.randrange(self.n)]
        visited = set(tour)
        while len(tour) < self.n:
            cur = tour[-1]
            probs = []
            for j in range(self.n):
                if j in visited:
                    probs.append(0.0)
                    continue
                tau = self.pheromone[cur, j] ** self.alpha
                eta = (1.0 / (self.dist[cur, j] + 1e-9)) ** self.beta
                probs.append(tau * eta)
            total = sum(probs)
            if total == 0:
                # pick random unvisited
                remaining = [j for j in range(self.n) if j not in visited]
                nxt = random.choice(remaining)
            else:
                probs = [p / total for p in probs]
                nxt = random.choices(range(self.n), weights=probs)[0]
                while nxt in visited:
                    nxt = random.randrange(self.n)
            tour.append(nxt)
            visited.add(nxt)
        return tour


class TabuSearch:
    def __init__(self, cost: Callable, neighbor: Callable, tabu_size: int = 10, max_iters: int = 1000):
        self.cost = cost
        self.neighbor = neighbor
        self.tabu_size = tabu_size
        self.max_iters = max_iters
        self.tabu_list: list[Any] = []
        self.best = None
        self.best_cost = float("inf")

    def run(self, x0: Any) -> Any:
        x = x0
        cur_cost = self.cost(x)
        self.best = x
        self.best_cost = cur_cost
        for it in range(self.max_iters):
            # generate neighbors
            best_nb = None
            best_nb_cost = float("inf")
            for _ in range(20):
                nb = self.neighbor(x)
                if nb in self.tabu_list:
                    continue
                c = self.cost(nb)
                if c < best_nb_cost:
                    best_nb_cost = c
                    best_nb = nb
            if best_nb is None:
                break
            x = best_nb
            cur_cost = best_nb_cost
            self.tabu_list.append(best_nb)
            if len(self.tabu_list) > self.tabu_size:
                self.tabu_list.pop(0)
            if cur_cost < self.best_cost:
                self.best = x
                self.best_cost = cur_cost
        return self.best


class DifferentialEvolution:
    def __init__(self, cost: Callable, dim: int, bounds: tuple[float, float] = (-5, 5), pop_size: int = 50, F: float = 0.8, CR: float = 0.9, max_iters: int = 100):
        self.cost = cost
        self.dim = dim
        self.bounds = bounds
        self.pop_size = pop_size
        self.F = F
        self.CR = CR
        self.max_iters = max_iters
        self.best = None
        self.best_cost = float("inf")

    def run(self) -> np.ndarray:
        lo, hi = self.bounds
        pop = np.random.uniform(lo, hi, (self.pop_size, self.dim))
        fitness = np.array([self.cost(p) for p in pop])
        best_idx = np.argmin(fitness)
        self.best = pop[best_idx].copy()
        self.best_cost = fitness[best_idx]
        for it in range(self.max_iters):
            for i in range(self.pop_size):
                # mutation
                idxs = [j for j in range(self.pop_size) if j != i]
                a, b, c = np.random.choice(idxs, 3, replace=False)
                mutant = pop[a] + self.F * (pop[b] - pop[c])
                mutant = np.clip(mutant, lo, hi)
                # crossover
                trial = pop[i].copy()
                jrand = np.random.randint(self.dim)
                for j in range(self.dim):
                    if np.random.rand() < self.CR or j == jrand:
                        trial[j] = mutant[j]
                f_trial = self.cost(trial)
                if f_trial < fitness[i]:
                    pop[i] = trial
                    fitness[i] = f_trial
                    if f_trial < self.best_cost:
                        self.best = trial.copy()
                        self.best_cost = f_trial
        return self.best
