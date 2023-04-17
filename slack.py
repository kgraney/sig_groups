import json
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token='XXXXX')

channels = {
    'kmg-test': {'id': 'C04TC4H2QD6', 'ts': None}, #'ts': '1678149403.712329'},
    'roster': {'id': 'C04N5P9G3DJ'},
    0: {'id': 'C04N3683F8T', 'ts': '1678158256.045639'},
    1: {'id': 'C04N368A4GK', 'ts': '1678158256.338269'},
    2: {'id': 'C04MNP915RV', 'ts': '1678158256.747769'},
    3: {'id': 'C04MNP96HP1', 'ts': '1678158257.104559'},
    4: {'id': 'C04MWMBCQJJ', 'ts': '1678158257.405489'},
    5: {'id': 'C04N5PDFE92', 'ts': '1678158257.716239'},
    6: {'id': 'C04NT0LFG9E', 'ts': '1678158258.027709'},
    7: {'id': 'C04N369KE2F', 'ts': '1678158258.307669'},
    8: {'id': 'C04NFUE76RX', 'ts': '1678158258.598759'},
    9: {'id': 'C04N36A6K6X', 'ts': '1678158258.963399'},
}

def PostRoster(rosters):
  ride = rosters.ride
  channel_id = channels[ride]['id']
  msg_ts = channels[ride]['ts']
  print(f'Writing to {channel_id} at {msg_ts} for ride {ride}')

  try:
    if msg_ts is None:
        result = client.chat_postMessage(channel=channel_id, text='roster',
            blocks=json.dumps(rosters.SlackBlocks()))
        print(result)
        timestamp = result.get('ts')
        client.pins_add(channel=channel_id, timestamp=timestamp)
        print(result)
        print(f"ride = {ride} channel = {channel_id} ts = {timestamp}")
    else:
        result = client.chat_update(channel=channel_id, ts=msg_ts, text='roster',
            blocks=json.dumps(rosters.SlackBlocks()))
        print(result)
  except SlackApiError as e:
    print(f"Error posting message: {e}")

def PostRosterStatus():
    channel_id = channels['roster']['id']
    try:
        result = client.files_upload(channels=channel_id, title=f"Algorithm Pairings", initial_comment=f"TheAlgorithm™ status as of {datetime.now()}:  This shows who's ridden together as of the next ride and through the modeled conclusion of the program.  Colors indicate frequency of riding together.", file="/tmp/pairings.png")
        print(result)
    except SlackApiError as e:
        print("Error uploading file: {}".format(e))



