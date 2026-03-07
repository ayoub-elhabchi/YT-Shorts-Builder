import requests
import json

url = "http://localhost:5000/build"

data = {
    "title": "Georgia's Lost Treasury - 2000 Year Old Computer",
  "full_audio_url": "https://drive.google.com/uc?id=1RXR1hcJ6HsosIZoSWJi-wD4VHV9C1A9u&export=download",
      "subtitles": True,
    "subtitle_style": "word_by_word",
  "scenes": [
    {
      "index": 1,
      "text": "A cargo ship vanished in 1803, swallowed by the Atlantic. Its wreck, sealed for centuries, held a secret.",
      "image_url": "https://drive.google.com/uc?id=18BB4RFla_7xrRBLJYWJCKTJDheuKtfZK&export=download"
    },
    {
      "index": 2,
      "text": "Dr. Elena Martinez stands on the deck of the research vessel.She watches the sonar‑lit hull.",
      "image_url": "https://drive.google.com/uc?id=1ax2HAB08TrGSX09PHCFgjOqG1g9ILIuV&export=download"
    },
    {
      "index": 3,
      "text": "Coordinates 34°12′N 58°23′W were logged in a sealed parchment. The recovered logbook described a bronze machine, gears turning without power. The object defies known chronology.",
      "image_url": "https://drive.google.com/uc?id=1kyzIq2J1MZqka5LiHPKW7B_hF-uVi5SB&export=download"
    },
    {
      "index": 4,
      "text": "How could a 2,000‑year‑old computer survive in a wooden ship?",
      "image_url": "https://drive.google.com/uc?id=1rRe2CdFeu8UAn8ErIxJNlUpZARrkxpbh&export=download"
    },
    {
      "index": 5,
      "text": "Not everyone sticks around till the end. But you did. The hunt continues. Don't fall behind.",
      "image_url": "https://drive.google.com/uc?id=1v86tPDMNbE12iJGkznWc6OicWwaW4Te1&export=download"
    },
    {
      "index": 6,
      "text": "The sealed chamber remains, its bronze plates cold. Future dives will test the limits of history.",
      "image_url": "https://drive.google.com/uc?id=1IlZADJ8YNlRvOioeZeAIc2dk-e7TdJl4&export=download"
    }
    ]
}

# data = {
#     "title": "He Memorized the Map",
#     "full_audio_url": "https://drive.google.com/uc?id=1BRIh3dPeJxkZgmY1KK3sYfILg29sTUXD&export=download",
#     "subtitles": True,
#     "subtitle_style": "word_by_word",
#     "scenes": [
#         {
#             "index": 1,
#             "text": "In 1923, a lone wanderer traced a secret path through the dunes. The wind whispered of forgotten promises.",
#             "image_url": "https://drive.google.com/uc?id=1HBDmhkTpegfP09yB8eir__V1Cn8rKShZ&export=download"
#         },
#         {
#             "index": 2,
#             "text": "Amir Hassan, a Cairo archivist, uncovered a crumbling diary in a sealed archive. His hands trembled as the pages turned.",
#             "image_url": "https://drive.google.com/uc?id=1sGvVuwGPSWaZ2dZ3k7QJjpsAJRdSCEFX&export=download"
#         },
#         {
#             "index": 3,
#             "text": "The diary revealed a weathered map, inked coordinates etched beneath a sun bleached seal. Each line whispered of a hidden vault.",
#             "image_url": "https://drive.google.com/uc?id=1J-APk2fJsyMErWXY-usyYyPsfnc92aNj&export=download"
#         },
#         {
#             "index": 4,
#             "text": "If the map is true, where does the gold still lie?",
#             "image_url": "https://drive.google.com/uc?id=1Ncu8SPVAPv2wgXOBoRD8k9F3A2E1Eu1o&export=download"
#         },
#         {
#             "index": 5,
#             "text": "Teams followed the trail, sand swallowing footsteps, hopes rising with each sunrise.",
#             "image_url": "https://drive.google.com/uc?id=1xlgFeglwb-LFHrfLl9GWy-d_eP3yqcUY&export=download"
#         },
#         {
#             "index": 6,
#             "text": "Not everyone sticks around till the end. But you did. The hunt continues. Don't fall behind.",
#             "image_url": "https://drive.google.com/uc?id=1490C8AS76LbDNSsUPLBVL2-a266rvKvq&export=download"
#         }
#     ]
# }

headers = {"Content-Type": "application/json"}

print("Sending request...")
response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))