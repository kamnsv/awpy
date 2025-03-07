import json
import os
import requests
import pytest
import pandas as pd

from awpy.parser import DemoParser
from awpy.analytics.states import generate_game_state


class TestStates:
    """Class to test the state parsing

    Uses https://www.hltv.org/matches/2344822/og-vs-natus-vincere-blast-premier-fall-series-2020
    """

    def setup_class(self):
        """Setup class by instantiating parser"""
        with open("tests/test_data.json") as f:
            self.demo_data = json.load(f)
        self._get_demofile(
            demo_link=self.demo_data["default"]["url"], demo_name="default"
        )
        self.parser = DemoParser(demofile="default.dem", log=True, parse_rate=256)
        self.data = self.parser.parse()

    def teardown_class(self):
        """Set parser to none"""
        self.parser = None
        self.data = None
        files_in_directory = os.listdir()
        filtered_files = [
            file
            for file in files_in_directory
            if file.endswith(".dem") or file.endswith(".json")
        ]
        if len(filtered_files) > 0:
            for f in filtered_files:
                os.remove(f)

    @staticmethod
    def _get_demofile(demo_link, demo_name):
        print("Requesting " + demo_link)
        r = requests.get(demo_link)
        open(demo_name + ".dem", "wb").write(r.content)

    @staticmethod
    def _delete_demofile(demo_name):
        print("Removing " + demo_name)
        os.remove(demo_name + ".dem")

    def test_wrong_frame_input(self):
        """Tests that wrong frame type raises error"""
        frame = "not a dict"
        with pytest.raises(ValueError):
            generate_game_state(frame)

    def test_wrong_state_type(self):
        """Tests that wrong state type raises error"""
        with pytest.raises(ValueError):
            generate_game_state(
                self.data["gameRounds"][0]["frames"][0], state_type="test"
            )

    def test_output(self):
        """Tests that output is a dict with 3 keys"""
        game_state = generate_game_state(self.data["gameRounds"][7]["frames"][0])
        assert type(game_state) == dict
        assert "ct" in game_state.keys()
        assert "t" in game_state.keys()
        assert "global" in game_state.keys()
        assert type(game_state["ct"]) == dict
        assert type(game_state["t"]) == dict
        assert type(game_state["global"]) == dict
