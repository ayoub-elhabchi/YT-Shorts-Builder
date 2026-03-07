import requests
import json

url = "http://localhost:5000/build"

data = {
    "title": "Georgia's Lost Treasury - 2000 Year Old Computer",
  "full_audio_url": "https://drive.google.com/uc?id=1RXR1hcJ6HsosIZoSWJi-wD4VHV9C1A9u&export=download",
  "scenes": [
    {
      "index": 1,
      "text": "[present][somber]Dr. Elena Martinez stands on the deck of the research vessel.<break time='0.5s'/>She watches the sonar‑lit hull.<break time='0.4s'/>",
      "image_url": "https://drive.google.com/uc?id=18BB4RFla_7xrRBLJYWJCKTJDheuKtfZK&export=download"
    },
    {
      "index": 2,
      "text": "Georgia. 1220. Mongol forces were advancing into the highlands. Archbishop Iovane IV had one window... to hide everything.",
      "image_url": "https://drive.google.com/uc?id=1ax2HAB08TrGSX09PHCFgjOqG1g9ILIuV&export=download"
    },
    {
      "index": 3,
      "text": "<prosody volume='x-soft' rate='slow'>[past][somber]Coordinates 34°12′N 58°23′W were logged in a sealed parchment.<break time='0.8s'/>The recovered logbook described a bronze machine, gears turning without power.<break time='0.7s'/>The object defies known chronology.<break time='0.6s'/></prosody>.",
      "image_url": "https://drive.google.com/uc?id=1kyzIq2J1MZqka5LiHPKW7B_hF-uVi5SB&export=download"
    },
    {
      "index": 4,
      "text": "[present][somber]How could a 2,000‑year‑old computer survive in a wooden ship?<break time='0.5s'/>",
      "image_url": "https://drive.google.com/uc?id=1rRe2CdFeu8UAn8ErIxJNlUpZARrkxpbh&export=download"
    },
    {
      "index": 5,
      "text": "[present][somber]Not everyone sticks around till the end. But you did.<break time='0.5s'/>The hunt continues. Don't fall behind.<break time='0.4s'/>",
      "image_url": "https://drive.google.com/uc?id=1v86tPDMNbE12iJGkznWc6OicWwaW4Te1&export=download"
    },
    {
      "index": 6,
      "text": "[present][somber]The sealed chamber remains, its bronze plates cold.<break time='0.5s'/>Future dives will test the limits of history.<break time='0.6s'/>",
      "image_url": "https://drive.google.com/uc?id=1IlZADJ8YNlRvOioeZeAIc2dk-e7TdJl4&export=download"
    }
    ]
}

headers = {"Content-Type": "application/json"}

print("Sending request...")
response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))