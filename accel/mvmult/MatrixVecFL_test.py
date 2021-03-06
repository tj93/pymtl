#==============================================================================
# MatrixVecFL_test
#==============================================================================

import pytest

from pymtl        import *
from pclib.test   import TestSource, TestMemory
from pclib.ifcs import mem_msgs
from MatrixVecFL  import MatrixVecFL

#------------------------------------------------------------------------------
# SourceHarness
#------------------------------------------------------------------------------
class SourceHarness( Model ):

  def __init__( s, nlanes, nmul_stages, mem_delay, src_delay, config_msgs ):

    cop_addr_nbits = 5
    cop_data_nbits = 32
    mem_addr_nbits = 32
    mem_data_nbits = 32

    memreq_params  = mem_msgs.MemReqParams( mem_addr_nbits, mem_data_nbits )
    memresp_params = mem_msgs.MemRespParams( mem_data_nbits )

    s.src   = TestSource  ( cop_addr_nbits + cop_data_nbits,
                            config_msgs, src_delay )
    s.cop   = MatrixVecFL( nlanes, nmul_stages,
                           cop_addr_nbits, cop_data_nbits,
                           mem_addr_nbits, mem_data_nbits )
    s.mem   = TestMemory  ( memreq_params, memresp_params,
                            nlanes, mem_delay )

    assert nlanes > 0
    s.nlanes = nlanes

  def elaborate_logic( s ):

    for i in range( s.nlanes ):
      s.connect( s.src.out,          s.cop.from_cpu )
      s.connect( s.cop.lane_req [i], s.mem.reqs [i] )
      s.connect( s.cop.lane_resp[i], s.mem.resps[i] )

  def done( s ):
    return s.src.done and s.cop.from_cpu.rdy

  def line_trace( s ):
    return "{} || {}".format( s.src.line_trace(), s.mem.line_trace() )

#------------------------------------------------------------------------------
# run_lane_managed_test
#------------------------------------------------------------------------------
def run_lane_managed_test( dump_vcd, model,
                           src_matrix, src_vector, dest_vector ):

  model.vcd_file = dump_vcd
  model.elaborate()

  sim = SimulationTool( model )

  # Load the memory

  model.mem.load_memory( src_matrix  )
  model.mem.load_memory( src_vector  )

  # Run the simulation

  sim.reset()

  print
  while not model.done() and sim.ncycles < 80:
    sim.print_line_trace()
    sim.cycle()

  assert model.done()

  dest_addr   = dest_vector[0]
  for i, dest_value in enumerate( dest_vector[1] ):
    assert model.mem.mem.mem[ dest_addr+i ] == dest_value

  # Add a couple extra ticks so that the VCD dump is nicer

  sim.cycle()
  sim.cycle()
  sim.cycle()

#------------------------------------------------------------------------------
# config_msg
#------------------------------------------------------------------------------
# Utility method for creating config messages
def config_msg( addr, value ):
  return concat( Bits(3, addr), Bits(32, value) )

#------------------------------------------------------------------------------
# mem_array_32bit
#------------------------------------------------------------------------------
# Utility function for creating arrays formatted for memory loading.
from itertools import chain
def mem_array_32bit( base_addr, data ):
  return [base_addr,
          list( chain.from_iterable([ [x,0,0,0] for x in data ] ))
         ]


#------------------------------------------------------------------------------
# test_managed
#------------------------------------------------------------------------------
#  5 1 3   1    16
#  1 1 1 . 2  =  6
#  1 2 1   3     8
#
@pytest.mark.parametrize(
  ('mem_delay','nmul_stages'), [(0,1),(0,4),(5,1),(5,4)]
)
def test_managed_1lane( dump_vcd, mem_delay, nmul_stages ):
  run_lane_managed_test( dump_vcd,
                  SourceHarness( 1, nmul_stages, mem_delay, 0,
                     [ config_msg( 1,   3), # size
                       config_msg( 2,   0), # r_addr
                       config_msg( 3,  80), # v_addr
                       config_msg( 4, 160), # d_addr
                       config_msg( 0,   1), # go
                     ],
                   ),
                   # NOTE: C++ has dummy data between rows when you have array**!
                   mem_array_32bit(  0, [ 5, 1 ,3, 99,
                                          1, 1 ,1, 99,
                                          1, 2 ,1] ),
                   mem_array_32bit( 80, [ 1, 2, 3 ]),
                   mem_array_32bit(160, [16]),
                 )

@pytest.mark.parametrize(
  ('mem_delay','nmul_stages'), [(0,1),(0,4),(5,1),(5,4)]
)
def test_managed_3lane( dump_vcd,  mem_delay, nmul_stages ):
  run_lane_managed_test( dump_vcd,
                  SourceHarness( 3, nmul_stages, mem_delay, 0,
                     [ config_msg( 1,   3), # size
                       config_msg( 2,   0), # r_addr
                       config_msg( 3,  80), # v_addr
                       config_msg( 4, 160), # d_addr
                       config_msg( 0,   1), # go
                     ],
                   ),
                   # NOTE: C++ has dummy data between rows when you have array**!
                   mem_array_32bit(  0, [ 5, 1 ,3, 99,
                                          1, 1 ,1, 99,
                                          1, 2 ,1] ),
                   mem_array_32bit( 80, [ 1, 2, 3 ]),
                   mem_array_32bit(160, [16, 6, 8 ]),
                 )
