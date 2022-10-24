import requests
import random
import json
import datetime
import os
import sys
import uuid
import time

def main(base_url):
    dp_url = "http://" + base_url + ":8001/dp/subscribe"

    dir_path = os.path.dirname(os.path.realpath(__file__))
    flight_idx = str(random.randint(1, 6))
    json_data = {}
    with open(dir_path + "/query_bboxes/box_too_large_query.geojson", 'r') as f:
        json_data = json.load(f)

    subscription = {}
    vertices = []
    geometry = json_data["geometry"]
    properties = json_data["properties"]
    time_before = properties["timestamp_before"]
    time_after = properties["timestamp_after"]
    
    coords = geometry["coordinates"][0]
    #print(coords)
    footprint = {}
    for c in coords:
        v = {"lng": c[1], "lat": c[0]}
        vertices.append(v)

    footprint["vertices"] = vertices
    spatial_volume = {"footprint": footprint, "altitude_lo": 0, "altitude_hi": 12000}
    extents = {"spatial_volume": spatial_volume, "time_start": time_after, "time_end": time_before}
    subscription["extents"] = extents
    print(subscription)

    response = requests.put(dp_url, json=subscription)


if __name__ in ["__main__", "__builtin__"]:
    url = sys.argv[1]
    main(url)