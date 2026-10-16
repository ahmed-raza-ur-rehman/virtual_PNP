# API Reference

## Python
- `pnp.optimization.placement.optimize_placement(targets, start)`
- `pnp.optimization.feeding.optimize_feeders(targets, feeders)`
- `pnp.optimization.feeding.optimize_turntable(targets, slots)`
- `pnp.planning.trajectory.plan_path(waypoints, ...)`
- `pnp.vision.pipeline.detect_fiducials(img)`
- `pnp.vision.pipeline.orientation_angle(img)`

## CLI
`vpnp optimize -i targets.json -o out.json`
`vpnp plan -w "0,0;10,0;10,10"`

## REST
POST /optimize/placement
POST /plan/path
