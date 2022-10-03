#!/usr/bin/env python3

import json
import os
import time
from collections import Counter

import chess.pgn
import requests

SWISS_DIR = "swisses"
ARENAS_DIR = "arenas"
TOKEN = None


if os.path.isfile(".env"):
    with open(".env") as f:
        for line in f:
            if line.startswith("TOKEN="):
                TOKEN = line.strip()[len("TOKEN=") :]


def download_swisses():
    os.makedirs(SWISS_DIR, exist_ok=True)

    with open("fide-swisses.ndjson") as f:
        for line in f:
            data = json.loads(line)
            print(data["name"])

            headers = {"Accept": "application/x-ndjson"}
            if TOKEN is not None:
                headers["Authorization"] = f"Bearer {TOKEN}"

            resp = requests.get(f"https://lichess.org/api/swiss/{data['id']}/games", headers=headers)
            resp.raise_for_status()
            with open(f"{SWISS_DIR}/{data['id']}.ndjson", "w") as of:
                of.write(resp.text)


def download_arenas():
    os.makedirs(ARENAS_DIR, exist_ok=True)

    with open("events2.ndjson") as f:
        for line in f:
            data = json.loads(line)
            print(data["fullName"])

            headers = {"Accept": "application/x-ndjson"}
            if TOKEN is not None:
                headers["Authorization"] = f"Bearer {TOKEN}"

            resp = requests.get(f"https://lichess.org/api/tournament/{data['id']}/games", headers=headers)
            resp.raise_for_status()
            with open(f"{ARENAS_DIR}/{data['id']}.ndjson", "w") as of:
                of.write(resp.text)


class Processor:
    def __init__(self):
        self.moves = 0
        self.games = 0
        self.positions = Counter()

    def process_ndjson_dir(self, directory):
        for fname in os.listdir(directory):
            if fname.endswith(".ndjson"):
                with open(f"{directory}/{fname}") as f:
                    for line in f:
                        game = json.loads(line)
                        self.games += 1
                        self.moves += game["moves"].count(" ")
                        self.positions[game["initialFen"]] += 1

    def process_pgn_dir(self, directory):
        for fname in os.listdir(directory):
            if fname.endswith(".pgn"):
                self.process_pgn(f"{directory}/{fname}")

    def process_pgn(self, fname):
        with open(fname) as f:
            print("Processing", fname)
            while game := chess.pgn.read_game(f):
                self.games += 1
                self.moves += sum(1 for _ in game.mainline())
                self.positions[game.headers["FEN"]] += 1

    def process_arenas_slim(self, ndjson_file):
        with open(ndjson_file) as f:
            for line in f:
                data = json.loads(line)
                print("Downloading info for", data["id"])
                resp = requests.get(f"https://lichess.org/api/tournament/{data['id']}")
                resp.raise_for_status()
                tour = resp.json()
                self.games += tour["stats"]["games"]
                self.moves += tour["stats"]["moves"]
                time.sleep(1)

    def print_results(self):
        print("Games:", self.games)
        print("Moves:", self.moves)
        print("Positions:", len(self.positions))
        common = self.positions.most_common()
        print("Min:", common[-1][1])
        print("Max:", common[0][1])
        for pos, occ in common:
            print(occ, pos)


if not os.path.isdir(SWISS_DIR):
    download_swisses()
# if not os.path.isdir(ARENAS_DIR):
#     download_arenas()

p = Processor()
p.process_ndjson_dir(SWISS_DIR)
# p.process_pgn_dir(ARENAS_DIR)
p.process_arenas_slim("events.ndjson")
p.process_arenas_slim("events2.ndjson")
p.process_pgn("offerspill_knockout.pgn")
p.process_pgn("ccc_nacl_knockout.pgn")
p.print_results()
