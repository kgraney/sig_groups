import sys
sys.path.insert(1, '/usr/local/google/home/kmg/')
sys.path.insert(1, '/mnt/c/Users/Kevin Graney/SIG Groupings/')

from sig_groups.airtable import AirtableClient
from sig_groups.config import LoadConfigFile
from sig_groups.formatting import PrintAvailabilityTable, PrintRosters, GenerateGif
from sig_groups.optimizer import AlgorithmTM, Params
from sig_groups.ride import Ride, Rosters
from sig_groups.rider import RiderData
from sig_groups.slack import SlackClient

config = LoadConfigFile("configs/2024.yaml")
rides = [Ride(x) for x in config.Rides()]

airtable_client = AirtableClient(config.Airtable(), config.Rides())

rider_data = RiderData(airtable_client.LoadLeaders(), airtable_client.LoadParticipants())
for m in config.Matches():
    rider_data.SetMatchScore(m['r1'], m['r2'], m['score'])

prior_rosters = airtable_client.GetPriorRosters(rider_data)
#PrintRosters(prior_rosters, rider_data)

params = Params()
params.start_ride = config.StartRide()
params.finalized_ride = config.Finalized()
params.max_group_size = 20
params.time_limit = config.AlgorithmParams()['time_limit']
params.num_rides = 10

for ride in rides:
    for constraint in config.Constraints(ride.num):
        ride.AddTogetherConstraint(constraint['riders'])

alg = AlgorithmTM(rider_data, rides, prior_rosters, params)
rosters = alg.Solve()
#PrintRosters(rosters, rider_data)

GenerateGif(config, rosters, rider_data)

slack_client = SlackClient(config.Slack(), rides)
slack_client.PostRosterStatus()

for ride in range(params.start_ride, params.num_rides):
    ride_rosters = Rosters(r for r in rosters if r.ride == ride)
    for roster in ride_rosters.rosters:
        airtable_client.CreateRoster(roster, rides)
    slack_client.PostRoster(ride_rosters)
