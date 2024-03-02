import logging
import requests

from sig_groups.ride import Roster
from sig_groups.rider import Leader, Participant, Match

class AirtableClient(object):
    def __init__(self, airtable_config, ride_config):
        self.base = airtable_config['base']
        self.key = airtable_config['key']
        logging.info('Initializing Airtable client for base: ', self.base)

        self.ride_num = {}
        for r in ride_config:
            self.ride_num[r['airtable_id']] = r['rank']

    def _GetAirtable(self, url_path):
        url = "https://api.airtable.com/v0/" + self.base + "/" + url_path
        headers = {'Authorization': 'Bearer ' + self.key}
        return requests.get(url, headers=headers)

    def _PostAirtable(self,url_path, data):
        url = "https://api.airtable.com/v0/" + self.base + "/" + url_path
        headers = {'Authorization': 'Bearer ' + self.key,
                 'Content-Type': 'application/json'}
        return requests.post(url, headers=headers, json=data)

    def _PutAirtable(self, url_path, data):
        url = "https://api.airtable.com/v0/" + self.base + "/" + url_path
        headers = {'Authorization': 'Bearer ' + self.key,
                 'Content-Type': 'application/json'}
        return requests.put(url, headers=headers, json=data)

    def _LoadTable(self, table, construct):
      records = []
      response = self._GetAirtable(table)
      for record in response.json()['records']:
        new = construct(record)
        records.append(new)
      return records

    def LoadLeaders(self):
      return self._LoadTable("Leaders", _CreateLeader)

    def LoadParticipants(self):
      return self._LoadTable("Participants", _CreateParticipant)

    def GetPriorRosters(self, rider_data):
      rosters = []
      response = self._GetAirtable('Rosters')
      for r in response.json()['records']:
        id = r['id']
        group = r['fields']['Group']
        ride = self.ride_num[r['fields']['Ride'][0]]
        rider_ids = []
        if 'Leaders' in r['fields']:
            rider_ids.extend(r['fields']['Leaders'])
        if 'Participants' in r['fields']:
            rider_ids.extend(r['fields']['Participants'])
        finalized = False
        if 'Finalized' in r['fields'] and r['fields']['Finalized'] == True:
           finalized = True
        rosters.append(Roster(rider_data, id, ride, group, rider_ids, finalized))
      return rosters

    def CreateRoster(self, roster, rides):
      ride_to_id = {}
      for r in rides:
        ride_to_id[r.num] = r.airtable_id

      if roster.finalized:
        print('Skipping finalized roster: ', r.id)
        return
      leaders = roster.GetLeaderIds()
      participants = roster.GetParticipantIds()
      fields = {
        'Ride': [ride_to_id[roster.ride]],
        'Group': roster.group,
        'Leaders': leaders,
        'Participants': participants,
      }
      if roster.id is not None:
        record = {'id': roster.id, 'fields': fields}
        print(record)
        resp = self._PutAirtable('Rosters', { 'records': [record] })
        print(resp.content)
      else:
        record = {'fields': fields}
        print(record)
        resp = self._PostAirtable('Rosters', { 'records': [record] })
        print(resp.content)

def _LoadAvailability(rider, json):
  if 'Availability' in json['fields']:
    for r in json['fields']['Availability']:
      rider.SetAvailable(int(r[len("Ride "):]) - 1)

def _LoadScouted(rider, json):
  if 'Scouted' in json['fields']:
    for ride_id in json['fields']['Scouted']:
      rider.scouted.add(ride_id)

def _CreateLeader(json):
    l = Leader(json['id'], json['fields']['Name'])
    l.gender = json['fields']['Gender']
    _LoadAvailability(l, json)
    _LoadScouted(l, json)
    if len(l.availability) < 1:
      l.part_time = True
    if json['fields']['Experience'] == 'Experienced Leader':
      l.type = Leader.Type.EXPERIENCED
    elif json['fields']['Experience'] == 'Inexperienced Leader':
      l.type = Leader.Type.INEXPERIENCED
    elif json['fields']['Experience'] == 'New Leader':
      l.type = Leader.Type.NEW
    return l

def _CreateParticipant(json):
    p = Participant(json['id'], json['fields']['Name'])
    p.gender = json['fields']['Gender']
    try:
      p.mentor = json['fields']['Mentor'][0]
    except KeyError: pass
    try:
      p.status = json['fields']['Status']
    except KeyError: pass

    if p.status == 'Progressing':
        p.status = 'Pr'
    elif p.status == 'Red Flag':
        p.status = 'RF'
    elif p.status == 'Out':
        p.status = 'O'
    elif p.status == 'Potential Leader':
        p.status = 'PL'

    if 'Woman Leader Required' in json['fields']:
        p.woman_leader_req = True
    _LoadAvailability(p, json)
    return p

def _CreateMatch(json):
    ps = []
    for k in ['P1', 'P2', 'L1', 'L2']:
        try:
            ps.append(json['fields'][k][0])
        except:
            pass
    assert(len(ps) == 2)
    obj = Match(*ps)
    words = json['fields']['Match']
    if words == 'Bad Match':
        obj.score = -50
    elif words == 'Good Match':
        obj.score = 5
    elif words == 'Meh Match':
        obj.score = -5
    elif words == 'Couple':
        obj.score = 1
        obj.couple = True
    elif words == 'Grad Ride':
        obj.grad_ride = True
    return obj

