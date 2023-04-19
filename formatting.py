import imageio
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from collections import defaultdict

def PrintAvailabilityTable(riders, num_rides):
    s = []
    for r in range(0, num_rides):
        s.append('Ride %d' % (r + 1))
    print(("{: <25} " + "{: <10}"*num_rides).format('', *s))
    for p in sorted(riders, key=lambda x: x.name):
        avails = []
        for r in range(0, num_rides):
            avails.append(p.IsAvailable(r))
        avail_str = ['X' if x else '' for x in avails]
        print(("{: <25} " + "{: <10}"*num_rides).format(p.name, *avail_str))

def PrintRosters(rosters, rider_data):
    by_ride = defaultdict(lambda: [])
    for r in rosters:
        by_ride[r.ride].append(r)

    for ride, rs in sorted(by_ride.items()):
        print('\n\nRide %d' % (ride+1))
        rows = max(len(r) for r in rs)
        cols = len(rs)

        matrix = [['' for _ in range(cols)] for _ in range(rows)]

        i = 0
        j = 0
        for r in rs:
            for p in r.rider_ids:
                matrix[j][i] = rider_data.Rider(p).RosterString()
                j += 1
            j = 0
            i += 1

        for row in matrix:
            print(("{: <30} "*cols).format(*row))

def GenerateGif(config, rosters, rider_data):
    # map from ride -> pair
    rides_together_through = defaultdict(lambda: defaultdict(lambda: 0))

    for r in rosters:
      seen = set()
      for p1 in r.rider_ids:
        for p2 in r.rider_ids:
          canonical_pair = tuple(sorted((p1,p2)))
          if canonical_pair in seen:
            continue
          seen.add(canonical_pair)
          for i in range(r.ride, config.NumRides()):
            rides_together_through[i][canonical_pair] += 1

    people = rider_data.AllRiders()

    def PairFrequencyPlot(finalized, ride):
        final_pair_matrix = np.zeros(shape=(len(people), len(people)))
        modeled_pair_matrix = np.zeros(shape=(len(people), len(people)))
        for i, p1 in enumerate(people):
          for j, p2 in enumerate(people):
            canonical_pair = tuple(sorted((p1.id, p2.id)))
            if i <= j:
                final_pair_matrix[j][i] = rides_together_through[finalized][canonical_pair]
                modeled_pair_matrix[i][j] = rides_together_through[ride][canonical_pair]
                modeled_pair_matrix[j][i] = rides_together_through[config.NumRides() - 1][canonical_pair]

        labels = [p.name for p in people]

        maxval = np.max([np.max(final_pair_matrix), np.max(modeled_pair_matrix)])
        fig, (ax1, ax2) = plt.subplots(1,2, figsize=(20,20))
        ax1.set_title('Modeled to Finish / Through Ride %d' % (ride + 1))
        ax1.set_xticks(np.arange(0, len(people), 1.0), labels=labels, minor=True, rotation=90, fontsize='x-small')
        ax1.set_xticks(np.arange(0, len(people), 1.0), labels=labels, minor=False, rotation=90, fontsize='x-small')
        ax1.set_yticks(np.arange(0, len(people), 1.0), labels=labels, minor=True, fontsize='x-small')
        ax1.set_yticks(np.arange(0, len(people), 1.0), labels=labels, minor=False, fontsize='x-small')
        ax2.set_xticks(np.arange(0, len(people), 1.0), labels=labels, minor=True, rotation=90, fontsize='x-small')
        ax2.set_xticks(np.arange(0, len(people), 1.0), labels=labels, minor=False, rotation=90, fontsize='x-small')

        #ax1.set_xticks(range(0, len(people)), labels=labels, minor=False, rotation=90, fontsize='xx-small')

        #ax1.set_xticklabels(labels, rotation=90, horizontalalignment='right')
        ax1.matshow(modeled_pair_matrix, vmin=0, vmax=maxval, cmap=plt.cm.viridis)
        ax2.set_title('Through Ride %d' % (finalized + 1))
        ax2.matshow(final_pair_matrix, vmin=0, vmax=maxval, cmap=plt.cm.viridis)
        #fig.colorbar(plot2)
        if ride <= finalized:
            fig.savefig('/tmp/pairings-%d.png' % ride, facecolor='white', transparent=False, bbox_inches='tight')
        else:
            fig.savefig('/tmp/pairings-%d.png' % ride, facecolor='yellow', transparent=False, bbox_inches='tight')
    for i in range(0, config.NumRides()):
        PairFrequencyPlot(config.Finalized(), i)

    with imageio.get_writer('/tmp/pairs.gif', mode='I', fps=2) as writer:
        files = ['/tmp/pairings-%d.png' % i for i in range(0, config.NumRides())]
        for filename in files:
            image = imageio.imread(filename)
            writer.append_data(image)
