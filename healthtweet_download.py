import mechanize
import traceback
from sys import stderr
from sys import argv
from sys import exit
from csv import writer as csv_writer
from urllib import quote_plus
import ujson
from datetime import datetime

def _get_healthtweet_data(loc, disease, browser, interval="Day", count_type="raw"):
    # 2014 url
    # url = "http://www.healthtweets.org/servlet/get_trends_plot_data?resolution="+interval+"&count_type="+count_type+"&dayNum=1065&to=08/29/2015&plot0_disease="+disease+"&location_plot0="+loc
    # 2015 url
    prefix = "www"
    url = "http://"+prefix+".healthtweets.org/servlet/get_trends_plot_data?resolution="+interval+"&count_type="+count_type+"&dayNum=1371&from=11/27/2011&to=08/29/2015&plot0_disease="+str(disease)+"&location_plot0="+quote_plus(str(loc))
    print >> stderr, "getting "+url
    try:
        r = browser.open(url)
        resp = r.get_data()
        return ujson.loads(resp)
    except (mechanize.HTTPError, mechanize.URLError):
        traceback.print_exc(file=stderr)
        print >> stderr, "\nurl: %s\n" % url
        return None


def _get_parse_healthtweet_data(location_ht_id, disease_id, browser_obj):
    json_obj = _get_healthtweet_data(location_ht_id, disease_id, browser_obj)
    if json_obj is None:
        print >> stderr, "error!  loc id: %s got error when getting data for disease %d" % (location_ht_id, disease_id)
        return []
    dates = []
    data_list = []
    for i in sorted(json_obj['chart_data'], key=lambda x: datetime.strptime(x[0], u"%m/%d/%Y")):
        date = i[0]
        data = int(i[1])
        if data:  # only sum and track weeks with nonzero data
            date_parsed = datetime.strptime(date, u"%m/%d/%Y")
            dates.append(date_parsed)
            data_list.append(data)
    assert len(dates) == len(data_list)
    if not data_list:
        print >> stderr, "error!  loc id: %s has no data for disease %d" % (location_ht_id, disease_id)
        return []
    return zip(dates, data_list)

if __name__ == "__main__":
    loc_id = 2645
    disease_id = -1
    if len(argv) > 1:
        loc_id = int(argv[1])
        if len(argv) > 2:
            disease_id = int(argv[2])
    print >> stderr, "downloading from healthtweets loc id:%s disease id:%s" % (loc_id, disease_id)

    # login to site
    login_url = "http://www.healthtweets.org/accounts/login/?next=/"
    #dev_login_url = "http://dev.healthtweets.org/accounts/login/?next=/"
    user = "msmith"
    pw = "ew2$zu1hRFUX*wxO"

    br = mechanize.Browser()
    br.open(login_url)
    br.select_form(nr = 0) # check
    br.form['username'] = user
    br.form['password'] = pw
    br.submit()
    l = sorted(_get_parse_healthtweet_data(loc_id, disease_id, br), key=lambda x: x[0])
    if not l:
        exit()
    with open("tweets_loc_%s_disease_%s_ht.csv" % (loc_id, disease_id), "wb") as f:
        w = csv_writer(f)
        w.writerow(["Date", "Data"])
        for date, data in l:
            w.writerow([date.strftime("%Y-%m-%d"), data])

