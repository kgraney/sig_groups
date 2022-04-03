from collections import defaultdict

def PrintAvailabilityTable(riders, num_rides):
    s = []
    for r in range(0, num_rides):
        s.append('Ride %d' % (r + 1))
    print(("{: <25} " + "{: <10}"*num_rides).format('', *s))
    for p in riders:
        avails = []
        for r in range(0, num_rides):
            avails.append(p.IsAvailable(r))
        avail_str = ['X' if x else '' for x in avails]
        print(("{: <25} " + "{: <10}"*num_rides).format(p.name, *avail_str))

def PrintRosters(rosters):
    by_ride = defaultdict(lambda: [])
    for r in rosters:
        by_ride[r.ride].append(r)

    for ride, rs in by_ride.items():
        print('\n\nRide %d' % (ride+1))
        rows = max(len(r) for r in rs)
        cols = len(rs)

        matrix = [['' for _ in range(cols)] for _ in range(rows)]

        i = 0
        j = 0
        for r in rs:
            for p in r.riders:
                matrix[j][i] = r.GetRiderStr(j)
                j += 1
            j = 0
            i += 1

        for row in matrix:
            print(("{: <30} "*cols).format(*row))
