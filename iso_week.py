from datetime import datetime
from datetime import timedelta


def week_from_str(dt_str, dt_format_str):
    dt = datetime.strptime(dt_str, dt_format_str)
    return week(dt)

def week(dt):
    '''
    return week number paired with year for a datetime
    '''
    year = dt.year
    month = dt.month
    iso = dt.isocalendar()
    week = iso[1]
    day = iso[2]
    if day == 7: # ISO weeks begin Monday but CDC weeks begin Sunday (day 7), so adjust
        dt += timedelta(days=1)
        iso = dt.isocalendar()
        week = iso[1]
    if week == 1 and month > 1:
        year += 1  # we've spilled into the next year
    return (year, week)

if __name__=="__main__":
    from dateutil import parser as dt_parser
    d = dt_parser.parse("11/27/2011")
    print d
    print week(d)
