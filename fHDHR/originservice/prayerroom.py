import os
import datetime
import tabula
import pytz
import calendar
import pathlib
import urllib.request

import fHDHR.tools


class FixedOffset(datetime.tzinfo):
    """Fixed UTC offset: `local = utc + offset`."""

    def __init__(self, offset, name):
        self.__offset = datetime.timedelta(hours=offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return datetime.timedelta(0)


def convert24(str1):
    str1_num = "{:02d}".format(int(str1.replace("am", "").replace("pm", "")))
    if "am" in str1:
        str1_end = "AM"
    elif "pm" in str1:
        str1_end = "PM"
    str1 = str(str1_num) + str1_end

    # Checking if last two elements of time
    # is AM and first two elements are 12
    if str1[-2:] == "AM" and str1[:2] == "12":
        return "00" + str1[2:-2]

    # remove the AM
    elif str1[-2:] == "AM":
        return str1[:-2]

    # Checking if last two elements of time
    # is PM and first two elements are 12
    elif str1[-2:] == "PM" and str1[:2] == "12":
        return str1[:-2]

    else:

        # add 12 to hours and remove PM
        return (str(int(str1[:2]) + 12) + str1[2:8]).replace("PM", "")


class fHDHRservice():
    def __init__(self, settings):
        self.config = settings

        self.web = fHDHR.tools.WebReq()
        self.web_cache_dir = self.config.dict["filedir"]["epg_cache"]["origin"]["web_cache"]
        self.pdf_sched = pathlib.Path(self.web_cache_dir).joinpath('sched.pdf')

        self.pdf_sched_url = ("https://s3.amazonaws.com/"
                              "ihopkc.org-prod-site/wp-content/uploads/"
                              "sites/108/2020/09/01171428/"
                              "24-Hours-Schedule-A-8-24-2020.pdf")

    def login(self):
        return True

    def get_channels(self):
        channel_list = [{
                             "name": "IHOP KC PrayerRoom",
                             "callsign": "prayerroom",
                             "number": "1",
                             "id": "prayerroom",
                             }]
        return channel_list

    def get_channel_stream(self, chandict, allchandict):
        caching = True
        streamlist = []
        streamdict = {}
        video_url = "https://storage.sardius.media/archives/-K6FGrVYzVr92SDZiDnc/events/site_68FBe1c2dE/video_0.m3u8"
        audio_url = "https://storage.sardius.media/archives/-K6FGrVYzVr92SDZiDnc/events/site_68FBe1c2dE/audio_0_eng.m3u8"
        streamurl = [video_url, audio_url]
        streamurl = video_url
        streamdict = {"number": chandict["number"], "stream_url": streamurl}
        streamlist.append(streamdict)

        return streamlist, caching

    def update_epg(self):
        clean_sched_dict = self.pull_pdf_epg_data()

        programguide = {}

        events_list = []

        # convert KC time to UTC
        kctime = pytz.timezone("America/Chicago")
        today_naive = datetime.datetime.strptime(str(datetime.date.today()) + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        kc_dt = kctime.localize(today_naive)
        for x in range(0, 6):
            xdate = kc_dt + datetime.timedelta(days=x)
            dayofweek = calendar.day_name[xdate.weekday()]
            xtdate = xdate + datetime.timedelta(days=1)

            for event in clean_sched_dict[dayofweek]:
                time_start = xdate.replace(hour=event["start_hour"])
                if event["end_hour"] == 0:
                    time_end = xtdate.replace(hour=event["end_hour"])
                else:
                    time_end = xdate.replace(hour=event["end_hour"])
                duration_minutes = (time_end - time_start).total_seconds() / 60
                print(time_start)
                time_start = time_start.astimezone(pytz.utc)
                print(time_start)
                time_end = time_end.astimezone(pytz.utc)
                curreventdict = {
                                "time_start": str(time_start.strftime('%Y%m%d%H%M%S')) + " +0000",
                                "time_end": str(time_end.strftime('%Y%m%d%H%M%S')) + " +0000",
                                "duration_minutes": duration_minutes,
                                "title": event["title"],
                                "assignments": event["assignments"],
                                "start_kc_time": event["start_kc_time"],
                                }
                events_list.append(curreventdict)

        for c in self.get_channels():

            if str(c["number"]) not in list(programguide.keys()):
                programguide[str(c["number"])] = {
                                                    "callsign": c["callsign"],
                                                    "name": c["name"],
                                                    "number": c["number"],
                                                    "id": c["id"],
                                                    "thumbnail": "https://yt3.ggpht.com/a/AATXAJyF27VVvcRYjnggXVY8NVwND68nWqzpXj5zaB2tUg=s176-c-k-c0x00ffffff-no-rj-mo",
                                                    "listing": [],
                                                    }

            for event in events_list:
                description = "Kansas City Time: " + event["start_kc_time"]
                assignment_reference = {
                                        "WL": "Worship Leader",
                                        "A": "Associate WL",
                                        "PL": "Prayer Leader",
                                        "SL": "Section Leader",
                                        }
                for assignment in list(event['assignments']):
                    assignment_title = assignment_reference[assignment]
                    assignment_person = event['assignments'][assignment]
                    description += str(", " + assignment_title + ": " + assignment_person)

                clean_prog_dict = {
                                    "time_start": event['time_start'],
                                    "time_end": event['time_end'],
                                    "duration_minutes": event['duration_minutes'],
                                    "thumbnail": "https://i.ytimg.com/vi/Faz6jkFTaa0/maxresdefault.jpg",
                                    "title": event['title'],
                                    "sub-title": event["start_kc_time"] + " Kansas City Time",
                                    "description": description,
                                    "rating": "N/A",
                                    "episodetitle": None,
                                    "releaseyear": None,
                                    "genres": [],
                                    "seasonnumber": None,
                                    "episodenumber": None,
                                    "isnew": False,
                                    "id": str(event['time_start']),
                                    }

                programguide[str(c["number"])]["listing"].append(clean_prog_dict)

        return programguide

    def download_pdf_epg(self):

        why_download = None

        if not os.path.exists(self.pdf_sched):
            why_download = "PDF cache missing."
        else:

            print("Checking online PDF for updates.")

            offline_file_time = self.get_offline_file_time()
            online_file_time = self.get_online_file_time()

            if not offline_file_time <= online_file_time:
                print("Cached PDF is current.")
            else:
                why_download = "Online PDF is newer."

        if why_download:
            self.clear_database_cache()
            print(why_download + ' Downloading the latest PDF...')
            urllib.request.urlretrieve(self.pdf_sched_url, self.pdf_sched)

    def scrape_pdf(self):

        # Pull blocks of table content into a list
        tablelist = []
        epgjson = tabula.read_pdf(self.pdf_sched, pages='1', output_format="json")
        for top_level_item in epgjson:
            for second_level_item in top_level_item['data']:
                for third_level_item in second_level_item:
                    if (third_level_item['top'] != 0.0
                       and third_level_item['left'] != 0.0
                       and third_level_item['width'] != 0.0
                       and third_level_item['height'] != 0.0
                       and third_level_item['text'] != ''):
                        if '\r' in third_level_item['text']:
                            block_list = third_level_item["text"].split('\r')
                            tablelist.append(block_list)

        # Read data left to right into a dict
        daysofweek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        current_time = None
        current_day_index = 0
        schedule_dict = {}
        for block_list in tablelist:
            if block_list[0][-2:] in ["am", "pm"] and block_list[0][:-2].isdigit():
                current_time = block_list[0]
                if current_time not in list(schedule_dict.keys()):
                    schedule_dict[current_time] = {}
                schedule_dict[current_time]["start"] = block_list[0]
                schedule_dict[current_time]["title"] = " ".join(block_list[1:])
            elif ('WL' in block_list
                  or 'A' in block_list
                  or 'PL' in block_list
                  or 'SL' in block_list):
                schedule_dict[current_time]["assignments"] = block_list
            else:
                current_day = daysofweek[current_day_index]
                schedule_dict[current_time][current_day] = block_list
                if current_day_index == 6:
                    current_day_index = 0
                    current_time = None
                else:
                    current_day_index += 1

        # additional pages of this document read differently
        # should only be a single other page
        tablelisttwo = []
        epgjson = tabula.read_pdf(self.pdf_sched, multiple_tables=True, pages='2', output_format="json")
        for top_level_item in epgjson:
            for second_level_item in top_level_item['data']:
                for third_level_item in second_level_item:
                    if (third_level_item['top'] != 0.0
                       and third_level_item['left'] != 0.0
                       and third_level_item['width'] != 0.0
                       and third_level_item['height'] != 0.0
                       and third_level_item['text'] != ''):
                        tablelisttwo.append(third_level_item['text'])

        current_time = None
        current_day_index = 0
        for table_item in list(tablelisttwo):
            if table_item[-2:] in ["am", "pm"] and table_item[:-2].isdigit():
                current_time = table_item
                if table_item not in list(schedule_dict.keys()):
                    schedule_dict[current_time] = {}
                schedule_dict[current_time]["start"] = table_item
            elif ('WL' in table_item
                  or 'A' in table_item
                  or 'PL' in table_item
                  or 'SL' in table_item):
                if "assignments" not in list(schedule_dict[current_time].keys()):
                    schedule_dict[current_time]["assignments"] = []
                schedule_dict[current_time]["assignments"].append(table_item)
            elif (table_item == "Intercession"
                  or table_item == "Worship with"
                  or table_item == "the Word"):
                if "title" not in schedule_dict[current_time].keys():
                    schedule_dict[current_time]["title"] = ''
                if schedule_dict[current_time]["title"] == '':
                    schedule_dict[current_time]["title"] += table_item
                else:
                    schedule_dict[current_time]["title"] += (" " + table_item)
            else:
                current_day = daysofweek[current_day_index]
                if current_day not in list(schedule_dict[current_time].keys()):
                    schedule_dict[current_time][current_day] = []

                schedule_dict[current_time][current_day].append(table_item)
                if current_day_index == 6:
                    current_day_index = 0
                else:
                    current_day_index += 1

        # Rebuild the dict into a daily schedule
        clean_sched_dict = {}
        for day in daysofweek:
            clean_sched_dict[day] = []
        for sched_item in list(schedule_dict.keys()):
            for day in daysofweek:
                eventdict = {
                            "title": schedule_dict[sched_item]["title"],
                            "start_hour": int(convert24(schedule_dict[sched_item]["start"])),
                            "assignments": {},
                            "day": day,
                            "start_kc_time": schedule_dict[sched_item]["start"],
                            }
                for x, y in zip(schedule_dict[sched_item]["assignments"], schedule_dict[sched_item][day]):
                    eventdict["assignments"][x] = y
                clean_sched_dict[day].append(eventdict)
        # Sort by start and add end times
        for day in daysofweek:
            events_with_end = []
            clean_sched_dict[day] = sorted(clean_sched_dict[day], key=lambda i: i['start_hour'])
            for idx, curr_event in enumerate(clean_sched_dict[day]):
                try:
                    next_event = clean_sched_dict[day][idx + 1]
                except IndexError:
                    next_event = {"start_hour": 0}
                curr_event["end_hour"] = next_event["start_hour"]
                events_with_end.append(curr_event)
            clean_sched_dict[day] = sorted(events_with_end, key=lambda i: i['start_hour'])
        return clean_sched_dict

    def pull_pdf_epg_data(self):
        self.download_pdf_epg()
        return self.scrape_pdf()

    def get_online_file_time(self):
        url_head = urllib.request.Request(self.pdf_sched_url, method='HEAD')
        resp = urllib.request.urlopen(url_head)
        online_file_time = resp.headers['last-modified'].replace(" GMT", "")
        online_file_time = datetime.datetime.strptime(online_file_time, '%a, %d %b %Y %H:%M:%S')
        online_file_time = online_file_time.replace(tzinfo=FixedOffset(-4, "GMT-4")).astimezone(datetime.timezone.utc)
        return online_file_time

    def get_offline_file_time(self):
        offline_file_time = datetime.datetime.utcfromtimestamp(os.path.getmtime(self.pdf_sched))
        offline_file_time = offline_file_time.replace(tzinfo=datetime.timezone.utc)
        return offline_file_time

    def clear_database_cache(self):
        print("Clearing PDF cache.")
        if os.path.exists(self.pdf_sched):
            os.remove(self.pdf_sched)
