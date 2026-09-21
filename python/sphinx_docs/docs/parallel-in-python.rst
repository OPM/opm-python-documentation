Run OPM Flow in parallel from Python
====================================

:doc:`flow-in-python` shows how to drive a simulation from a single Python
process. This page covers running the same simulation across several MPI ranks.

Prerequisites
-------------

- Flow compiled with Python support **and** MPI enabled, i.e. the cmake flags
  ``-DOPM_ENABLE_PYTHON=ON``, ``-DOPM_INSTALL_PYTHON=ON`` and ``-DUSE_MPI=ON``.
  See :doc:`flow-in-python` for a sample build script.

- A graph partitioner available at configure time — Zoltan or ParMETIS —
  otherwise the grid cannot be distributed.

- `mpi4py <https://mpi4py.readthedocs.io/>`_ installed in the same Python
  environment as the ``opm`` module.

- ``PYTHONPATH`` pointing at both build trees, since ``opm-common`` provides
  ``opm.io.*`` and ``opm-simulators`` provides ``opm.simulators.*``:

  .. code-block:: bash

     export PYTHONPATH="<opm-common-build>/python:<opm-simulators-build>/python"

  The two merge into one ``opm`` package because neither defines an
  ``__init__.py`` at the ``opm`` level — they are PEP 420 namespace packages.


What ``mpirun`` actually does
-----------------------------

.. code-block:: bash

   mpirun -np 4 python3 my_script.py

This starts **four independent Python interpreters**, not one parallel Python.
Each executes the whole script and is assigned its own MPI rank. Any statement
that is not guarded by a rank check runs four times, and every collective call
must be reached by all ranks or the run blocks forever.

The simulation is parallel because OPM distributes the grid internally: rank 0
parses the deck, broadcasts it to the other ranks, the partitioner splits the
grid, and each rank then owns a subset of the cells.


A minimal parallel run
----------------------

.. code-block:: python

   from mpi4py import MPI          # must be imported first: this calls MPI_Init

   from opm.simulators import BlackOilSimulator

   comm = MPI.COMM_WORLD

   sim = BlackOilSimulator(filename="SPE1CASE1.DATA")

   # mpi4py has already initialised MPI, so OPM must not do it again.
   sim.setup_mpi(init=False, finalize=False)

   rc = sim.step_init()
   if rc != 0:
       raise RuntimeError(f"step_init() failed with code {rc}")

   for _ in range(2):
       if sim.step() == 0:        # 0 means the schedule hit an EXIT keyword
           break

   sim.step_cleanup()
   comm.barrier()

Run it with:

.. code-block:: bash

   mpirun -np 4 python3 my_script.py

and confirm the rank count in the print file:

.. code-block:: bash

   grep "Number of MPI processes" SPE1CASE1.PRT


Constructing the simulator
--------------------------

.. warning::

   In parallel, only the **filename constructor** works:

   .. code-block:: python

      sim = BlackOilSimulator(filename="SPE1CASE1.DATA")

   The four-argument form documented for serial runs —
   ``BlackOilSimulator(deck, state, schedule, summary_config)`` — cannot run on
   more than one rank. An ``EclipseState`` built in Python is the *serial*
   class, while a parallel run requires ``ParallelEclipseState``, which has no
   Python binding. OPM reports::

      Error: Parallel simulator setup is incorrect as it does not use ParallelEclipseState

   but this is **not** raised as a Python exception; see
   :ref:`checking-return-values` below.

With the filename form, OPM owns the whole pipeline — parsing, broadcast,
partitioning and distribution — so no serial state object ever crosses into the
parallel code path.


Initialising MPI
----------------

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


.. _checking-return-values:

Checking return values
----------------------

.. warning::

   ``step_init()`` and ``step()`` use **opposite** success conventions, and
   neither raises on failure. Do not reuse one check for the other.

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Method
     - Success
     - Notes
   * - ``step_init()``
     - ``0``
     - Non-zero means setup failed. Nothing is raised.
   * - ``step()``
     - ``1``
     - ``0`` means the schedule hit an ``EXIT`` keyword — a normal early stop.

A failed ``step_init()`` returns a non-zero code and leaves a null simulator
behind. The failure only becomes visible at the *next* call, as a segmentation
fault rather than a Python traceback. Calling ``step_init()`` a second time
reports success, because the internal "already initialised" flag was set
despite the failure.

Always check the return value:

.. code-block:: python

   rc = sim.step_init()
   if rc != 0:
       raise RuntimeError(f"step_init() failed with code {rc}")

.. note::

   ``get_dt()`` must not be called before the first ``step()``. It maps to
   ``SimulatorTimer::stepLengthTaken()``, which is guarded by an assertion on
   the step counter. In a build without ``-DNDEBUG`` this aborts the
   interpreter with ``SIGABRT``, which Python cannot catch.


Working with distributed arrays
-------------------------------

After the grid is distributed, each rank holds **only its own cells**, plus an
overlap layer. Array getters return that local array, not the global field.

For SPE1CASE1 (300 cells) the local lengths are:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Ranks
     - ``len(sim.get_porosity())`` per rank
   * - 1
     - ``[300]``
   * - 2
     - ``[177, 189]``
   * - 4
     - ``[135, 123, 117, 132]``

The local lengths sum to more than 300 because overlap cells are counted on
more than one rank. Owned cells sum to exactly 300.

Setters expect an array of **this rank's** length. The safe pattern is to
derive the new array from the old one, which stays correct at any rank count:

.. code-block:: python

   poro = sim.get_porosity()
   sim.set_porosity(poro * 0.95)      # correct on 1, 2 or 4 ranks

A script that builds a 300-element array from ``DIMENS`` is wrong on every run
with more than one rank.


Verifying that the run is really parallel
-----------------------------------------

A run that does not crash is not evidence of anything — four *independent
serial* runs do not crash either. Two checks distinguish the cases.

First, the print file should report the rank count:

.. code-block:: bash

   grep "Number of MPI processes" SPE1CASE1.PRT

Second, compare values across ranks. Quantities such as the step counter must
agree, while local array lengths must differ:

.. code-block:: python

   def agree(label, value):
       gathered = comm.allgather(value)
       same = len({repr(v) for v in gathered}) == 1
       if comm.Get_rank() == 0:
           print(f"{'same  ' if same else 'DIFFER'} {label:<20} {gathered}")
       return gathered

   agree("current_step", sim.current_step())        # expect agreement
   agree("len(porosity)", len(sim.get_porosity()))  # expect differences

If the porosity lengths agree at four ranks, the grid was never distributed and
you are running four serial simulations.


Complete example
----------------

.. code-block:: python

   #!/usr/bin/env python3
   """SPE1CASE1 driven from Python across several MPI ranks.

       mpirun -np 4 python3 spe1case1_parallel.py
   """

   from mpi4py import MPI          # must come first: this calls MPI_Init

   from opm.simulators import BlackOilSimulator

   COMM = MPI.COMM_WORLD
   RANK = COMM.Get_rank()
   SIZE = COMM.Get_size()

   CASE = "SPE1CASE1.DATA"
   NSTEPS = 2


   def root(msg):
       """Print once, from rank 0."""
       if RANK == 0:
           print(msg, flush=True)


   def agree(label, value):
       """Report whether every rank produced the same value."""
       gathered = COMM.allgather(value)
       same = len({repr(v) for v in gathered}) == 1
       root(f"  {'same  ' if same else 'DIFFER'} {label:<22} {gathered}")
       return gathered


   def main():
       root(f"SPE1CASE1 on {SIZE} rank(s)")

       sim = BlackOilSimulator(filename=CASE)
       sim.setup_mpi(init=False, finalize=False)

       rc = sim.step_init()
       if rc != 0:
           raise RuntimeError(f"step_init() failed with code {rc} on rank {RANK}")

       agree("current_step", sim.current_step())

       poro = sim.get_porosity()
       lengths = agree("len(porosity)", len(poro))
       if RANK == 0:
           print(f"  -> {sum(lengths)} local cells across {SIZE} ranks "
                 f"(300 owned + overlap)", flush=True)

       sim.set_porosity(poro * 0.95)

       for i in range(NSTEPS):
           if sim.step() == 0:
               root("  EXIT encountered in the schedule -- stopping early")
               break
           root(f"after step {i}:")
           agree("get_dt", sim.get_dt())
           agree("current_step", sim.current_step())

       sim.step_cleanup()

       # Every rank must reach this, or the others block here forever.
       COMM.barrier()
       root(f"done -- check 'Number of MPI processes: {SIZE}' in the PRT file")


   if __name__ == "__main__":
       main()


Known limitations
-----------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Limitation
     - Consequence
   * - No Python binding for ``ParallelEclipseState``
     - Decks cannot be built or modified in Python before a parallel run. Use
       the filename constructor and edit the deck on disk.
   * - ``step_init()`` failures are not raised
     - A setup error surfaces as a segmentation fault on the next call. Always
       check the return value.
   * - Return conventions are inconsistent
     - ``step_init()`` returns ``0`` on success, ``step()`` returns ``1``.
   * - ``get_dt()`` asserts before the first step
     - Aborts the interpreter in builds without ``-DNDEBUG``.

These apply to ``GasWaterSimulator`` and ``OnePhaseSimulator`` as well, since
the behaviour comes from their shared base class.
