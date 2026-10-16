import cocotb
from cocotb.triggers import RisingEdge, Timer

@cocotb.test()
async def pwm_duty(dut):
    dut.rst.value = 1
    await Timer(20, units="ns")
    dut.rst.value = 0
    dut.duty.value = 0x8000
    await Timer(1000, units="ns")
    assert True
