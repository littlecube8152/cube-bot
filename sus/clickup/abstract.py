from __future__ import annotations

import json
import requests
import os
from sus.config import config_handler

API_ENDPOINT = "https://api.clickup.com/api/v2/"
API_TOKEN = None

# TODO: handle deletion of all objects
# It is not very useful under the context of this bot, but it is nice to have it for completeness


@config_handler.after_load
def __load_config():
    global API_TOKEN
    API_TOKEN = config_handler.get_configuration("clickup.token")


def call_method(method: str, params: dict = {}):
    r = requests.get(os.path.join(API_ENDPOINT, method),
                     params=params, headers={"Authorization": API_TOKEN})
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
        self.parent_task: ClickupTask | None = None
        self.url: str = data["url"]
        # self.list: ClickupList = ClickupList(data["list"], , defer=True)
        self.subtask: list[ClickupTask] = []

    def add_child(self, task: ClickupTask):
        self.subtask.append(task)


class ClickupList:
    def __init__(self, data, user_id, defer=False):
        self.id: int = int(data["id"])
        self.user_id: int = user_id
        self.name: str = data["name"]
        self.tasks: list[ClickupTask] = []
        self.expanded_tasks: list[ClickupTask] = []
        self.status_list: list[ClickupTaskStatus] = []
        if not defer:
            self.update()

    def update(self):
        list_data = call_method(os.path.join("list", str(self.id))).json()
        self.name = list_data["name"]
        self.status_list = [ClickupTaskStatus(status) for status in list_data["statuses"]]

        # It is better to reconstruct all tasks at this point, since tasks tend to come in large numbers
        # Using the API call we can save many calls (as internet is probably the bottleneck)
        self.expanded_tasks = []
        page = 0
        while True:
            task_data = (call_method(os.path.join("list", str(self.id), "task"),
                                     {"page": page, 
                                      "order_by": "due_date", 
                                      "subtasks": True,
                                      "assignees": [self.user_id, self.user_id], # force it to be an array
                                      "statuses": [status.name for status in self.status_list if status.type not in ["done", "closed"]]})
                         .json())
            self.expanded_tasks += [ClickupTask(ele) for ele in task_data["tasks"]]
            if task_data["last_page"]:
                break
        self.tasks = [task for task in self.expanded_tasks if task.parent is None]
        task_map = {task.id: task for task in self.expanded_tasks}
        for task in self.expanded_tasks:
            if task.parent:
                try:
                    task.parent_task = task_map[task.parent]
                    task.parent_task.add_child(task)
                except KeyError:
                    print(f"Task {task} has unaccessible parent {task.parent}")
                    pass


class ClickupSpace:
    def __init__(self, data, user_id, defer=False):
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.user_id: int = user_id
        self.lists: list[ClickupList] = []

        if not defer:
            self.update()

    def __eq__(self, rhs: ClickupSpace):
        assert isinstance(rhs, ClickupSpace)
        return self.id == rhs.id

    def update(self):
        list_data = call_method(os.path.join("space", str(self.id), "list")).json()

        self.lists: list[ClickupList] = [ClickupList(ele, self.user_id, True) for ele in list_data["lists"]]
        
        for list in self.lists:
            list.update()


class ClickupTeam:
    def __init__(self, data, user_id, defer=False):
        """
        Initialize a ClickUp team with the data.
        `data` must contain the field id and name.

        @params defer: Whether the data fetching is deferred.
        """
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.user_id: int = user_id
        self.spaces: list[ClickupSpace] = []
        if not defer:
            self.update()

    def __eq__(self, rhs: ClickupTeam):
        assert isinstance(rhs, ClickupTeam)
        return self.id == rhs.id

    def update(self):
        space_data = call_method(os.path.join("team", str(self.id), "space")).json()
        self.spaces = [ClickupSpace(ele, self.user_id, True) for ele in space_data["spaces"]]

        for space in self.spaces:
            space.update()


class ClickupData:
    def __init__(self, defer=False):
        """
        Initialize all ClickUp data with the token.

        @params defer: Whether the data fetching is deferred.
        """
        self.teams: list[ClickupTeam] = []
        self.user_id: int
        if not defer:
            self.update()

    def get_tasks(self) -> list[ClickupTask]:
        return [task for team in self.teams for space in team.spaces for list in space.lists for task in list.tasks]

    def get_expanded_tasks(self, max_child: int) -> list[ClickupTask]:
        return sum([[task] + task.subtask[:max_child]
                    for team in self.teams
                    for space in team.spaces
                    for list in space.lists
                    for task in list.tasks],
                   [])

    def update(self):
        user_data = call_method("user").json()
        self.user_id = user_data["user"]["id"]
        team_data = call_method("team").json()
        self.teams = [ClickupTeam(ele, self.user_id, True) for ele in team_data["teams"]]
        for team in self.teams:
            team.update()
