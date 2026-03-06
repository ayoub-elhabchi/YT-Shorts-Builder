import requests
import json

url = "http://localhost:5000/build"

data = {
    "title": "Test Video",
    "scenes": [
        {   "index"    : 1,
            "image_url": "https://drive.google.com/uc?id=1KxE1zW3BCSAhikpkRCk5fkVu7fk2DDGr&export=download",
            "audio_url": "https://drive.google.com/uc?id=1mXtLX_SHZjNZxyf_zgxoJZqK1xt7hnpt&export=download"
        },
        {   "index"    : 2,
            "image_url": "https://drive.google.com/uc?id=1gowqXz6vmOkQtUIr3vRINHcZrPcq3FsW&export=download",
            "audio_url": "https://drive.google.com/uc?id=1prY96YKhd2-YIsZC4Osq7VgbSERVE1m4&export=download"
        }
    ]
}

headers = {"Content-Type": "application/json"}

print("Sending request...")
response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))