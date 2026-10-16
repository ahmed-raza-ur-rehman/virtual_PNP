// ---------------------------------------------------------------------------
// pnp_defs.vh - global compile-time contract for the PnP control core.
//
// Coordinate system (see docs/ICD.md):
//   * positions are 32-bit signed Q12.4 fixed point in micrometres,
//     i.e. 1 LSB = 1/16 um = 62.5 nm.
//   * velocities are Q12.4 um/s, accelerations Q12.4 um/s^2.
//   * angles are Q8.8 degrees, 1 LSB = 1/256 deg.
//
// Every module that crosses the core boundary includes this file so that a
// width or scaling change is made in exactly one place.
// ---------------------------------------------------------------------------
`ifndef PNP_DEFS_VH
`define PNP_DEFS_VH

// ---- fixed-point formats -------------------------------------------------
`define PNP_POS_W        32   // Q12.4 position / velocity / acceleration word
`define PNP_FRAC_W       4    // fractional bits of the Q12.4 format
`define PNP_ANG_W        16   // Q8.8 angle word
`define PNP_ANG_FRAC_W   8

// ---- axis geometry -------------------------------------------------------
`define PNP_NUM_AXES     3    // X, Y, Z  (R is generated from the vision pipe)
`define PNP_AXIS_W       2

// ---- control loop --------------------------------------------------------
`define PNP_SAMPLE_W     16   // position error integrator width
`define PNP_DUTY_W       16   // PWM / DDA duty resolution

// ---- bus / protocol ------------------------------------------------------
`define PNP_ADDR_W       8
`define PNP_DATA_W       32

// ---- machine limits encoded in RTL so firmware and FPGA cannot disagree ---
// (millimetres converted to the Q12.4 micrometre format)
`define PNP_X_MIN        (-32'sd500000)
`define PNP_X_MAX        ( 32'sd500000)
`define PNP_Y_MIN        (-32'sd400000)
`define PNP_Y_MAX        ( 32'sd400000)
`define PNP_Z_MIN        (-32'sd120000)
`define PNP_Z_MAX        ( 32'sd120000)

`endif // PNP_DEFS_VH
