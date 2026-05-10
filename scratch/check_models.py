import urllib.request
import json

api_key = ""
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        models = data.get("models", [])
        for m in models:
            print(m.get("name"))
except Exception as e:
    print(f"Error: {e}")
