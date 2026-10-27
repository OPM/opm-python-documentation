Run Python embedded in OPM Flow
===============================

The PYACTION keyword is a Flow specific keyword which allows for executing embedded Python
code in the SCHEDULE section. The embedded Python code will then be executed at the end of each successful timestep.

The PYACTION keyword is inspired
by the ACTIONX keyword, but instead of a .DATA formatted condition you
are allowed to implement the condition with a general Python script. The
ACTIONX keywords are very clearly separated in a condition part and an
action part in the form of a list of keywords which are effectively injected in
the SCHEDULE section when the condition evaluates to true.
This is not so for PYACTION where there is one Python script in which both
conditions can be evaluated and changes applied.

See also: PYACTION in the `reference manual <https://opm-project.org/?page_id=955>`_ for more information and `opm-tests <https://github.com/OPM/opm-tests/tree/master/pyaction>`_ for examples.

In order to enable the PYACTION keyword:

1. Compile Flow with Embedded Python support:

   - Add the cmake flags ``-DOPM_ENABLE_PYTHON=ON`` and ``-DOPM_ENABLE_EMBEDDED_PYTHON=ON`` (you can also change these settings in the ``CMakeLists.txt`` of ``opm-common`` and ``opm-simulators``).

..

2. The keyword PYACTION must be added to the SCHEDULE section:

   .. code-block:: python

      <PYACTION_NAME>  <SINGLE/UNLIMITED> /
      <pythonscript> / -- path to the python script, relative to the location of the DATA-file

3. You need to provide the Python script.

   To interact with the simulator in the embedded Python code, you can access four variables from the simulator:

   .. code-block:: python

      # Python module opm_embedded
      import opm_embedded
      # The current EclipseState
      ecl_state = opm_embedded.current_ecl_state
      # The current Schedule
      schedule = opm_embedded.current_schedule
      # The current SummaryState
      summary_state = opm_embedded.current_summary_state
      # The current report step
      report_step = opm_embedded.current_report_step

   - ``current_ecl_state``: An instance of the `EclipseState <common.html#opm.io.ecl_state.EclipseState>`_ class — this is a representation of all static properties in the model, ranging from porosity to relperm tables. The content of the ecl state is immutable — you are not allowed to change the static properties at runtime.

   - ``current_schedule``: An instance of the `Schedule <common.html#opm.io.schedule.Schedule>`_ class — this is a representation of all the content from the SCHEDULE section, notably all well and group information and the timestepping.

   - ``current_report_step``: This is an integer for the report step we are currently working on. Observe that the PYACTION is called for every simulator timestep, i.e. it will typically be called multiple times with the same value for the report step argument.

   - ``current_summary_state``: An instance of the `SummaryState <common.html#opm.io.sim.SummaryState>`_ class — this is where the current summary results of the simulator are stored. The `SummaryState <common.html#opm.io.sim.SummaryState>`_ class has methods to get hold of well, group, and general variables.


Stateful behavior using Python classes
--------------------------------------

In the below code snippet, we use a ``WellController`` class to manage production wells by tracking their status and simulation timing.
We create one instance of the WellController and use its internal state across multiple timesteps and PYACTION calls.

.. code-block:: python

   import opm_embedded
   from datetime import datetime, timedelta

   # Check if the setup has already been done to avoid reinitialization
   if 'setup_done' not in locals():
       # Target oil production rate in standard units (e.g., stb/day)
       OIL_RATE_TARGET = 8000
       # Minimum time in days between opening new wells
       MIN_DAYS_BETWEEN_OPENINGS = 50

       class WellController:
           """
           A controller to manage the opening of production wells based on
           oil rate targets and elapsed simulation time.

           Attributes:
               closed_wells (list[str]): List of wells yet to be opened.
               last_opening_time (datetime): Simulation time of the last well opening.
                                             Initially, this is set to the simulation start time.
           """
           def __init__(self, well_names, start_time):
               """
               Initialize the WellController.

               Args:
                   well_names (list[str]): Names of wells to be controlled.
                   start_time (datetime): Simulation start time.
               """
               self.closed_wells = list(well_names)
               self.last_opening_time = start_time

           def update(self, current_oil_rate, current_time):
               """
               Evaluate the current oil production and determine whether to open
               a new well based on the target rate and time since the last opening.

               Args:
                   current_oil_rate (float): The current oil rate.
                   current_time (datetime): Current simulation time.
               """
               days_since_last_opening = (current_time - self.last_opening_time).days

               if (current_oil_rate < OIL_RATE_TARGET and
                   days_since_last_opening >= MIN_DAYS_BETWEEN_OPENINGS and
                   len(self.closed_wells) > 0):

                   next_well = self.closed_wells.pop(0)
                   self.last_opening_time = current_time

                   schedule.open_well(next_well)
                   opm_embedded.OpmLog.info(f"Opened well {next_well}")

           def set_next_dt(self, current_time):
               """
               Insert the NEXTSTEP keyword to control the simulator's timestep,
               adjusting based on whether a well was just opened.

               Args:
                   current_time (datetime): Current simulation time.
               """
               if self.closed_wells:
                   days_since_last_opening = (current_time - self.last_opening_time).days
                   if days_since_last_opening >= MIN_DAYS_BETWEEN_OPENINGS:
                       next_dt = 10.0
                   else:
                       next_dt = 50.0
                   kw = f"""
                   NEXTSTEP
                   {next_dt} /
                   """
                   schedule.insert_keywords(kw)

       # Instantiate the controller with a list of wells and simulation start time
       # This controller will be instatiated once and be used in all following PYACTION calls.
       controller = WellController(well_names=['PROD01', 'PROD02'],
                     start_time=opm_embedded.current_schedule.start)
       setup_done = True

   # Retrieve current simulation components from the OPM embedded module
   schedule = opm_embedded.current_schedule
   report_step = opm_embedded.current_report_step
   summary_state = opm_embedded.current_summary_state

   # Compute the current simulation time
   current_time = schedule.start + timedelta(seconds=summary_state.elapsed())
   current_oil_rate = summary_state.group_var('P', 'GOPR')

   # Update well control logic based on current state
   controller.update(current_oil_rate, current_time)
   # Set the next simulation step duration
   controller.set_next_dt(current_time)

   # Optional logs to track the status of the two wells:
   # opm_embedded.OpmLog.info("PROD01: {}".format(schedule.get_well("PROD01", report_step).status()))
   # opm_embedded.OpmLog.info("PROD02: {}".format(schedule.get_well("PROD02", report_step).status()))

Use this code snippet with the example `MSW-3D-TWO-PRODUCERS <https://github.com/OPM/opm-tests/blob/master/msw/MSW-3D-TWO-PRODUCERS.DATA>`_ by saving the file as ``wellcontroller.py`` at the same location as ``MSW-3D-TWO-PRODUCERS.DATA`` and adding

.. code-block:: none

   PYACTION
   WELLCONTROLLER UNLIMITED /
   'wellcontroller.py' /

to the ``SCHEDULE`` section of ``MSW-3D-TWO-PRODUCERS.DATA``.

Inserting user defined quantity (UDQ) keywords
----------------------------------------------

The ``UDQ`` keyword can be inserted from a PYACTION script. These features are supported:

- ``ASSIGN`` and ``DEFINE`` for field (``FU_``) and well (``WU_``) variables.
- Well variables for named wells, for example ``ASSIGN WU_FLAG 'OP01' 5 /``.
- New UDQ variables that are not declared in the DATA file. To write a new variable to
  the summary output, list it in the SUMMARY section.

Inserting UDQ keywords
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import opm_embedded

   summary_state = opm_embedded.current_summary_state
   schedule = opm_embedded.current_schedule

   # Run the insertion only once
   if 'setup_done' not in globals():
       done = False
       setup_done = True

   wells = ["OP0{}".format(i) for i in range(1, 10)]
   if not done and any(summary_state.well_var(w, "WGOR") >= summary_state["FU_GOR2"] for w in wells):
       opm_embedded.OpmLog.info("PYACTION PYACTION_UDQ triggered")
       schedule.insert_keywords("""
       UDQ
       DEFINE  WU_NEW   WOPR * 2 /
       ASSIGN  WU_FLAG  'OP01' 5 /
       /
       """)
       done = True

Here ``WU_NEW`` and ``WU_FLAG`` are already declared in the UDQ section of the DATA file.

Computing UDQ values in Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of inserting the ``UDQ`` keyword, a PYACTION script can also compute the values
in Python and write them into the summary state. Then the DATA file needs no ``UDQ``
keyword; the variables are only listed in the SUMMARY section, so they are written to
the summary output:

.. code-block:: python

   summary_state = opm_embedded.current_summary_state

   if "FU_TIME" not in summary_state:
       summary_state["FU_TIME"] = 0.0
   summary_state["FU_TIME"] += summary_state["TIMESTEP"]
   summary_state["FU_VAR19"] = summary_state.well_var("INJ1", "WWIR")

Complete examples in opm-tests, each with an ACTIONX version that gives the same results
(serial and with 4 MPI processes):

- Inserting UDQ keywords:
  `PYACTION_UDQ_INSERT_KW.DATA <https://github.com/OPM/opm-tests/blob/master/pyaction/PYACTION_UDQ_INSERT_KW.DATA>`_
  with the script
  `pyaction_udq_insert_kw.py <https://github.com/OPM/opm-tests/blob/master/pyaction/pyaction_udq_insert_kw.py>`_;
  ACTIONX version
  `ACTIONX_UDQ_INSERT_KW.DATA <https://github.com/OPM/opm-tests/blob/master/actionx/ACTIONX_UDQ_INSERT_KW.DATA>`_.
- Computing UDQ values in Python:
  `UDQ_M3_PYACTION.DATA <https://github.com/OPM/opm-tests/blob/master/udq_pyaction/UDQ_M3_PYACTION.DATA>`_
  with the script
  `udq_m3_pyaction.py <https://github.com/OPM/opm-tests/blob/master/udq_pyaction/udq_m3_pyaction.py>`_;
  ACTIONX version
  `UDQ_M3.DATA <https://github.com/OPM/opm-tests/blob/master/udq_actionx/UDQ_M3.DATA>`_.

.. warning::

   The well name ``'?'`` (for example ``ASSIGN WU_Q '?' 7 /``) is **not supported yet**.
   In ACTIONX, ``'?'`` means the wells that matched the condition. A PYACTION script
   has no ACTIONX condition, so Flow stops with
   ``UDQ assignment for WU_Q does not have an associate match set``.
   Instead, find the wells in Python and write their names into the string:

   .. code-block:: python

      wells = ["OP0{}".format(i) for i in range(1, 10)]
      matched = [w for w in wells if summary_state.well_var(w, "WGOR") >= summary_state["FU_GOR2"]]
      kw = "UDQ\n" + "".join(f"ASSIGN WU_Q '{w}' 7 /\n" for w in matched) + "/\n"
      schedule.insert_keywords(kw)

