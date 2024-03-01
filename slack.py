import json
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class SlackClient(object):
    def __init__(self, slack_config, rides):
        self.client = WebClient(token=slack_config['token'])
        self.report_channel = slack_config['reports_channel']
        self.public_uploads_channel = slack_config['public_uploads_channel']

        self.channel = {}
        self.post_ts = {}
        for r in rides:
            self.channel[r.num] = r.slack_channel
            self.post_ts[r.num] = r.slack_roster_post

    def PostRosterStatus(self):
        try:
            result = self.client.files_upload(channels=self.report_channel, title=f"Algorithm Pairings", initial_comment=f"TheAlgorithm™ status as of {datetime.now()}.", file="/tmp/pairs.gif")
            print(result)
        except SlackApiError as e:
            print("Error uploading file: {}".format(e))

    def PostRoster(self, rosters):
      ride = rosters.ride
      channel_id = self.channel[ride]
      msg_ts = self.post_ts[ride]
      print(f'Writing to {channel_id} at {msg_ts} for ride {ride}')

      image_id = None
      try:
        result = self.client.files_upload(channels=self.public_uploads_channel, title=f"Algorithm Pairings", initial_comment=f"TheAlgorithm™ status as of {datetime.now()}.", file="/tmp/pairings-%d.png" % ride, filetype="png")
        print(result)
        image_id = result['file']['id']
      except SlackApiError as e:
        print("Error uploading file: {}".format(e))
        return

      try:
        if msg_ts is None:
            result = self.client.chat_postMessage(channel=channel_id, text='roster',
                blocks=json.dumps(rosters.SlackBlocks()))
            print(result)
            timestamp = result.get('ts')
            self.client.pins_add(channel=channel_id, timestamp=timestamp)
            print(result)
            print(f"ride = {ride} channel = {channel_id} ts = {timestamp}")
        else:
            result = self.client.chat_update(channel=channel_id, ts=msg_ts, text='roster',
                blocks=json.dumps(rosters.SlackBlocks(image_id)))
            print(result)
      except SlackApiError as e:
        print(f"Error posting message: {e}")

    def PostFinal(self, rosters):
      ride = rosters.ride
      channel_id = self.channel[ride]
      msg_ts = self.post_ts[ride]
      try:
        result = self.client.chat_getPermalink(channel=channel_id, message_ts=msg_ts)
        print(result)
        link = result['permalink']

        result = self.client.chat_postMessage(channel=channel_id, text='The rosters are finalized for this ride!  See them here: %s' % link)
        print(result)
      except SlackApiError as e:
        print(f"Error posting message: {e}")


