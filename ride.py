from sig_groups.rider import Leader, Participant

class Roster(object):
    def __init__(self, ride, group, riders, finalized=False):
        self.ride = ride
        self.group = group
        self.riders = riders
        self.finalized = finalized

    def GetRiderStr(self, i):
      r = self.riders[i]
      l = '  '
      if r.IsLeader():
          l = 'L'
          l += '*' if r.experienced else ' '
      return ('   ' + l + ' ' + r.gender + ' ' + r.name)

    def __len__(self):
      return len(self.riders)

    def __str__(self):
        s = ('Ride %d'%(self.ride+1) + ' Group %d'%(self.group+1) + '\n')
        for i in range(0, len(self.riders)):
            s += self.GetRiderStr(i)
            s += '\n'
        return s
