from datetime import datetime
from sig_groups.rider import Leader, Participant

class Roster(object):
    def __init__(self, id, ride, group, riders, finalized=False):
        self.id = id
        self.ride = ride
        self.group = group
        self.riders = riders
        self.finalized = finalized

    def GetRiderStr(self, i):
      return ('   ' + self.riders[i].RosterString())

    def __len__(self):
      return len(self.riders)

    def __str__(self):
        s = ('Ride %d'%(self.ride+1) + ' Group %d'%(self.group+1) + '\n')
        for i in range(0, len(self.riders)):
            s += self.GetRiderStr(i)
            s += '\n'
        return s

class Rosters(object):
    def __init__(self, rosters):
        self.rosters = sorted(list(rosters), key=lambda x: x.group)
        self.finalized = all(r.finalized for r in self.rosters)
        for r in self.rosters:
            self.ride = r.ride
            break

    def SlackBlocks(self):
        s = '\n'.join(str(s) for s in self.rosters)
        finalized_msg = f":computer: These rosters are a *DRAFT* (last updated {datetime.now()})."
        if self.finalized:
            finalized_msg = f":white_check_mark: These rosters are *FINALIZED*."
        return [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Ride {self.ride + 1} Rosters",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{finalized_msg}",
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{s}```",
                    }
                }
                ]
