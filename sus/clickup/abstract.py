from __future__ import annotations
import os
import requests
from sus.config import config_handler

API_ENDPOINT = "https://api.clickup.com/api/v2/"
API_TOKEN = None
@config_handler.after_load
def __load_config():
    global API_TOKEN
    API_TOKEN = config_handler.get_configuration("clickup.token")

def call_method(method: str, headers: dict = {}):
    headers["Authorization"] = API_TOKEN
    return requests.get(os.path.join(API_ENDPOINT, method), headers=headers)

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
        self.text_content: str = data["text_content"]
        self.status: ClickupTaskStatus = ClickupTaskStatus(data["status"])
        # We all divide by 1000 to match with Python's UNIX time format
        self.date_created: float = int(data["date_created"]) / 1000
        self.date_updated: float = int(data["date_updated"]) / 1000
        self.due_date: float | None = int(data["due_date"]) / 1000 if data["due_date"] else None
        self.url: str = data["url"]
        self.list: ClickupList = ClickupList(data["list"], False)

class ClickupList:
    def __init__(self, data, recurse = True):
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        if recurse:
            self.update_subclass()

    def update_subclass(self):
        task_data = {}
        self.tasks: list[ClickupTask] = []
        page = 0
        while True:
            task_data = call_method(os.path.join("list", str(self.id), "task"),
                                     {"page": str(page), "order_by": "due_date"}).json()
            self.tasks += [ClickupTask(ele) for ele in task_data["tasks"]]
            if task_data["last_page"]:
                break

class ClickupSpace:
    def __init__(self, data):
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.status_list: list[ClickupTaskStatus] = [ClickupTaskStatus(status) for status in data["statuses"]]
        self.update_subclass()

    def update_subclass(self):
        list_data = call_method(os.path.join("space", str(self.id), "list")).json()
        self.lists: list[ClickupList] = [ClickupList(ele) for ele in list_data["lists"]]

class ClickupTeam:
    def __init__(self, data):
        self.id: int = int(data["id"])
        self.name: str = data["name"]
        self.update_subclass()

    def update_subclass(self):
        space_data = call_method(os.path.join("team", str(self.id), "space")).json()
        self.spaces: list[ClickupSpace] = [ClickupSpace(ele) for ele in space_data["spaces"]]

class ClickupData:
    def __init__(self):
        team_data = call_method("team").json()
        self.teams: list[ClickupTeam] = [ClickupTeam(ele) for ele in team_data["teams"]]

    def get_all_tasks(self) -> list[ClickupTask]:
        tasks: list[ClickupTask] = []
        for team in self.teams:
            for space in team.spaces:
                for list in space.lists:
                    tasks += list.tasks
        return tasks
                    