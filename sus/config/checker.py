import requests

def clickup_checker(token):
    API_ENDPOINT = "https://api.clickup.com/api/v2/user"
    return requests.get(API_ENDPOINT, headers={"Authorization": token}).status_code == 200