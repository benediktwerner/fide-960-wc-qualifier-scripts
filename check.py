#! /usr/bin/env python3

import requests
import json
import time
import os
import subprocess
import itertools
from datetime import datetime


NB = 200  # increase if error given

NAME_MAP = {
    "FIDE CCC & NACCL World Fischer Random": "CCC & NACCL",
    "FIDE Offerspill World Fischer Random": "Offerspill",
}

os.makedirs("events", exist_ok=True)

if not os.path.isfile("events.ndjson"):
    print("Downloading fide events list")
    with open("events.ndjson", "w") as f:
        for line in requests.get("https://lichess.org/api/user/fide/tournament/created", stream=True).iter_lines():
            line = line.decode("utf-8").strip()
            e = json.loads(line)
            if "World Fischer Random" not in e["fullName"]:
                break
            print(line, file=f)
    time.sleep(2)

with open("events.ndjson", "r") as f:
    events = [json.loads(line) for line in f.read().splitlines()]

now = time.time() * 1000
completed_events = [e for e in sorted(events, key=lambda e: e["startsAt"]) if e["finishesAt"] <= now]


def get_top_rankers(event):
    event = event["id"]
    fname = f"events/{event}.ndjson"
    if not os.path.isfile(fname) or int(subprocess.check_output(["wc", "-l", fname]).split()[0]) < NB:
        headers = {
            "Accept": "application/x-ndjson",
        }
        if os.path.isfile("token"):
            with open("token", "r") as f:
                tokendata = f.read()
            headers["Authorization"] = f"Bearer {tokendata}"
        results = requests.get(
            f"https://lichess.org/api/tournament/{event}/results?nb={NB}",
            headers=headers,
        ).text
        with open(fname, "w") as f:
            f.write(results)
        time.sleep(5)
    with open(fname, "r") as f:
        results = [json.loads(line) for line in f.read().splitlines()]
    return results


qualified_players = set()
warn = set()
is_banned = {}

# if os.path.isfile("banned.json"):
#     with open("banned.json") as f:
#         is_banned = json.load(f)


# def load_profile_info(players):
#     players = [p["username"] for p in players if p["username"] not in is_banned]
#     if players:
#         profiles = requests.post("https://lichess.org/api/users", data=",".join(players)).json()
#         for p in profiles:
#             is_banned[p["username"]] = (
#                 p.get("profile", {}).get("country") in ("RU", "BY")
#                 or p.get("disabled", False)
#                 or p.get("tosViolation", False)
#             )

#         with open("banned.json", "w") as f:
#             json.dump(is_banned, f)
#         time.sleep(5)


for event in completed_events:
    players = [
        p
        for p in get_top_rankers(event)
        if ("title" not in p or p["title"] == "LM") and p["username"] not in qualified_players
    ]
    # load_profile_info(players)

    print()
    print(
        f"#### [{NAME_MAP[event['fullName']]} Qualifier — {datetime.utcfromtimestamp(event['startsAt'] // 1000):%d. %B %H:00}](https://lichess.org/tournament/{event['id']})"
    )

    added = 0
    for p in players:
        # if is_banned[p["username"]]:
        #     warn.add(p["username"])
        #     continue
        qualified_players.add(p["username"])
        added += 1
        print(f"{added}. {p['username']}")
        if added == 50:
            break
    else:
        print("Error: Increase NB players pulled in parameter at the top of the file")


def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, size))
        if not chunk:
            break
        yield chunk


for chunk in chunked_iterable(qualified_players, 300):
    profiles = requests.post("https://lichess.org/api/users", data=",".join(chunk))
    for player in profiles.json():
        if player.get("profile", {}).get("country") in ("RU", "BY"):
            warn.add(player["username"])
    time.sleep(2)

print()
print("The following players should be warned about RU/BY flags:")
for p in sorted(warn, key=str.lower):
    print(p)
