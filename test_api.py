import requests
import json

url = "http://localhost:5000/build"

data = {
    "title": "Test Video",
    "scenes": [
        {   "index"    : 1,
            "image_url": "https://drive.google.com/uc?id=1RFSUSiGCS_uoDD-bN3LE4gb5koske1WN&export=download",
            "audio_url": "https://drive.google.com/uc?id=1dbvyzVKOiW7IrFBwn6I-wQZJJk3uY3l4&export=download"
        },
        {   "index"    : 2,
            "image_url": "https://drive.google.com/uc?id=13jTGjMwu9qDqdOg7GdFN4FqsbUQfqSfJ&export=download",
            "audio_url": "https://drive.google.com/uc?id=1_B-im20mYlDNDnaLg0t729-zOHRaIUrV&export=download"
        },
        {   "index"    : 3,
            "image_url": "https://drive.google.com/uc?id=1BBPBBAONJW5-70f3nqPrw9fqOij6Vqr4&export=download",
            "audio_url": "https://drive.google.com/uc?id=1jQr-OWjjKM52DCPAUEO59z0Evw6qm01Z&export=download"
        },{   "index"    : 4,
            "image_url": "https://drive.google.com/uc?id=1GLM54mp0O-n5TEoP43LA_gCMm_bUzwra&export=download",
            "audio_url": "https://drive.google.com/uc?id=1Zqg_j77sLneQLkZbpHRDHP0O5-qECE4P&export=download"
        }
    ]
}

headers = {"Content-Type": "application/json"}

print("Sending request...")
response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))