from collections import defaultdict
from enum import Enum

class Rider(object):
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.gender = None
    self.availability = set()
    self.status = ''

  def IsLeader(self):
    return False

  def NeedsWomanLeader(self):
    return False

  def SetAvailable(self, ride_num):
    self.availability.add(ride_num)

  def IsAvailable(self, ride_num):
    return ride_num in self.availability

  def RosterString(self):
    return ('   ' + self.gender + ' ' + self.name)


class Leader(Rider):
  class Type(Enum):
    EXPERIENCED = 1
    NEW = 2
    INEXPERIENCED = 3

  def __init__(self, id, name):
    super().__init__(id, name)
    self.type = Leader.Type.NEW
    self.part_time = False
    self.scouted = set()

  def IsLeader(self):
    return True

  def Scouted(self, ride):
    return ride in self.scouted

  def Ignore(self):
    return self.part_time

  def RosterString(self):
    l = 'L'
    if self.type == Leader.Type.EXPERIENCED:
        l += '*'
    elif self.type == Leader.Type.INEXPERIENCED:
        l += '-'
    else:
        l += ' '
    return (l + ' ' + self.gender + ' ' + self.name)


class Participant(Rider):
  def __init__(self, id, name):
    super().__init__(id, name)
    self.mentor = None
    self.status = ''
    self.woman_leader_req = False

  def NeedsWomanLeader(self):
    return self.woman_leader_req

  def Ignore(self):
    return self.status == 'O'

class RiderData(object):
  def __init__(self, leaders, participants, matches):
    self.rider_map = {}
    for x in leaders:
      self.rider_map[x.id] = x
    for x in participants:
      self.rider_map[x.id] = x

    self.matches = {}  # map from (id, id) -> Match
    for m in matches:
      self.matches[(m.p1, m.p2)] = m
      self.matches[(m.p2, m.p1)] = m

    self.couples = set()

  def AllRiders(self):
    return self.rider_map.values()

  def AllFtRiders(self):
    result = []
    for v in self.rider_map.values():
      if v.Ignore():
        continue
      result.append(v)
    return result

  def AllFtParticipants(self):
    result = []
    for v in self.rider_map.values():
      if v.Ignore() or v.IsLeader():
        continue
      result.append(v)
    return result

  def AllLeaders(self):
    result = []
    for v in self.rider_map.values():
      if isinstance(v, Leader):
        result.append(v)
    return result

  def AllParticipants(self):
    result = []
    for v in self.rider_map.values():
      if isinstance(v, Participant):
        result.append(v)
    return result

  def GetMatchScore(self, p1, p2):
    try:
      return self.matches[(p1, p2)].score
    except KeyError:
      return 1

  def IsCouple(self, p1, p2):
    try:
      return self.matches[(p1, p2)].couple
    except KeyError:
      return False

  def IsGradRide(self, p1, p2):
    try:
      return self.matches[(p1, p2)].grad_ride
    except KeyError:
      return False

  def Rider(self, id):
    return self.rider_map[id]

class Match(object):
  def __init__(self, p1, p2):
    self.p1 = p1
    self.p2 = p2
    self.score = 0
    self.couple = False
    self.grad_ride = False
