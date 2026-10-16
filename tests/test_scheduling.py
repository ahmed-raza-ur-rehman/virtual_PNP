from pnp.optimization.scheduling import makespan, schedule_multihead


def test_schedule():
    tasks = [{"id": i, "duration": 1.0, "ready_time": 0.0} for i in range(8)]
    sched = schedule_multihead(tasks, heads=4)
    assert len(sched) == 4
    assert makespan(sched) <= 3.0
