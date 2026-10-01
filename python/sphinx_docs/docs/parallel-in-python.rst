Run OPM Flow in parallel from Python
====================================

:doc:`flow-in-python` shows how to drive a simulation from a single Python
process. This page covers running the same simulation across several MPI ranks.

Prerequisites
-------------

This page assumes you can already run a serial simulation from Python. See
:doc:`flow-in-python` for compiling Flow with Python support and for setting
``PYTHONPATH``.

Running in parallel needs the following in addition:

- **MPI available at configure time.** ``USE_MPI`` is ``ON`` by default, so in
  practice this just means having an MPI implementation installed where CMake
  can find it.

- **A graph partitioner** — Zoltan or METIS/ParMETIS — present at configure
  time. The default partitioning method is ``zoltanwell``, so without one of
  these libraries you will need ``--partition-method=simple``, which uses
  OPM's built-in rectangular partitioning of the Cartesian grid instead.

- **mpi4py**, *if the script itself needs MPI* — to print from one rank only,
  or to combine the per-rank results of ``get_porosity()`` and friends. It is
  not needed simply to run in parallel: with the defaults
  ``init=True, finalize=True`` OPM initializes MPI itself, and
  ``mpirun -np 4 python3 my_script.py`` works with no mpi4py at all. But once
  mpi4py is imported, the flag values described under "Initializing MPI" below
  become required rather than optional. See the
  `mpi4py documentation <https://mpi4py.readthedocs.io/>`_.


An example script for a parallel run
------------------------------------

.. code-block:: python

    from mpi4py import MPI  # noqa: E402  -- owns MPI_Init; must come before OPM
    from opm.simulators import BlackOilSimulator  # noqa: E402
    from opm.io.parser import Parser  # noqa: E402
    from opm.io.ecl_state import EclipseState  # noqa: E402
    from opm.io.schedule import Schedule  # noqa: E402
    from opm.io.summary import SummaryConfig  # noqa: E402

    CASE = "SPE1CASE1.DATA"

    COMM = MPI.COMM_WORLD
    RANK = COMM.Get_rank()


    def main():
        deck = Parser().parse(CASE)
        state = EclipseState(deck)            # needed to build the Schedule only
        schedule = Schedule(deck, state)
        summary_config = SummaryConfig(deck, state, schedule)

        # The one change from the documented example: None instead of `state`.
        sim = BlackOilSimulator(deck, None, schedule, summary_config)
        sim.setup_mpi(init=False, finalize=False)

        sim.step_init()

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

The rest of this page covers behavior that is easy to get wrong,
and the reasons behind the recommendations above.

Initializing MPI
~~~~~~~~~~~~~~~~

``setup_mpi()`` takes two flags, and both matter when mpi4py is in use:

.. code-block:: python

   sim.setup_mpi(init=False, finalize=False)

``init=False``
   ``from mpi4py import MPI`` already called ``MPI_Init``. Letting OPM
   initialize MPI a second time is an error.

``finalize=False``
   Leaves MPI running after the simulator shuts down. With ``finalize=True``
   OPM tears MPI down, and any collective call afterwards — including an
   ``allgather`` used for checking results — aborts. The teardown happens in
   the simulator's destructor, not in ``step_cleanup()``: had the example above
   used ``finalize=True``, it would fire when ``main()`` returns and ``sim``
   goes out of scope, so collectives still work immediately after
   ``step_cleanup()``.


Constructing the simulator
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

   In parallel, only the **filename constructor** works:

   .. code-block:: python

      sim = BlackOilSimulator(filename="SPE1CASE1.DATA")

   The four-argument form documented for serial runs —
   ``BlackOilSimulator(deck, state, schedule, summary_config)`` — cannot run on
   more than one rank. It aborts with
   ``Parallel simulator setup is incorrect as it does not use ParallelEclipseState``.
