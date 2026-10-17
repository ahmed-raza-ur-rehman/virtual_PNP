from pnp.eda.flow import EDAFlow


def test_eda_flow():
    src = "module foo (a, b, c); input a, b; output c; assign c = a & b; endmodule"
    flow = EDAFlow()
    result = flow.run(src)
    assert "placement" in result
    assert "routes" in result
    assert result["drc_violations"] >= 0
    import os
    assert result["lvs_errors"] == 0
    assert os.path.exists(result["gds_path"])
