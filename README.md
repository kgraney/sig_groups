
## High-level
`sig_groups` contains the AlgorithmTM implementation for SIG groupings.  At a
high-level it defines a model, which is passes to a 
[CP-SAT](https://developers.google.com/optimization/cp/cp_solver)
solver, which attempts to assign SIG groups based on a variety of constraints
and preferences using CP-SAT.  CP-SAT implements a SAT solver and integer
programming solver.  This means we define the model in terms of constraints
(hard requirements) and weights (soft multipliers that we attempt to minimize
or maximize if the coefficient is one).  If constraints are not met the model
will fail to find a solution, if weights, with a boolean coefficient, can not
be satisified then all possible solutions will be penalized by the weight.
Generally weights are preferred to constraints in all but true constraints.
Defining constraints can speed up execution (by pruning the solution space),
but it comes at the risk of finding no solution if the constraint can't be
satisfied.

Constraints and weights, which are implemented in `optimizer.py`, loosely
try to assemble groups that

- Have either zero or 2+ riders of each gender
- Have at least two leaders, and at least one experienced leader
- Have even sizes and an even number of leaders (and specifically don't define
  groups with more leaders but fewer participants)
- Distribute the leaders that have scouted the ride among as many groups as
  possible

Additionally there are custom preferences supported:

- On a week-by-week basis we can prefer that individual groups of 2+ riders be
  grouped together
- We can mark some riders as requiring a woman leader
- We can mark pairs of riders as incompatible (so we prefer groups that don't
  put them together)

The AlgorithmTM actually runs in two passes: the first decides optimum group
sizes (based on a 4 participant rule and other constraints) and the second
pass shuffles riders among groups to find the optimium group composition within
the relatively even sized groups determined by the first pass.

When shuffling participants between groups, the AlgorithmTM model attempts,
given the constraints and over the purview of a model run, to match as many
different pairs of riders in the same groups.  That is, it aims to maximize the
number of unique pairs $(p_1, p_2)$ that have ridden together at least once
during the purview of a model run.

The model can run either on the entire program from now until the grad ride, or
look forward only one or more weeks.  Because finding the ideal optimal solution
is NP-complete the AlgorithmTM is generally run with a timeout parameter, and
it is allowed to search for a solution up until the timeout.  The best solution
found prior to the timeout is presented as the optimal solution.

As the search space decreases later in the SIG program the AlgorithmTM may
begin to find optimal solutions before timing out.

Due to the complexity of the problem, running the AlgorithmTM on a multi-core
high-performance CPU will improve results for a given timeout.  In 2023 the
AlgorithmTM was run on an AMD Ryzen Threadripper 3990X (128 threads).
Multithreading, and timeouts, are handled by CP-SAT.

## I/O

Inputs to the AlgorithmTM are sourced from two main sources:

- Config files
- Airtable

The AlgorthmTM code outputs information locally and to Slack.

### Airtable
Airtable hosts the source of truth for participant and leader information as
well as ride information.  The model is a loose ORM where objects such as
`Rider` (with inherited objects `Leader(Rider)` and `Participant(Rider)`),
`Roster`, and `Ride` are all sourced from Airtable.

Airtable is the source of truth for the following information:

- Availability on a week-by-week basis
- Rider names
- Rider genders
- Leader status (scouted, experienced/inexperienced, etc.)
- Basic ride information
- Historical rosters

When the AlgorithmTM finishes running (including timeouts) it writes rosters 
to Airtable.  The data in Airtable eventually becomes "historical rosters" as
the SIG progresses.  It can also be posted to Slack automatically in a separate
step.

### Config file
The config file for a given season includes credentials and references to the 
Airtable API.  See `AirtableClient` for logic mapping Airtable content to
Python objects.  The config file is specified in YAML and contains the
following information

- Week-to-week constraints
- Permanent constraints (e.g. incompatible riders)
- Week-to-week parameters (start ride, end-ride, execution timeout, etc.)
- API credentials (for Slack and Airtable)

### Slack
The AlgorithmTM writes its output to Slack in a few different places

There's a Slack channel per-ride that has a sticky post with the roster.  The
config file contains a mapping between rides and the channel/post with the
roster.  The AlgorithmTM can update the sticky post whenever the optimal roster
is computed.  As the program progesses the roster for a given ride may change
as individual availability changes, constraints/preferences are added, and
ultimately the AlgorithmTM is re-run.

Each algoritm run also posts some diagnostic information, including a
visualization with $(p_1, p_2)$ pairing counts to a roster boss channel to
monitor the impact of changes in constraints and availability as the program
progresses.

There's a separate flow for marking the Slack-posted roster "finalized" for a
given week.

Slack credentials are also contained in the config file.  The Slack workspace
has a robot account "RosterBot" that posts algorithm output, including the
rosters, to Slack.
