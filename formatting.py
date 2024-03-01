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

    # We want the chart to focus on riders attending more rides and filter out
    # those (particulary stale leader entries) that don't attend any.
    people = sorted(rider_data.AllRiders(), key=lambda x: x.NumAvailableRides(), reverse=True)
    people = [x for x in people if x.NumAvailableRides() > 0]

    def PairFrequencyPlot(finalized, ride):
        modeled_pair_matrix = np.zeros(shape=(len(people), len(people)))
        new_pair_matrix = np.zeros(shape=(len(people), len(people)))
        for i, p1 in enumerate(people):
          for j, p2 in enumerate(people):
            canonical_pair = tuple(sorted((p1.id, p2.id)))
            if i <= j:
                modeled_pair_matrix[i][j] = rides_together_through[ride][canonical_pair]
                modeled_pair_matrix[j][i] = rides_together_through[config.NumRides() - 1][canonical_pair]
                if i != j:
                    new_pair_matrix[i][j] = (rides_together_through[ride][canonical_pair]
                                             - rides_together_through[ride-1][canonical_pair])

        labels = [p.name for p in people]

        fig, (ax1) = plt.subplots(1,1,figsize=(10,10))
        ax1.set_title('Pair Frequency: Modeled to Finish \ Through Ride %d' % (ride + 1))
        ax1.set_xticks(np.arange(0, len(people), 1.0), labels=labels, minor=True, rotation=90, fontsize='small')
        ax1.set_xticks(np.arange(0, len(people), 1.0), labels=labels, minor=False, rotation=90, fontsize='small')
        ax1.set_yticks(np.arange(0, len(people), 1.0), labels=labels, minor=True, fontsize='small')
        ax1.set_yticks(np.arange(0, len(people), 1.0), labels=labels, minor=False, fontsize='small')

        def highlight_cell(x,y, ax=None, **kwargs):
            rect = plt.Rectangle((x-.5, y-.5), 1,1, fill=False, **kwargs)
            ax = ax or plt.gca()
            ax.add_patch(rect)
            return rect

        ax1.matshow(modeled_pair_matrix, vmin=0, vmax=config.NumRides(), cmap=plt.cm.Blues, aspect='equal')
        for i in range(0, len(people)):
            for j in range(0, len(people)):
                c = modeled_pair_matrix[j,i]
                ax1.text(i, j, str(int(c)), va='center', ha='center')
                # Riding together on this ride
                if new_pair_matrix[i][j]:
                    # First time riding together
                    if modeled_pair_matrix[i][j] == 1:
                        highlight_cell(j, i, ax=ax1, color="green", linewidth=2)
                    else:
                        highlight_cell(j, i, ax=ax1, color="red", linewidth=2)

        if ride <= finalized:
            fig.savefig('/tmp/pairings-%d.png' % ride, facecolor='white', transparent=False, bbox_inches='tight')
        else:
            fig.savefig('/tmp/pairings-%d.png' % ride, facecolor='yellow', transparent=False, bbox_inches='tight')

    for i in range(0, config.NumRides()):
        PairFrequencyPlot(config.Finalized(), i)

    with imageio.get_writer('/tmp/pairs.gif', mode='I', fps=2, loop=0) as writer:
        files = ['/tmp/pairings-%d.png' % i for i in range(0, config.NumRides())]
        for filename in files:
            image = imageio.imread(filename)
            writer.append_data(image)
