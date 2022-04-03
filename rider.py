from collections import defaultdict

class Rider(object):
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.gender = None
    self.availability = set()
    self.status = ''

  def Invalid(self):
    return len(self.availability) == 0

  def IsLeader(self):
    return False

  def NeedsWomanLeader(self):
    return False

  def SetAvailable(self, ride_num):
    self.availability.add(ride_num)

  def IsAvailable(self, ride_num):
    return ride_num in self.availability

class Leader(Rider):
  def __init__(self, id, name):
    super().__init__(id, name)
    self.experienced = False
    self.part_time = False
    self.scouted = set()

  def IsLeader(self):
    return True

  def Scouted(self, ride):
    return ride in self.scouted

class Participant(Rider):
  def __init__(self, id, name):
    super().__init__(id, name)
    self.mentor = None
    self.status = ''
    self.woman_leader_req = False

  def NeedsWomanLeader(self):
    return self.woman_leader_req


class RiderData(object):
  def __init__(self, leaders, participants, matches):
    self.rider_map = {}
    for x in leaders:
      self.rider_map[x.id] = x
    for x in participants:
      self.rider_map[x.id] = x

    self.matches = {}  # map from (id, id) -> score
    for m in matches:
      self.matches[(m.p1, m.p2)] = m.score
      self.matches[(m.p2, m.p1)] = m.score

  def AllRiders(self):
    return self.rider_map.values()

  def AllFtRiders(self):
    result = []
    for v in self.rider_map.values():
      if isinstance(v, Leader) and v.part_time:
        continue
      if v.Invalid():
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
      return self.matches[(p1, p2)]
    except KeyError:
      return 1

  def Rider(self, id):
    return self.rider_map[id]

class Match(object):
  def __init__(self, p1, p2):
    self.p1 = p1
    self.p2 = p2
    self.score = 0
