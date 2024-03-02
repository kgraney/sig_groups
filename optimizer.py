import math
import random

from collections import defaultdict, OrderedDict
from ortools.sat.python import cp_model

from sig_groups.ride import Roster
from sig_groups.rider import Leader, Participant, Match
from sig_groups.formatting import PrintRosters

class Params(object):
    def __init__(self):
        # Hard limits on group sizes.
        self.max_group_size = 20

        # The maximum number of groups to assign each week.
        self.max_groups = 8

        # Total number of rides in the program.
        self.num_rides = 10

        # Maximum amount of time to run for, in seconds, per-pass.
        self.time_limit = 30

        # The ride to start generating groups at.
        self.start_ride = 0

        # The last finalized ride (i.e. the last one that happened already).
        self.finalized_ride = 0

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
    self.target_leaders = {}
    self.target_participants = {}
    self.num_scouts = {}

    ### Derived variables.

    # Map from (r, g) -> [bool]
    self.groups = defaultdict(lambda: [])
    self.group_participants = defaultdict(lambda: [])
    self.group_leaders = defaultdict(lambda: [])
    self.group_leaders_experienced = defaultdict(lambda: [])
    self.group_leaders_inexperienced = defaultdict(lambda: [])
    self.group_leaders_scouted = defaultdict(lambda: [])
    self.group_leaders_female = defaultdict(lambda: [])

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
    log_map("target_participants", self.target_participants)
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
    restore("target_participants", self.target_participants, constraint=True)
    restore("target_leaders", self.target_leaders, constraint=True)

from ipykernel import comm
class Printer(cp_model.CpSolverSolutionCallback):
  def __init__(self, vars, riders):
    cp_model.CpSolverSolutionCallback.__init__(self)
    self.vars = vars
    self.riders = riders

  def on_solution_callback(self):
    memberships = []
    for (k,v) in self.vars.memberships.items():
      if (self.Value(v)):
        memberships.append(k)

    groups = defaultdict(lambda: defaultdict(lambda: []))
    for (r, g, p) in memberships:
      groups[r+1][g+1].append(self.riders.Rider(p).RosterString())

    #print('----------------------------')
    comm.Comm(target_name='rosters', data=dict(groups), buffers=[])
    #print(memberships)
    #print('============================')


class AlgorithmTM(object):
  def __init__(self, riders, rides, prior_rosters, params):
    self.riders = riders
    self.rides = {}
    for r in rides:
        self.rides[r.num] = r
    self.prior_rosters = prior_rosters
    self.params = params

    # map from r -> int
    self.num_scouts = defaultdict(lambda: 0)
    num_available_leaders = defaultdict(lambda: 0)
    self.num_scouts = defaultdict(lambda: 0)
    for r in range(0, params.num_rides):
      for p in self.riders.AllLeaders():
        if p.IsLeader() and p.Scouted(r):
          self.num_scouts[r] += 1
        if p.IsAvailable(r):
          num_available_leaders[r] += 1

    print('Initializing Algorithm to start at ride ', self.params.start_ride)

  def GetRosters(self, memberships):
    data = defaultdict(lambda: [])
    for (r, g, p) in memberships:
      data[(r,g)].append(p)

    existing_rosters = {}
    for roster in self.prior_rosters:
        key = (roster.ride, roster.group)
        existing_rosters[key] = roster.id

    rosters = []
    for (r,g) in sorted(data):
      if (r,g) in existing_rosters:
        rosters.append(Roster(self.riders, existing_rosters[(r,g)], r, g, data[(r,g)]))
      else:
        rosters.append(Roster(self.riders, None, r, g, data[(r,g)]))
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
      num_scout_groups = []
      for g in range(0, self.params.max_groups):
        vars.group_active[(r,g)] = model.NewBoolVar(VarName('group_active', [r, g]))
        num_scouts_group = []
        for p in self.riders.AllRiders():
          me = vars.memberships[(r, g, p.id)]

          vars.groups[(r,g)].append(me)
          vars.groups_genders[(r,g)][p.gender].append(me)
          if p.IsLeader():
            vars.group_leaders[(r,g)].append(me)
            if p.type == Leader.Type.EXPERIENCED:
              vars.group_leaders_experienced[(r,g)].append(me)
            if p.type == Leader.Type.INEXPERIENCED:
              vars.group_leaders_inexperienced[(r,g)].append(me)
            if p.Scouted(r):
              vars.group_leaders_scouted[(r,g)].append(me)
              num_scouts_group.append(me)
            if p.gender == 'F':
              vars.group_leaders_female[(r,g)].append(me)
          else:
            vars.group_participants[(r,g)].append(me)

        group_has_scout = model.NewBoolVar(VarName('group_has_scout', [r, g]))
        model.Add(sum(num_scouts_group) >= 1).OnlyEnforceIf(group_has_scout)
        model.Add(sum(num_scouts_group) < 1).OnlyEnforceIf(group_has_scout.Not())
        num_scout_groups.append(group_has_scout)
      vars.num_scouts[r] = sum(num_scout_groups)

    # Constrain historical rosters to what they were.
    prior_ride_true = set()
    finalized = set()
    for roster in self.prior_rosters:
      if roster.finalized:
        for rider in [self.riders.Rider(r) for r in roster.rider_ids]:
          prior_ride_true.add((roster.ride, roster.group, rider.id))
        finalized.add((roster.ride, roster.group))
    for p in self.riders.AllRiders():
      for r in range(0, self.params.num_rides):
        for g in range(0, self.params.max_groups):
          if (r,g,p.id) in prior_ride_true:
            model.Add(vars.memberships[(r, g, p.id)] == 1)
          else:
            if r <= self.params.finalized_ride:# or (r,g) in finalized:
                model.Add(vars.memberships[(r, g, p.id)] == 0)

  def AddGroupConstraints(self, model, vars):
    """
    Defines the rigid constraints on each group.
    """
    # Define target group topology for each ride.
    for r in range(self.params.start_ride, self.params.num_rides):
      vars.num_groups[r] = model.NewIntVar(0, self.params.max_groups, VarName('num_groups', [r]))
      vars.target_participants[r] = model.NewIntVar(0, self.params.max_group_size, VarName('target_participants', [r]))
      vars.target_leaders[r] = model.NewIntVar(0, self.params.max_group_size, VarName('target_leaders', [r]))

    for r in range(self.params.start_ride, self.params.num_rides):
      #target_scouts_groups = model.NewIntVar(0, self.params.max_groups, VarName('target_scout_groups', [r]))
      #model.AddMinEquality(target_scouts_groups, [self.num_scouts[r], vars.num_groups[r]])
      #model.Add(vars.num_scouts[r] == target_scouts_groups)
      for g in range(0, self.params.max_groups):
        group_size = sum(vars.groups[(r,g)])
        group_active = vars.group_active[(r,g)]
        num_leaders = sum(vars.group_leaders[(r,g)])
        num_participants = sum(vars.group_participants[(r,g)])

        # Make sure we're setting exactly num_groups for the given ride.
        too_many_groups = model.NewBoolVar(VarName('too_many_groups', [r, g]))
        model.Add(g >= vars.num_groups[r]).OnlyEnforceIf(too_many_groups)
        model.Add(g < vars.num_groups[r]).OnlyEnforceIf(too_many_groups.Not())
        model.Add(group_size == 0).OnlyEnforceIf(too_many_groups)
        model.Add(group_size > 0).OnlyEnforceIf(too_many_groups.Not())

        # If the group isn't active it must be empty.
        model.Add(group_size == 0).OnlyEnforceIf(group_active.Not())

        # Each group must have at least two leaders, and at least one
        # experienced leader.
        model.Add(sum(vars.group_leaders[(r,g)]) >= 2).OnlyEnforceIf(group_active)
        model.Add(sum(vars.group_leaders_experienced[(r,g)]) >= 1).OnlyEnforceIf(group_active)

        # No lone riders of either gender.
        model.Add(sum(vars.groups_genders[(r,g)]['F']) != 1).OnlyEnforceIf(group_active)
        model.Add(sum(vars.groups_genders[(r,g)]['M']) != 1).OnlyEnforceIf(group_active)

        # Hard limit on even group sizes / number of leaders.
        model.AddLinearConstraint(num_participants - vars.target_participants[r], 0, 1).OnlyEnforceIf(group_active)
        model.AddLinearConstraint(num_leaders - vars.target_leaders[r], 0, 1).OnlyEnforceIf(group_active)

    # Make sure that groups with more leaders don't have fewer participants.
    for r in range(self.params.start_ride, self.params.num_rides):
      for g1 in range(0, self.params.max_groups):
        for g2 in range(0, self.params.max_groups):
            g1_has_more_leaders = model.NewBoolVar(VarName('more_leaders', [r, g1, g2]))
            model.Add(sum(vars.group_leaders[(r,g1)]) > sum(vars.group_leaders[(r,g2)])).OnlyEnforceIf(g1_has_more_leaders)
            model.Add(sum(vars.group_leaders[(r,g1)]) <= sum(vars.group_leaders[(r,g2)])).OnlyEnforceIf(g1_has_more_leaders.Not())
            model.Add(sum(vars.group_participants[(r,g1)]) >= sum(vars.group_participants[(r,g2)])).OnlyEnforceIf(g1_has_more_leaders)

  def AddRiderConstraints(self, model, vars):
    # Make sure every rider is in exactly one group if they're attending the
    # ride and zero groups if they aren't.
    for r in range(self.params.start_ride, self.params.num_rides):
      for p in self.riders.AllRiders():
        s = 0
        for g in range(0, self.params.max_groups):
          s += vars.memberships[(r, g, p.id)]
        model.Add(s == p.IsAvailable(r))

    # Make sure participants that need a woman leader are assigned a group with one.
    for r in range(self.params.start_ride, self.params.num_rides):
      for p in self.riders.AllRiders():
        for g in range(0, self.params.max_groups):
          if p.NeedsWomanLeader():
            model.Add(sum(vars.group_leaders_female[(r,g)]) > 0).OnlyEnforceIf(vars.memberships[(r,g,p.id)])

  def OptimizeGroupSize(self, model, vars):
    '''
    Try to make the groups roughly equal size relative to each other, but also
    not too big.
    '''
    penalties = []
    for r in range(self.params.start_ride, self.params.num_rides):
      # Have the minimum number of target_leaders for each group.
      model.Add(vars.target_leaders[r] >= 2)

      # Don't have too many target leaders.
      leader_penalty = model.NewIntVar(0, len(self.riders.AllLeaders()),
                                       VarName('leader_penalty', [r]))
      model.AddAbsEquality(leader_penalty, vars.target_leaders[r] - 2)
      penalties.append(leader_penalty)

      # Don't stray too far from 4 target participants.
      participant_penalty = model.NewIntVar(0, len(self.riders.AllParticipants()) + 4,
                                            VarName('participant_penalty', [r]))
      model.AddAbsEquality(participant_penalty, vars.target_participants[r] - 4)
      penalties.append(100*participant_penalty)
      participant_penalty2 = model.NewIntVar(0, len(self.riders.AllParticipants()) + 3,
                                            VarName('participant_penalty2', [r]))
      model.AddAbsEquality(participant_penalty2, vars.target_participants[r] - 3)
      penalties.append(100*participant_penalty2)

      # Penalize groups that stray too far from target_participants.
      for g in range(0, self.params.max_groups):
        num_participants = sum(vars.group_participants[(r,g)])
        group_active = vars.group_active[(r,g)]

        penalty = model.NewIntVar(0, len(self.riders.AllParticipants()), VarName('num_participants_penalty', [r, g]))
        model.AddAbsEquality(penalty, num_participants - vars.target_participants[r])
        penalty2 = model.NewIntVar(0, len(self.riders.AllParticipants()), VarName('num_participants_penalty2', [r, g]))
        model.Add(penalty2 == penalty).OnlyEnforceIf(group_active)
        model.Add(penalty2 == 0).OnlyEnforceIf(group_active.Not())
        penalties.append(penalty2)

    model.Minimize(sum(penalties))

  def OptimizePairings(self, model, vars):
    '''
    Maximize the number of pairs of different riders that ride together.
    '''
    # Compute the set of all possible pairs of riders, and then we try to
    # optimize for including as many pairs as possible in the rosters.
    all_pairs = set()
    for p1 in self.riders.AllRiders():
      for p2 in self.riders.AllRiders():
        if (p1.id != p2.id and (p2.id, p1.id) not in all_pairs):
          all_pairs.add((p1.id, p2.id))
    print("Number of riders: ", len(self.riders.AllRiders()))
    print("Number of total rider pairings: ", len(all_pairs))
    print()
    assert(math.isclose(len(all_pairs),
           math.factorial(len(self.riders.AllRiders()))/
           math.factorial(2)/
           math.factorial(len(self.riders.AllRiders())-2)))

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

    # Penalize groups where an inexperienced leader isn't with 2 other leaders.
    for r in range(0, self.params.num_rides):
      scores.append(100*vars.num_scouts[r])
      for g in range(0, self.params.max_groups):
        inexperienced = sum(vars.group_leaders_inexperienced[(r,g)])
        num_leaders = sum(vars.group_leaders[(r,g)])
        group_active = vars.group_active[(r,g)]

        penalty = model.NewIntVar(0, len(self.riders.AllLeaders()), VarName('inexperienced_leader_penalty', [r, g]))
        model.AddAbsEquality(penalty, num_leaders - inexperienced - 2)
        penalty2 = model.NewIntVar(0, len(self.riders.AllLeaders()), VarName('inexperienced_leader_penalty2', [r, g]))
        model.Add(penalty2 == penalty).OnlyEnforceIf(group_active)
        model.Add(penalty2 == 0).OnlyEnforceIf(group_active.Not())
        scores.append(-200*penalty2)

    for (p1, p2) in all_pairs:
      vars.paired[(p1, p2)] = model.NewBoolVar(VarName('paired', [p1, p2]))
      p1_obj = self.riders.Rider(p1)
      p2_obj = self.riders.Rider(p2)

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
        for mr in range(1, self.params.num_rides):
            not_previously_available = True
            for mrp in range(1, mr):
                not_previously_available = (not_previously_available and
                    (not p1_obj.IsAvailable(mrp) or not p2_obj.IsAvailable(mrp)))
            if (r >= self.params.start_ride and
                r == mr and MentorPair(p1, p2) and
                p1_obj.IsAvailable(r) and p2_obj.IsAvailable(r) and
                not_previously_available):
              print('Adding ride %d mentor constraint for'%r, p1_obj.name, p2_obj.name)
              model.AddBoolOr(paired_on_ride)

        ride = self.rides[r]
        if (p1_obj.IsAvailable(r) and p2_obj.IsAvailable(r) and
            ride.PairRidersTogether(p1, p2)):
            print('Adding ride %d bonus for'%r, p1_obj.name, p2_obj.name)
            scores.append(1000 * sum(paired_on_ride))

        # Augment scores with match scores
        scores.append(self.riders.GetMatchScore(p1, p2) * sum(paired_on_ride))

      if not p1_obj.Ignore() and not p2_obj.Ignore():
        model.AddBoolOr(paired_in_group).OnlyEnforceIf(vars.paired[(p1, p2)])
        model.AddBoolAnd(not_paired_in_group).OnlyEnforceIf(vars.paired[(p1, p2)].Not())

      bonus_pairs = model.NewIntVar(0, self.params.num_rides,
                                    VarName('bonus_pairs', [p1, p2]))
      model.AddAbsEquality(bonus_pairs, 1 - sum(paired_in_group))
      scores.append(-10*bonus_pairs)

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

  def SolveAndLog(self, solver, printer, model, vars):
    status = solver.Solve(model, printer)
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
    printer = Printer(vars, self.riders)
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    solver.parameters.max_time_in_seconds = self.params.time_limit

    results = self.SolveAndLog(solver, printer, model, vars)
    if results is None:
      return

    print()
    for (k,vs) in vars.target_participants.items():
      vn = vars.num_groups[k]
      vl = vars.target_leaders[k]
      print('Ride %d >> %d num_groups : target_participants %d and target_leaders %d' %
            (k+1, solver.Value(vn), solver.Value(vs), solver.Value(vl)))

    hints = vars.RecordHints(solver)
    print()
    print('Optimzing pairings...')
    vars = Vars()
    model = self.BuildBaseModel(vars)
    vars.RestoreHints(model, hints)
    self.OptimizePairings(model, vars)
    print(model.ModelStats())

    printer = Printer(vars, self.riders)
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    solver.parameters.max_time_in_seconds = self.params.time_limit

    results = self.SolveAndLog(solver, printer, model, vars)
    if results is None:
      return

    memberships = []
    for (k,v) in vars.memberships.items():
      if (solver.Value(v)):
        memberships.append(k)
    return self.GetRosters(memberships)
