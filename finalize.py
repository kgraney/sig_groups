import sys
sys.path.insert(1, '/usr/local/google/home/kmg/')
sys.path.insert(1, '/mnt/c/Users/Kevin Graney/SIG Groupings/')

from sig_groups.ride import Ride, Rosters
from sig_groups.config import LoadConfigFile
from sig_groups.airtable import AirtableClient
from sig_groups.slack import SlackClient
from sig_groups.rider import RiderData
from sig_groups.formatting import PrintRosters

config = LoadConfigFile("configs/2024.yaml")
rides = [Ride(x) for x in config.Rides()]

airtable_client = AirtableClient(config.Airtable(), config.Rides())
rider_data = RiderData(airtable_client.LoadLeaders(), airtable_client.LoadParticipants(), [])

rosters = airtable_client.GetPriorRosters(rider_data)

slack_client = SlackClient(config.Slack(), rides)
PrintRosters(rosters, rider_data)
for ride in [8]:
    ride_rosters = Rosters(r for r in rosters if r.ride == ride)
    slack_client.PostRoster(ride_rosters)

    slack_client.PostFinal(ride_rosters)
