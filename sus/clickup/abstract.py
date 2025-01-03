from __future__ import annotations

import json
import requests
import os
from sus.config import config_handler

API_ENDPOINT = "https://api.clickup.com/api/v2/"
API_TOKEN = None

@config_handler.after_load
def __load_config():
    global API_TOKEN
    API_TOKEN = config_handler.get_configuration("clickup.token")

def call_method(method: str, params: dict = {}):
    r = requests.get(os.path.join(API_ENDPOINT, method), params=params, headers={"Authorization": API_TOKEN})
    if not r.ok:
        r.raise_for_status()
    return r
    

class ClickupTaskStatus:
    def __init__(self, data):
        self.id: str = data["id"]
        self.name: str = data["status"]
        self.type: str = data["type"]
        self.orderindex: int = int(data["orderindex"])
        self.color: str = data["color"]

class ClickupTask:
    def __init__(self, data):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.tags: list[str] = [tag["name"] for tag in data["tags"]]
        self.text_content: str = data["text_content"]
        self.status: ClickupTaskStatus = ClickupTaskStatus(data["status"])
        # We all divide by 1000 to match with Python's UNIX time format
        self.date_created: float = int(data["date_created"]) / 1000
        self.date_updated: float = int(data["date_updated"]) / 1000
        self.due_date: float | None = int(data["due_date"]) / 1000 if data["due_date"] else None
        self.parent: int | None = data["parent"]
        self.url: str = data["url"]
        self.list: ClickupList = ClickupList(data["list"], defer=True) 
        self.subtask: list[ClickupTask] = []

    def add_child(self, task: ClickupTask):
        self.subtask.append(task)

class ClickupList:
    def __init__(self, data, defer=False):
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.tasks: list[ClickupTask] = []
        self.expanded_tasks: list[ClickupTask] = []
        if not defer:
            self.update()

    def update(self):
        task_data = {}

        # It is better to reconstruct all tasks at this point, since tasks tend to come in large numbers
        # Using the API call we can save many calls (as internet is probably the bottleneck)
        self.expanded_tasks = []
        page = 0
        while True:
            task_data = call_method(os.path.join("list", str(self.id), "task"),
                                     {"page": str(page), "order_by": "due_date", "subtasks": "true"}).json()
            self.expanded_tasks += [ClickupTask(ele) for ele in task_data["tasks"]]
            if task_data["last_page"]:
                break
        self.tasks = [task for task in self.expanded_tasks if task.parent is None]
        task_map = {task.id: task for task in self.tasks}
        for task in self.expanded_tasks:
            if task.parent:
                task_map[task.parent].add_child(task)
        

class ClickupSpace:
    def __init__(self, data, defer=False):
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.lists: list[ClickupList] = []
        # TODO: considering whether to add back this, since it is unhelpful
        # self.status_list: list[ClickupTaskStatus] = [ClickupTaskStatus(status) for status in data["statuses"]]

        if not defer:
            self.update()

    def __eq__(self, rhs: ClickupSpace):
        assert isinstance(rhs, ClickupSpace)
        return self.id == rhs.id


    def update(self):
        list_data = call_method(os.path.join("space", str(self.id), "list")).json()

        fetched_lists: list[ClickupList] = [ClickupList(ele, True) for ele in list_data["lists"]]
        for fetched_list in fetched_lists:
            if fetched_list not in self.lists:
                self.lists.append(fetched_list)
        for list in self.lists:
            list.update()

class ClickupTeam:
    def __init__(self, data, defer=False):
        """
        Initialize a ClickUp team with the data.
        `data` must contain the field id and name.

        @params defer: Whether the data fetching is deferred.
        """
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.spaces: list[ClickupSpace] = []
        if not defer:
            self.update()

    def __eq__(self, rhs: ClickupTeam):
        assert isinstance(rhs, ClickupTeam)
        return self.id == rhs.id

    def update(self):
        space_data = call_method(os.path.join("team", str(self.id), "space")).json()
        fetched_spaces = [ClickupSpace(ele, True) for ele in space_data["spaces"]]
        for fetched_space in fetched_spaces:
            if fetched_space not in self.spaces:
                self.spaces.append(fetched_space)

        for space in self.spaces:
            space.update()

class ClickupData:
    def __init__(self, defer=False):
        """
        Initialize all ClickUp data with the token.

        @params defer: Whether the data fetching is deferred.
        """
        self.teams: list[ClickupTeam] = []
        if not defer:
            self.update()

    def get_tasks(self) -> list[ClickupTask]:
        return [task for team in self.teams for space in team.spaces for list in space.lists for task in list.tasks]
    
    def get_expanded_tasks(self) -> list[ClickupTask]:
        return [task for team in self.teams for space in team.spaces for list in space.lists for task in list.expanded_tasks]
    
    def update(self):
        team_data = call_method("team").json()
        fetched_teams = [ClickupTeam(ele, True) for ele in team_data["teams"]]
        for fetched_team in fetched_teams:
            if fetched_team not in self.teams:
                self.teams.append(fetched_team)
        self.tasks = []
        for team in self.teams:
            team.update()
        

                    