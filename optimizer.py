import math
import random

from collections import defaultdict
from ortools.sat.python import cp_model

from sig_groups.ride import Roster
from sig_groups.rider import Leader, Participant, Match

class Params(object):
    def __init__(self):
        # Hard limits on group sizes.
        self.min_group_size = 4
        self.max_group_size = 20

        # Soft limit on max group size.
        self.max_desirable_group_size = 7

        # The maximum number of groups to assign each week.
        self.max_groups = 8

        # Total number of rides in the program.
        self.num_rides = 10

        # Maximum amount of time to run for, in seconds, per-pass.
        self.time_limit = 30

def VarName(prefix, params):
  return ('%s_' % prefix) + '_'.join(map(str, params))

class Vars(object):
  def __init__(self):
    # Map from (r, g, p) -> bool.
    self.memberships = {}

    # Map from (r, g) -> bool.
    self.group_active = {}

    # Map from r -> int
    self.num_groups = {}
    self.target_size = {}
    self.target_leaders = {}

    ### Derived variables.

    # Map from (r, g) -> [bool]
    self.groups = defaultdict(lambda: [])
    self.group_leaders = defaultdict(lambda: [])
    self.group_leaders_experienced = defaultdict(lambda: [])

    # Map from (r, g) -> gender -> [bool]
    self.groups_genders = defaultdict(lambda: defaultdict(lambda: []))

    # Map from (p1, p2) -> bool indicating that these two people rode together.
    self.paired = {}

  def RecordHints(self, solver):
    hints = {}
    def log_map(name, var):
      hints[name] = {}
      for (k,v) in var.items():
          hints[name][k] = solver.Value(v)
    log_map("memberships", self.memberships)
    log_map("group_active", self.group_active)
    log_map("num_groups", self.num_groups)
    log_map("target_size", self.target_size)
    log_map("target_leaders", self.target_leaders)
    return hints

  def RestoreHints(self, model, hints):
    def restore(name, var, constraint=None):
      for k in hints[name]:
        if constraint:
          model.Add(var[k] == hints[name][k])
        else:
          model.AddHint(var[k], hints[name][k])

    restore("memberships", self.memberships)
    restore("group_active", self.group_active, constraint=True)
    restore("num_groups", self.num_groups, constraint=True)
    restore("target_size", self.target_size, constraint=True)
    restore("target_leaders", self.target_leaders, constraint=True)

class AlgorithmTM(object):
  def __init__(self, riders, prior_rosters, params):
    self.riders = riders
    self.prior_rosters = prior_rosters
    self.params = params

    num_prior_rides = 0
    for r in prior_rosters:
      num_prior_rides = max(num_prior_rides, r.ride + 1)

    # The ride to start algorithm constraints on.
    self.start_ride = num_prior_rides
    print('Initializing Algorithm to start at ride ', self.start_ride)

  def GetRosters(self, memberships):
    data = defaultdict(lambda: [])
    for (r, g, p) in memberships:
      data[(r,g)].append(self.riders.Rider(p))

    rosters = []
    for (r,g) in sorted(data):
      rosters.append(Roster(r, g, data[(r,g)]))
    return rosters

  def InitializeModel(self, model, vars):
   # Setup a boolean matrix for each rider in every group on every ride.
    for p in self.riders.AllRiders():
      for r in range(0, self.params.num_rides):
        for g in range(0, self.params.max_groups):
          vars.memberships[(r, g, p.id)] = model.NewBoolVar(VarName('membership', [r, g, p.id]))

    # Each group in the array is an individual (r, g) list of participant bools.
    # Add references into the boolean matrix for different breakdowns by group,
    # gender, leader, etc.
    for r in range(0, self.params.num_rides):
      for g in range(0, self.params.max_groups):
        vars.group_active[(r,g)] = model.NewBoolVar(VarName('group_active', [r, g]))

        for p in self.riders.AllRiders():
          me = vars.memberships[(r, g, p.id)]

          vars.groups[(r,g)].append(me)
          vars.groups_genders[(r,g)][p.gender].append(me)
          if isinstance(p, Leader):
            vars.group_leaders[(r,g)].append(me)
            if p.experienced:
              vars.group_leaders_experienced[(r,g)].append(me)

    # Constrain historical rosters to what they were.
    prior_ride_true = set()
    for roster in self.prior_rosters:
      for rider in roster.riders:
        prior_ride_true.add((roster.ride, roster.group, rider.id))
    for p in self.riders.AllRiders():
      for r in range(0, self.start_ride):
        for g in range(0, self.params.max_groups):
          if (r,g,p.id) in prior_ride_true:
            model.Add(vars.memberships[(r, g, p.id)] == 1)
          else:
            model.Add(vars.memberships[(r, g, p.id)] == 0)

  def AddGroupConstraints(self, model, vars):
    """
    Defines the rigid constraints on each group.
    """
    # Define target group topology for each ride.
    for r in range(self.start_ride, self.params.num_rides):
      vars.num_groups[r] = model.NewIntVar(0, self.params.max_groups, VarName('num_groups', [r]))
      vars.target_size[r] = model.NewIntVar(0, self.params.max_group_size, VarName('target_size', [r]))
      vars.target_leaders[r] = model.NewIntVar(0, self.params.max_group_size, VarName('target_leaders', [r]))
      model.AddHint(vars.target_size[r], self.params.max_desirable_group_size)
      model.AddHint(vars.target_leaders[r], 2)

    for r in range(self.start_ride, self.params.num_rides):
      for g in range(0, self.params.max_groups):
        group_size = sum(vars.groups[(r,g)])
        group_active = vars.group_active[(r,g)]
        num_leaders = sum(vars.group_leaders[(r,g)])

        # Make sure we're setting exactly num_groups for the given ride.
        too_many_groups = model.NewBoolVar(VarName('too_many_groups', [r, g]))
        model.Add(g >= vars.num_groups[r]).OnlyEnforceIf(too_many_groups)
        model.Add(g < vars.num_groups[r]).OnlyEnforceIf(too_many_groups.Not())
        model.Add(group_size == 0).OnlyEnforceIf(too_many_groups)
        model.Add(group_size > 0).OnlyEnforceIf(too_many_groups.Not())

        # If the group isn't active it must be empty.
        model.Add(group_size == 0).OnlyEnforceIf(group_active.Not())

        # Hard limits on group size.
        model.Add(group_size >= self.params.min_group_size).OnlyEnforceIf(group_active)
        model.Add(group_size <= self.params.max_group_size).OnlyEnforceIf(group_active)

        # Each group must have at least two leaders, and at least one
        # experienced leader.
        model.Add(sum(vars.group_leaders[(r,g)]) >= 2).OnlyEnforceIf(group_active)
        model.Add(sum(vars.group_leaders_experienced[(r,g)]) >= 1).OnlyEnforceIf(group_active)

        # No lone riders of either gender.
        model.Add(sum(vars.groups_genders[(r,g)]['F']) != 1).OnlyEnforceIf(group_active)
        model.Add(sum(vars.groups_genders[(r,g)]['M']) != 1).OnlyEnforceIf(group_active)

        # Hard limit on even group sizes / number of leaders.
        model.AddLinearConstraint(group_size - vars.target_size[r], 0, 1).OnlyEnforceIf(group_active)
        model.AddLinearConstraint(num_leaders - vars.target_leaders[r], 0, 1).OnlyEnforceIf(group_active)

  def AddRiderConstraints(self, model, vars):
    # Make sure every rider is in exactly one group if they're attending the
    # ride and zero groups if they aren't.
    for r in range(self.start_ride, self.params.num_rides):
      for p in self.riders.AllRiders():
        s = 0
        for g in range(0, self.params.max_groups):
          s += vars.memberships[(r, g, p.id)]
        model.Add(s == p.IsAvailable(r))

  def OptimizeGroupSize(self, model, vars):
    '''
    Try to make the groups roughly equal size relative to each other, but also
    not too big.
    '''
    penalties = []
    for r in range(self.start_ride, self.params.num_rides):
      for g in range(self.start_ride, self.params.max_groups):
        group_size = sum(vars.groups[(r,g)])
        group_active = vars.group_active[(r,g)]
        num_leaders = sum(vars.group_leaders[(r,g)])

        # Don't stray too far from the target group size.
        size_deviates = model.NewBoolVar(VarName('size_deviates', [r, g]))
        model.AddLinearConstraint(group_size - vars.target_size[r], 0, 2).OnlyEnforceIf(size_deviates)
        penalties.append(size_deviates*1000)

    # Penalize a large target group size.
    for r in range(self.start_ride, self.params.num_rides):
      target_size_too_big = model.NewBoolVar(VarName('target_size_too_big', [r]))
      model.Add(vars.target_size[r] > self.params.max_desirable_group_size).OnlyEnforceIf(target_size_too_big)
      model.Add(vars.target_size[r] <= self.params.max_desirable_group_size).OnlyEnforceIf(target_size_too_big.Not())
      penalties.append(target_size_too_big*100000)

    model.Minimize(sum(penalties))

  def OptimizePairings(self, model, vars):
    '''
    Maximize the number of pairs of different riders that ride together.
    '''

    # Compute the set of all possible pairs of riders, and then we try to
    # optimize for including as many pairs as possible in the rosters.
    all_pairs = set()
    for p1 in self.riders.AllFtRiders():
      for p2 in self.riders.AllFtRiders():
        if (p1.id != p2.id and (p2.id, p1.id) not in all_pairs):
          all_pairs.add((p1.id, p2.id))
    print("Number of riders: ", len(self.riders.AllFtRiders()))
    print("Number of total rider pairings: ", len(all_pairs))
    print()
    assert(len(all_pairs) == math.factorial(len(self.riders.AllFtRiders()))/
           math.factorial(2)/math.factorial(len(self.riders.AllFtRiders())-2))

    # For each pair of riders we create a boolean that represents if these
    # riders have ridden together.
    #
    # We also account for a match score (hand curated) for some pairs of riders.
    # These are used as the coefficient on the paired boolean to compute a score
    # for the roster.
    def MentorPair(i1, i2):
      p1 = self.riders.Rider(i1)
      p2 = self.riders.Rider(i2)
      if p1.IsLeader() == p2.IsLeader():
        return False
      if p1.IsLeader():
        return p2.mentor == p1.id
      if p2.IsLeader():
        return p1.mentor == p2.id

    scores = []
    for (p1, p2) in all_pairs:
      vars.paired[(p1, p2)] = model.NewBoolVar(VarName('paired', [p1, p2]))

      paired_in_group = []
      not_paired_in_group = []
      for r in range(0, self.params.num_rides):
        paired_on_ride = []
        for g in range(0, self.params.max_groups):
          paired_here = model.NewBoolVar(VarName('paired_at', [p1, p2, r, g]))
          pair = [vars.memberships[(r, g, p1)], vars.memberships[(r, g, p2)]]
          not_pair = [vars.memberships[(r, g, p1)].Not(), vars.memberships[(r, g, p2)].Not()]
          model.AddBoolAnd(pair).OnlyEnforceIf(paired_here)
          model.AddBoolOr(not_pair).OnlyEnforceIf(paired_here.Not())

          paired_in_group.append(paired_here)
          not_paired_in_group.append(paired_here.Not())

          paired_on_ride.append(paired_here)

        # For ride 2 force mentor/mentee pairings.
        p1_obj = self.riders.Rider(p1)
        p2_obj = self.riders.Rider(p2)
        if (r == 1 and MentorPair(p1, p2) and
            p1_obj.IsAvailable(r) and p2_obj.IsAvailable(r)):
          print('Adding ride %d mentor constraint for'%r, p1_obj.name, p2_obj.name)
          model.AddBoolOr(paired_on_ride)
        if (r == 2 and MentorPair(p1, p2) and
            (not p1_obj.IsAvailable(1) or not p2_obj.IsAvailable(1)) and
            p1_obj.IsAvailable(r) and p2_obj.IsAvailable(r)):
          print('Adding ride %d mentor constraint for'%r, p1_obj.name, p2_obj.name)
          model.AddBoolOr(paired_on_ride)
        if (r == 3 and MentorPair(p1, p2) and
            (not p1_obj.IsAvailable(1) or not p2_obj.IsAvailable(1)) and
            (not p1_obj.IsAvailable(2) or not p2_obj.IsAvailable(2)) and
            p1_obj.IsAvailable(r) and p2_obj.IsAvailable(r)):
          print('Adding ride %d mentor constraint for'%r, p1_obj.name, p2_obj.name)
          model.AddBoolOr(paired_on_ride)

      model.AddBoolOr(paired_in_group).OnlyEnforceIf(vars.paired[(p1, p2)])
      model.AddBoolAnd(not_paired_in_group).OnlyEnforceIf(vars.paired[(p1, p2)].Not())

      scores.append(self.riders.GetMatchScore(p1, p2) * vars.paired[(p1, p2)])

    model.Maximize(sum(vars.paired.values()) + sum(scores))

  def BuildBaseModel(self, vars):
    model = cp_model.CpModel()
    self.InitializeModel(model, vars)

    # Make sure that every ride has at least one group.
    for r in range(0, self.params.num_rides):
      bools = []
      for k in vars.group_active:
        if k[0] == r:
          bools.append(vars.group_active[k])
      model.AddBoolOr(bools)

    self.AddGroupConstraints(model, vars)
    self.AddRiderConstraints(model, vars)
    return model

  def SolveAndLog(self, solver, model, vars):
    status = solver.Solve(model)
    print(f'Maximum of objective function: {solver.ObjectiveValue()}\n')
    print('\nStatistics')
    print(f'  status   : {solver.StatusName(status)}')
    print(f'  conflicts: {solver.NumConflicts()}')
    print(f'  branches : {solver.NumBranches()}')
    print(f'  wall time: {solver.WallTime()} s')
    results = {}
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
      return vars.RecordHints(solver)
    else:
      print('No solution found.')
      return None

  def Solve(self):
    print('Optimizing group size...')

    vars = Vars()
    model = self.BuildBaseModel(vars)
    self.OptimizeGroupSize(model, vars)
    print(model.ModelStats())
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    solver.parameters.max_time_in_seconds = self.params.time_limit

    results = self.SolveAndLog(solver, model, vars)
    if results is None:
      return

    print()
    for (k,vs) in vars.target_size.items():
      vn = vars.num_groups[k]
      vl = vars.target_leaders[k]
      print('Ride %d >> %d groups : target_size %d and target_leaders %d' %
            (k, solver.Value(vn), solver.Value(vs), solver.Value(vl)))

    hints = vars.RecordHints(solver)
    print()
    print('Optimzing pairings...')
    vars = Vars()
    model = self.BuildBaseModel(vars)
    vars.RestoreHints(model, hints)
    self.OptimizePairings(model, vars)
    print(model.ModelStats())
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    solver.parameters.max_time_in_seconds = self.params.time_limit

    results = self.SolveAndLog(solver, model, vars)
    if results is None:
      return

    memberships = []
    for (k,v) in vars.memberships.items():
      if (solver.Value(v)):
        memberships.append(k)
    return self.GetRosters(memberships)
