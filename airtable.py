import requests

from sig_groups.ride import Roster
from sig_groups.rider import Leader, Participant, Match

def _LoadAvailability(rider, json):
  if 'Availability' in json['fields']:
    for r in json['fields']['Availability']:
      rider.SetAvailable(int(r[len("Ride "):]) - 1)

def _CreateLeader(json):
    l = Leader(json['id'], json['fields']['Name'])
    l.gender = json['fields']['Gender']
    _LoadAvailability(l, json)
    if len(l.availability) < 5:
      l.part_time = True
    if json['fields']['Experience'] == 'Experienced Leader':
      l.experienced = True
    return l

def _CreateParticipant(json):
    p = Participant(json['id'], json['fields']['Name'])
    p.gender = json['fields']['Gender']
    try:
      p.mentor = json['fields']['Mentor'][0]
    except KeyError: pass
    try:
      p.status = json['fields']['status']
    except KeyError: pass

    if p.status == 'Progressing':
        p.status = 'Pr'
    elif p.status == 'Red Flag':
        p.status = 'RF'
    elif p.status == 'Out':
        p.status = 'O'
    elif p.status == 'Potential Leader':
        p.status = 'PL'
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
        obj.score = -1000
    elif words == 'Good Match':
        obj.score = 300
    elif words == 'Meh Match':
        obj.score = -100
    return obj

def _GetAirtableKey():
    #key_file = "/mnt/c/Users/Kevin Graney/Desktop/airtable_key.txt"
    key_file = "/usr/local/google/home/kmg/airtable_key.txt"
    airtable_api_key = None
    with open(key_file, 'r') as f:
      airtable_api_key = f.readlines()[0].strip()
    return airtable_api_key

AIRTABLE_BASE = 'app1abUFnsuwfcY2a'
AIRTABLE_KEY = _GetAirtableKey()

def _GetAirtable(url_path):
    url = "https://api.airtable.com/v0/" + AIRTABLE_BASE + "/" + url_path
    headers = {'Authorization': 'Bearer ' + AIRTABLE_KEY}
    return requests.get(url, headers=headers)

def _PostAirtable(url_path, data):
    url = "https://api.airtable.com/v0/" + AIRTABLE_BASE + "/" + url_path
    headers = {'Authorization': 'Bearer ' + AIRTABLE_KEY,
             'Content-Type': 'application/json'}
    return requests.post(url, headers=headers, json=data)

def _LoadTable(table, construct):
  records = []
  response = _GetAirtable(table)
  for record in response.json()['records']:
    new = construct(record)
    records.append(new)
  return records

def LoadLeaders():
  return _LoadTable("Leaders", _CreateLeader)

def LoadParticipants():
  return _LoadTable("Participants", _CreateParticipant)

def LoadMatches():
  return _LoadTable("Matches", _CreateMatch)

_AIRTABLE_TO_RIDE = {}
_RIDE_TO_AIRTABLE = {}
response = _GetAirtable('Rides')
for (i, r) in enumerate(response.json()['records']):
    _RIDE_TO_AIRTABLE[r['fields']['Ride Number']] = r['id']
    _AIRTABLE_TO_RIDE[r['id']] = r['fields']['Ride Number']

def RideNumToAirtableId(num):
    return _RIDE_TO_AIRTABLE[num + 1]

def AirtableIdToRideNum(id):
    return _AIRTABLE_TO_RIDE[id] - 1

def GetPriorRosters(data):
  rosters = []
  response = _GetAirtable('Rosters')
  for r in response.json()['records']:
    group = r['fields']['Group']
    ride = AirtableIdToRideNum(r['fields']['Ride'][0])
    riders = [data.Rider(x)
              for x in r['fields']['Leaders'] + r['fields']['Participants']]
    rosters.append(Roster(ride, group, riders))
  return rosters
