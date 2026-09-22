Run OPM Flow in parallel from Python
====================================

:doc:`flow-in-python` shows how to drive a simulation from a single Python
process. This page covers running the same simulation across several MPI ranks.

Prerequisites
-------------

This page assumes you can already run a serial simulation from Python. See
:doc:`flow-in-python` for compiling Flow with Python support and for setting
``PYTHONPATH``.

Running in parallel needs three things in addition:

- **MPI enabled in the build.** Add ``-DUSE_MPI=ON`` to the cmake flags
  alongside ``-DOPM_ENABLE_PYTHON=ON`` and ``-DOPM_INSTALL_PYTHON=ON``.

- **A graph partitioner** present at configure time, either Zoltan or
  ParMETIS. Without one, the grid cannot be distributed across ranks.

- **mpi4py** installed in the same Python environment as the ``opm`` module.
  See the `mpi4py documentation <https://mpi4py.readthedocs.io/>`_.


A script for parallel run example
----------------------

.. code-block:: python

   from opm.simulators import BlackOilSimulator

   # mpi4py owns MPI_Init/MPI_Finalize; importing it initialises MPI for the
   # whole process, including the simulator underneath.
   from mpi4py import MPI

   COMM = MPI.COMM_WORLD
   RANK = COMM.Get_rank()

   CASE = "SPE1CASE1.DATA"


   def main():
       sim = BlackOilSimulator(filename=CASE)

       # init=False: MPI is already initialised by mpi4py.
       # finalize=False: keep MPI alive until the script exits.
       sim.setup_mpi(init=False, finalize=False)

       # sim_step_init() return 1 is fail. So we have to check abit
       rc = sim.step_init()
       if rc != 0:
           raise RuntimeError(f"step_init() failed with code {rc} on rank {RANK}")

       sim.step()

       # The grid is distributed, so each rank sees only its own cells
       # (owned + overlap).
       poro = sim.get_porosity()
       sim.set_porosity(poro * 0.95)

       sim.step()

       sim.step_cleanup()

       if RANK == 0:
           print("done -- results written to SPE1CASE1.PRT", flush=True)


   if __name__ == "__main__":
       main()


Run it with:

.. code-block:: bash

   mpirun -np 4 python3 my_script.py

and confirm the rank count in the print file:

.. code-block:: bash

   grep "Number of MPI processes" SPE1CASE1.PRT


Good to know
------------

The rest of this page covers behaviour that is easy to get wrong,
and the reasons behind the recommendations above.

Initialising MPI
~~~~~~~~~~~~~~~~

``setup_mpi()`` takes two flags, and both matter when mpi4py is in use:

.. code-block:: python

   sim.setup_mpi(init=False, finalize=False)

``init=False``
   ``from mpi4py import MPI`` already called ``MPI_Init``. Letting OPM
   initialise MPI a second time is an error.

``finalize=False``
   Leaves MPI running after the simulator shuts down. With ``finalize=True``
   OPM tears MPI down, and any collective call afterwards — including an
   ``allgather`` used for checking results — aborts.



Constructing the simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

   In parallel, only the **filename constructor** works:

   .. code-block:: python

      sim = BlackOilSimulator(filename="SPE1CASE1.DATA")

   The four-argument form documented for serial runs —
   ``BlackOilSimulator(deck, state, schedule, summary_config)`` — cannot run on
   more than one rank.

