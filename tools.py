import requests


def httpGet(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        return f"httpGet error: {e}"

def askUser(prompt):
    return input(prompt)
