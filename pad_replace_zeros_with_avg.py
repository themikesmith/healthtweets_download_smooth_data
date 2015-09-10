
__author__ = 'mcs'

import sys
from iso_week import week
from dateutil import parser as dt_parser
from datetime import datetime
from datetime import timedelta
import cPickle as pickle
import bisect
from csv import reader as csv_reader
from csv import writer as csv_writer
from re import sub

one_day = timedelta(days=1)
daily_data = {}  # dt -> (numerator, denominator)
weekly_running_avgs = {}  # (year, week) -> (numerator, denominator, n)

def get_avg_window(dt, sorted_days_list, sorted_data_list, window_size=7):
    """
    Given a date, get the 7 days before and 7 days after for which
    we have data, and average them.
    :param dt: date time in question
    :param sorted_days_list: sorted list of days, pruned of zero day data
    :param sorted_data_list: sorted list of data, pruned of zero day data, corresponding to list of days
    :param window_size: days in one side of window, default 7
    :return: avg of 7 day window around given dt
    """
    # print dt
    # print sorted_days_list
    assert len(sorted_days_list) == len(sorted_data_list)
    dt_index = bisect.bisect(sorted_days_list, dt)
    min_index = dt_index - window_size
    max_index = dt_index + window_size
    # print "index:%d interval:(%d : %d)" % (dt_index, min_index, max_index)
    # print "list boundaries:%d and %d" % (0, len(sorted_days_list))
    if min_index < 0:
        min_index = 0
    if max_index > len(sorted_days_list):
        max_index = len(sorted_days_list)
    # print "now:: index:%d interval:(%d : %d)" % (dt_index, min_index, max_index)
    actual_window_size = min(dt_index - min_index, max_index - dt_index)
    # print "before:%d after:%d actual window size:%d" % (dt_index - min_index, max_index - dt_index, actual_window_size)
    min_index = dt_index - actual_window_size
    max_index = dt_index + actual_window_size
    # print "now:: index:%d interval:(%d : %d)" % (dt_index, min_index, max_index)
    data_slice = sorted_data_list[min_index:max_index]
    # for x in range(min_index, max_index):
    #     print "%s -> %s" % (sorted_days_list[x], data_slice[x-min_index])
    # print data_slice
    if len(data_slice) == 0:
        # print 0
        return 0
    else:
        return float(sum(data_slice)) / float(len(data_slice))


def main():
    # read in gap days
    # load all dates where downtime indicates we need to insert weekly avg
    five_mins = pickle.load(open(sys.argv[1], 'rb'))  # five minute series pandas pickled
    for infilename in sys.argv[2:]:
        daily_data = {}  # dt -> (numerator, denominator)
        weekly_running_avgs = {}  # (year, week) -> (numerator, denominator, n)
        print >> sys.stderr, 'reading from:%s' % infilename
        zero_days = []  # track days with zero tweets
        # read all lines in data file, ignoring data from gap days
        with open(infilename, "rb") as infile:
            r = csv_reader(infile)
            r.next()
            for row in r:
                dt = dt_parser.parse(row[0])
                if dt in daily_data:
                    raise ValueError('dt already in data:%s' % dt)
                daily_data[dt] = float(row[1])
                if daily_data[dt] == 0:
                    #print >> sys.stderr, "zero day found:", dt
                    zero_days.append(dt)
        # assert indicated gap days are a superset of the set of days with 0 data
        zero_days = set(zero_days)
        five_min_days = set(five_mins.index)
        # print 'zero days:', sorted(zero_days)
        # print '5 min days:', sorted(five_min_days)
        # this should be empty, ie, all zero days should have > 5 min of gap
        zero_days_not_in_gap = zero_days - five_min_days
        try:
            assert len(zero_days_not_in_gap) == 0
        except AssertionError as e:
            #print >> sys.stderr, "zero days not in five_min days:", sorted(zero_days_not_in_gap)
            # smooth zero days not accounted for by gap
            days = set(daily_data.keys())
            nonzero_days = sorted(days - zero_days_not_in_gap)
            nonzero_data = [daily_data[dt] for dt in nonzero_days]
            for dt in zero_days_not_in_gap:
                #print >> sys.stderr, "smoothing zero day not in gap:", dt
                daily_data[dt] = get_avg_window(dt, nonzero_days, nonzero_data)
        # this could be nonempty, as we could have data on days where we had five minutes of gap
        # print >> sys.stderr, "five_min days not in zero days:"
        # diff_two = five_min_days - zero_days
        # print >> sys.stderr, len(diff_two)
        # prune gap days from data
        for day in sorted(five_min_days):
            #print >> sys.stderr, "setting five min day zero:", day
            daily_data[day] = 0
        # keep running avg for each iso week; denominator is 7 - gap days
        prev_day = None
        for day in sorted(daily_data):
            if prev_day is not None:
                if day - prev_day > one_day:
                    #print >> sys.stderr, 'gap larger than one day: %s to %s' % (prev_day, day)
                    curr = prev_day
                    while curr < day:
                        #print >> sys.stderr, 'inserting zero for %s' % curr
                        daily_data[curr] = 0
                        curr = curr + one_day
            #print >> sys.stderr, "on day:", day
            prev_day = day
            day_data = daily_data[day]
            w = week(day)
            if w not in weekly_running_avgs:
                weekly_running_avgs[w] = 0.0, 0.0
            if day_data == 0:
                continue  # skip gap days
            old_data, n = weekly_running_avgs[w]
            new_data = (old_data * n + day_data) / (n + 1)
            weekly_running_avgs[w] = new_data, (n+1)
        # for each gap day, swap in respective weekly avg
        # for day in five_min_days:
        for day in sorted(daily_data):
            day_data = daily_data[day]
            if day_data == 0:
                w = week(day)
                if w not in weekly_running_avgs:
                    weekly_running_avgs[w] = 0.0, 0.0
                #print >> sys.stderr, "padding day:%s" % day
                d, n = weekly_running_avgs[w]
                daily_data[day] = d
        # and print
        with open(sub(r"_pad\.csv", "_avg.csv", infilename), 'wb') as out:
            print >> sys.stderr, 'writing to %s' % out.name
            w = csv_writer(out)
            w.writerow(["Date","Avg data"])
            for day in sorted(daily_data):
                day_data = daily_data[day]
                w.writerow([day.strftime("%Y-%m-%d"), day_data])

if __name__ == '__main__':
    main()
    # # b is all days
    # # c is all data
    # # d is all dates, with zeros removed
    # # e is all data, with zeros removed
    # today = datetime.today().date()
    # b = [today + timedelta(days=x) for x in range(40)]
    # c = range(1, 41)
    # d = [today + timedelta(days=x) for x in range(40)]
    # e = range(1, 41)
    # assert len(c) == len(b)
    # to_zero = [0,4,5,6,7,13,16,len(e)-6, len(e)-1]
    # for zero_index in to_zero:
    #     temp_day = b[zero_index]
    #     temp_data = c[zero_index]
    #     d.remove(temp_day)
    #     e.remove(temp_data)
    #     c[zero_index] = 0
    # for i, x in enumerate(b):
    #     print "%s -> %d" % (x, c[i])
    # print ""
    # for i, x in enumerate(d):
    #     print "%s -> %d" % (x, e[i])
    # for i, x in enumerate(c):
    #     if x == 0:
    #         get_avg_window(b[i], d, e)
