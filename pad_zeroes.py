import sys
from datetime import datetime, timedelta
from dateutil import parser as dt_parser
from csv import writer as csv_writer
from csv import reader as csv_reader
from re import sub

def _get_dt_str(dt):
    return dt.strftime("%Y-%m-%d")

def main():
    for infilename in sys.argv[1:]:
        outfilename = sub("\.csv", "_pad.csv", infilename)
        prev_dt = -1
        week = timedelta(days=7)
        one = timedelta(days=1)
        with open(outfilename, "wb") as outfile:
            w = csv_writer(outfile)
            with open(infilename, "rb") as infile:
                r = csv_reader(infile)
                header = r.next()
                w.writerow(header)
                for row in r:
                    dt = dt_parser.parse(row[0])
                    if prev_dt != -1:
                        # we're past the first line... compare!
                        diff = dt - prev_dt
                        if diff > one:
                            for i in reversed(range(diff.days - 1)):
                                wahoo = timedelta(days=(i+1))
                                pad = dt - wahoo
                                #print >> sys.stderr, "padding:%s" % pad
                                w.writerow([_get_dt_str(pad), 0])
                    w.writerow([_get_dt_str(dt), row[1]])
                    prev_dt = dt

if __name__ == "__main__":
    main()
