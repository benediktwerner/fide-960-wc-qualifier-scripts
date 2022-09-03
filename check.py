#! /usr/bin/env python3

import requests
import json
import time
import os
import subprocess
import itertools
from datetime import datetime


NB = 1000  # increase if error given
NUM_QUALIFY = 500

EVENTS_FILE = "events2.ndjson"
EVENTS_CREATOR = "konstantinos07"

NAME_MAP = {
    "FIDE CCC & NACCL World Fischer Random": "CCC & NACCL",
    "FIDE Offerspill World Fischer Random": "Offerspill",
}

os.makedirs("events", exist_ok=True)

if not os.path.isfile(EVENTS_FILE):
    print("Downloading fide events list")
    with open(EVENTS_FILE, "w") as f:
        for line in requests.get(
            f"https://lichess.org/api/user/{EVENTS_CREATOR}/tournament/created", stream=True
        ).iter_lines():
            line = line.decode("utf-8").strip()
            e = json.loads(line)
            if "World Fischer Random" not in e["fullName"]:
                continue
            print(line, file=f)
    time.sleep(2)

with open(EVENTS_FILE, "r") as f:
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
warn_rus = set()
warn_banned = set()
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

print("Checking top rankers")

for event in completed_events:
    players = [p for p in get_top_rankers(event) if p["username"] not in qualified_players]
    # load_profile_info(players)

    print()
    print(
        f"#### [{event['fullName']} — {datetime.utcfromtimestamp(event['startsAt'] // 1000):%d. %B %H:00}](https://lichess.org/tournament/{event['id']})"
    )

    added = 0
    for p in players:
        qualified_players.add(p["username"])
        added += 1
        print(f"{added}. {p['username']}")
        if added == NUM_QUALIFY:
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


print("Checking flags and bans")

for chunk in chunked_iterable(qualified_players, 300):
    profiles = requests.post("https://lichess.org/api/users", data=",".join(chunk))
    for player in profiles.json():
        if player.get("profile", {}).get("country") in ("RU", "BY"):
            warn_rus.add(player["username"])
        if player.get("disabled", False) or player.get("tosViolation", False):
            warn_banned.add(player["username"])
    time.sleep(2)

print()
print("The following players should be warned about RU/BY flags:")
for p in sorted(warn_rus, key=str.lower):
    print(p)

print()
print("The following players are closed or banned:")
for p in sorted(warn_banned, key=str.lower):
    print(p)
