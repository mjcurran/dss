import requests
import random
import json
import datetime
import os
import sys
import uuid
import time

def main(base_url):

    #sp_url = "http://10.83.0.4:8000/sp/inject" # address in emulation.py CORE session
    sp_url = "http://" + base_url + ":8000/sp/inject"

    dir_path = os.path.dirname(os.path.realpath(__file__))
    flight_idx = str(random.randint(1, 6))
    json_data = {}
    with open(dir_path + "/aircraft_states/flight_" + flight_idx + "_rid_aircraft_state.json", 'r') as f:
        json_data = json.load(f)

    #for state in json_data["states"]:
    #    print(state)
    flight_details = json_data["flight_details"]
    rid_details = flight_details["rid_details"]
    #print(rid_details)

    index = 0
    telemetry = []
    for state in json_data["states"]:
        telemetry.append(state)
        index += 1
        if index > 2:
            req_flights = {}
            req_flights["requested_flights"] = []
            injection = {}
            injection["injection_id"] = str(uuid.uuid4())
            injection["telemetry"] = telemetry
            injection["details_responses"] = []
            
            details = {"details": rid_details}
            injection["details_responses"].append(details)
            req_flights["requested_flights"].append(injection)
            #print(req_flights)
            response = requests.put(sp_url, json=req_flights)
            print(response)
            index = 0
            telemetry = []
            time.sleep(1)

if __name__ in ["__main__", "__builtin__"]:
    url = sys.argv[1]
    main(url)