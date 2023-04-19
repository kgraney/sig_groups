import yaml

class Config:
    def __init__(self, yaml):
        self.yaml = yaml

    def Slack(self):
        return self.yaml['integrations']['slack']

    def Airtable(self):
        return self.yaml['integrations']['airtable']

    def Rides(self):
        return self.yaml['rides']

    def Matches(self):
        return self.yaml['matches']

    def Finalized(self):
        return self.yaml['algorithm']['start_ride'] - 1

    def StartRide(self):
        return self.yaml['algorithm']['start_ride']

    def NumRides(self):
        return len(self.yaml['rides'])

    def AlgorithmParams(self):
        return self.yaml['algorithm']

def LoadConfigFile(path):
    with open(path, "r") as yamlfile:
        data = yaml.load(yamlfile, Loader=yaml.FullLoader)
        return Config(data)

