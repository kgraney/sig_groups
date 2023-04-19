from datetime import datetime
from sig_groups.rider import Leader, Participant

class Ride(object):
    def __init__(self, ride_config):
        self.num = ride_config['rank']
        self.title = ride_config['title']
        self.airtable_id = ride_config['airtable_id']
        self.slack_channel = ride_config['slack_channel']
        self.slack_roster_post = ride_config['slack_roster_post']


class Roster(object):
    def __init__(self, rider_data, id, ride, group, rider_ids, finalized=False):
        self.rider_data = rider_data
        self.id = id
        self.ride = ride
        self.group = group
        self.rider_ids = rider_ids
        self.finalized = finalized

    def GetLeaderIds(self):
        return [x for x in self.rider_ids if self.rider_data.Rider(x).IsLeader()]

    def GetParticipantIds(self):
        return [x for x in self.rider_ids if not self.rider_data.Rider(x).IsLeader()]

    def GetRiderStr(self, i):
        return ('   ' + self.rider_data.Rider(self.rider_ids[i]).RosterString())

    def __len__(self):
        return len(self.rider_ids)

    def __str__(self):
        s = ('Ride %d'%(self.ride+1) + ' Group %d'%(self.group+1) + '\n')
        for i in range(0, len(self.rider_ids)):
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
