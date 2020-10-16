import json


class Debug_JSON():

    def __init__(self, settings, origserv, epghandling):
        self.config = settings
        self.origserv = origserv

    def get_debug_json(self, base_url, tuners):
        debugjson = {
                    "base_url": base_url,
                    "total channels": self.origserv.get_station_total(),
                    "tuner status": tuners.status(),
                    }
        return json.dumps(debugjson, indent=4)
