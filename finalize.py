import argparse
import sys
sys.path.insert(1, '/usr/local/google/home/kmg/')
sys.path.insert(1, '/mnt/c/Users/Kevin Graney/SIG Groupings/')
sys.path.insert(1, '/usr/local/google/home/amfisher/dsig24')
sys.path.insert(1, '/mnt/c/Users/Allison Fisher/SIG Groupings/')

from sig_groups.ride import Ride, Rosters
from sig_groups.config import LoadConfigFile
from sig_groups.airtable import AirtableClient
from sig_groups.slack import SlackClient
from sig_groups.rider import RiderData
from sig_groups.formatting import PrintRosters, GenerateGif

def finalize(config, ride, publish=False):
    rides = [Ride(x) for x in config.Rides()]

    airtable_client = AirtableClient(config.Airtable(), config.Rides())
    rider_data = RiderData(airtable_client.LoadLeaders(), airtable_client.LoadParticipants())

    rosters = airtable_client.GetPriorRosters(rider_data)

    slack_client = SlackClient(config.Slack(), rides)
    print('Finalizing ride %d...' % (ride+1))

    ride_rosters = Rosters(r for r in rosters if r.ride == ride)
    print('This is the finalized roster for ride %d...' % (ride+1))
    PrintRosters(ride_rosters.rosters, rider_data)
    GenerateGif(config, rosters, rider_data)

    if (publish):
        print('Posting to slack...')
        slack_client.PostRoster(ride_rosters)
        slack_client.PostFinal(ride_rosters)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='finalize.py',
        description='Finalizes through the provided ride.')
    parser.add_argument('ride', type=int,
        help='Specifies the ride number to finalize, starting at 0.')
    parser.add_argument('-c', '--config', help='Config file path',
        default='configs/2024.yaml')
    parser.add_argument('-p', '--publish', action='store_true',
        default=False,
        help='Publish the finalized Roster.')

    args = parser.parse_args()
    print('Loading config file %s....' % args.config)
    config = LoadConfigFile(args.config)
    finalize(config, args.ride, args.publish)
