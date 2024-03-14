# The Algorithm™

## High-level Concepts

`sig_groups` contains the Algorithm™ implementation for SIG
groupings.  At a high-level it defines a model that it passes to a
[CP-SAT](https://developers.google.com/optimization/cp/cp_solver)
solver, which attempts to assign SIG groups based on a variety of
constraints and preferences (linear coefficients).  CP-SAT implements
a [SAT solver](https://en.wikipedia.org/wiki/SAT_solver) and [integer
programming](https://en.wikipedia.org/wiki/Integer_programming) optimizer.
This means we define the model in terms of constraints (hard requirements)
and weights (coefficients on boolean terms in linear expressions).  We try
to minimize or maximize the value of these linear expressions given different
boolean solutions that satisfy the constraints.

![sample roster gif](docs/sample_roster.gif?raw=true)
See the [sample roster](docs/sample_roster.txt) corresponding to this image.

## The Algorithm™'s Objectives

Constraints and preferences, which are implemented in `optimizer.py`,
loosely try to assemble groups that

- Have either zero or 2+ riders of each M/F gender
- Have at least two leaders, and at least one experienced leader
- Have even sizes and an even number of leaders (and specifically don't define
  groups with more leaders but fewer participants)
- Distribute the leaders that have scouted the ride among as many groups as
  possible

Additionally there are custom preferences supported:

- On a week-by-week basis we can prefer that individual groups of 2+ riders be
  grouped together
- We can mark some riders as requiring a woman leader
- We can assign scores to pairs of riders to mark them as incompatible (so we
  prefer groups that don't put them together) or highly compatible (so they
  ride together often)

There are also some custom behaviors defined such a mentor/mentee pairings.  From
the second ride onwards mentors and mentees are constrained to ride together on
the first ride where both are available.

Given the constraints and preferences the Algorithm™ attempts, over the course of
the program, to have as many different pairs of riders ride together as possible.

## High-level structure / execution

The Algorithm™ actually runs in two passes: the first decides the optimum number
of groups and their sizes for each ride (based on a 4 participant rule, leader
constraints, and other considerations) and the second pass determines the
optimum assignments of riders to these groups to meet the optimization objective
(having as many different pairs of riders ride together as possible).  The
solution from the first pass is set as a constraint for the second pass.  The
two passes are intended mainly to make the groups "look good", i.e. shape them
well before shuffling individuals around within the shape.

The Algorithm™ model attempts, in the second pass, given the constraints and
over the time purview of a model run, to have as many different pairs of riders
ride in the same group at least once.  That is, it aims to maximize the number
of unique pairs $(p_1, p_2)$ that have ridden together at least once during the
purview of a model run.

The model can run either on the entire program from now until the grad ride, or
look forward only one or more weeks.  Because finding the ideal optimal solution
is NP-complete the Algorithm™ is generally run with a timeout parameter, and
it is allowed to search for a solution up until the timeout.  The best solution
found prior to the timeout is presented as the optimal solution.  The Algorithm™ 
is typically run from the current week's ride through the grad ride.  Historical
rosters are "finalized" meaning they become constrained in the model to what
they were.  Because historical rosters are constraints, the search space
decreases as the SIG program progresses and the Algorithm™ may begin to find
optimal solutions before timing out later in the program.

Due to the complexity of the problem, running the Algorithm™ on a multi-core
high-performance CPU will improve results for a given timeout.  CP-SAT benefits
from many CPU cores; it does not benefit from GPUs since the problem is a sparse
computation.  In 2023 the Algorithm™ was run on an AMD Ryzen Threadripper 3995WX
(128 threads).  Multithreading, and timeouts, are handled automatically by
CP-SAT.

## CP-SAT programming considerations

If constraints are not met the model will fail to find a solution.  If a
preference, a coefficient multiplied by a boolean variable, is imposed
by for a certain undesirable condition then a solution will be presented
even if the condition is satisfied, but the "score" of the solution may be
penalized by the coefficient multiplied by a "true" boolean.  If there is
no possible solution without the undesirable condition being satisfied then
all solutions may be penalized equally, effectively ignoring the condition.

Generally preferences are preferred to constraints for all but the strictest
constraints.  Defining constraints can speed up execution (by pruning the
solution space), but it comes at the risk of finding no solution if the
constraint can't be satisfied at all.  Debugging `INFEASIBLE` solutions
because the constraints can't be met is tricky.  Often it requires guessing
which constraints made the problem unsatisfiable, removing them, and re-running
the model.

Programming constraints and linear coefficients in CP-SAT is a bit unique.
There are a few patterns used in `optimizer.py` that offer utility.

 * **[Channeling constraints](https://developers.google.com/optimization/cp/channeling)**
   can be used to implement conditional logic, say obtain a boolean variable
   derived from other variables for use in a linear expression.

 * **Matrices of boolean variables** are used to represent different possible
   outputs.  For example the entire SIG is modeled as a 3D matrix of booleans
   with one dimension representing the ride, another the group on that ride,
   and a third representing the rider.  So it's a boolean matrix of shape
   `NumRides x MaxNumGroups x NumRiders` of where a one represents the
   rider being in the given group on the given ride.

 * **Different views of the same data** are used to make defining constraints
   simple.  If we consider the matrix described in the previous bullet, we
   want to then define constraints that model what we want, i.e. that riders
   are only in one group, they are only on rides they can attend, etc.  The
   sum of the matrix in one dimension, for example, is the number of riders
   in the group.  A filtered sum is the number of leaders, or women, or
   experienced leaders.  These sums can be referenced by other variables and
   then used in other constraints (or weighted sums).

The value of any variable defined in CP-SAT can be extracted when a solution is
found.  This can be useful for debugging (it's also how the actual rosters are
extracted from the matrix of group memberships and how the output of the first
pass is constrained in the second pass).

## I/O

Inputs to the Algorithm™ are sourced from two main sources:

- Config files
- Airtable

The Algorthm™ code outputs information:

- Locally
- To Slack
- To Airtable

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
- Mentor / mentee pairings

When the Algorithm™ finishes running (including timeouts) it writes rosters 
to Airtable.  The data in Airtable eventually becomes "historical rosters" as
the SIG progresses.  It can also be posted to Slack automatically in a separate
step.

> **Note** there are currently no locks around what should be a critical
> section reading and writing data to Airtable.  Airtable may be modified in
> a race with other executions of the Algorithm™ or other sources of Airtable
> writes (including the Airtable UI).

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
The Algorithm™ writes its output to Slack in a few different places

There's a Slack channel per-ride that has a sticky post with the roster.  The
config file contains a mapping between rides and the channel/post with the
roster.  The Algorithm™ can update the sticky post whenever the optimal roster
is computed.  As the program progesses the roster for a given ride may change
as individual availability changes, constraints/preferences are added, and
ultimately the Algorithm™ is re-run.

Each algoritm run also posts some diagnostic information, including an animated
visualization with $(p_1, p_2)$ pairing counts to a roster boss channel to
monitor the impact of changes in constraints and availability as the program
progresses.

The roster for each ride, including a static image with the new pairings on
that ride, is updated in the Slack channel for each ride.  The config contains
a unique reference to the roster post in Slack (by timestamp and channel).  This
post is updated on every run of the Algorithm™.  To create a new pinned post in
a channel for the roster `slack_roster_post` can be left undefined.

```
rides:
  - rank: 0
    title: Some Ride Title
    airtable_id: recXXXXXXXXXXXXXX
    slack_channel: C0XXXXXXXXX
    slack_roster_post: "1709263008.070159"
```

There's a separate flow for marking the Slack-posted roster "finalized" for a
given week.  This is distinct from running the Algorithm™; it simply makes a
Slack post announcing the finalized roster and updates the pinned post to
indicate it's finalized.

Slack credentials are also contained in the config file.  The Slack workspace
has a robot account "RosterBot" that posts Algorithm™ output, including the
rosters, to Slack.

## Instructions

### Setup

```
python -m venv .env && source .env/bin/activate && pip3 install -r requirements.txt
```

### Running the Algorithm™
To run the algorithm execute the following command.  Note that generating the
images requires a `$DISPLAY` environment variable set (though nothing is
actually displayed on `$DISPLAY`).

Important things to consider _before_ running the script:

- The `algorithm` section of the config is starting at the correct ride. (The
  first ride is ride 0.)
- The `algorithm` section of the config specifies the desired timeout.  Longer
  can be more accurate, but also more expensive.  There is a point of
  diminishing returns.
- `main.py` is loading the correct config
- There's no race anticipated writing to Airtable.

By default the script will output to the local console with images in `/tmp`.
```
python3 main.py
```

To run the script _and_ publish the output to Slack/Airtable, pass the
`--publish` flag.
```
python3 main.py --publish
```

### Finalizing rosters
To finalize rosters run the following command.  Be sure `finalize.py` is
loading the correct config and that the correct ride is being finalized.
_Setting the ride to finalize requires a change to the code._

The finalization script loads rosters from Airtable and posts them to
Slack.  This "feature" can be used to override the Algorithm™ output
without a rerun.

```
python3 finalize.py
```
