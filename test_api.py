import requests
import json

url = "http://localhost:5000/build"

data = {
  "title": "Georgia's Lost Treasury - 2000 Year Old Computer V2",
  "full_audio_url": "https://drive.google.com/uc?id=1RXR1hcJ6HsosIZoSWJi-wD4VHV9C1A9u&export=download",
  "subtitles": True,
  # "overlay": False,
  "subtitle_style": "word_by_word",
  "transition": "fade",
  "transition_duration": 0.5,
  "scenes": [
    {
      "index": 1,
      "text": "A cargo ship vanished in 1803, swallowed by the Atlantic. Its wreck, sealed for centuries, held a secret.",
      "image_url": "https://drive.google.com/uc?id=18BB4RFla_7xrRBLJYWJCKTJDheuKtfZK&export=download",
      "transition": "fade",
      "transition_duration": 0.5,
      "overlay": "documentary.mp4",
      "ken_burns_effect": "zoom_in"
    },
    {
      "index": 2,
      "text": "Dr. Elena Martinez stands on the deck of the research vessel. She watches the sonar‑lit hull.",
      "image_url": "https://drive.google.com/uc?id=1ax2HAB08TrGSX09PHCFgjOqG1g9ILIuV&export=download",
      "transition": "zoom",
      "transition_duration": 0.6,
      "overlay": "documentary_2.mp4",
      "ken_burns_effect": "pan_right"
    },
    {
      "index": 3,
      "text": "Coordinates 34°12′N 58°23′W were logged in a sealed parchment. The recovered logbook described a bronze machine, gears turning without power. The object defies known chronology.",
      "image_url": "https://drive.google.com/uc?id=1kyzIq2J1MZqka5LiHPKW7B_hF-uVi5SB&export=download",
      "transition": "fade_black",
      "transition_duration": 0.8,
      "ken_burns_effect": "zoom_out"
    },
    {
      "index": 4,
      "text": "How could a 2,000‑year‑old computer survive in a wooden ship?",
      "image_url": "https://drive.google.com/uc?id=1rRe2CdFeu8UAn8ErIxJNlUpZARrkxpbh&export=download",
      "transition": "fade",
      "transition_duration": 0.4,
      "overlay": "dust.mp4",
      "ken_burns_effect": "pan_up"
    },
    {
      "index": 5,
      "text": "Not everyone sticks around till the end. But you did. The hunt continues. Don't fall behind.",
      "image_url": "https://drive.google.com/uc?id=1v86tPDMNbE12iJGkznWc6OicWwaW4Te1&export=download",
      "transition": "zoom",
      "transition_duration": 0.6
    },
    {
      "index": 6,
      "text": "The sealed chamber remains, its bronze plates cold. Future dives will test the limits of history.",
      "image_url": "https://drive.google.com/uc?id=1IlZADJ8YNlRvOioeZeAIc2dk-e7TdJl4&export=download",
      "transition": "fade_black",
      "transition_duration": 0.8,
      "overlay": "documentary_4.mp4",
      "ken_burns_effect": "pan_down"
    }
  ]
}

# data = {
#     "title": "He Defected to America. Then Vanished Back Into Cuba.",
#     "full_audio_url": "https://drive.google.com/file/d/1Cr2r1QwS1_jZQ4S4_zCQigdwJvMaAUda/view?usp=drive_link",
#     "subtitles": True,
#     "subtitle_style": "word_by_word",
#     "transition": "fade",
#     "transition_duration": 0.5,
#     "scenes": [
#         {
#             "index": 1,
#             "text": "He handed America a Soviet fighter jet. Walked off the runway. And disappeared into a CIA building.",
#             "image_url": "https://drive.google.com/uc?id=1eNUjXmvzrqSVLIgPDQ6CZEgX_S2-4TWx&export=download"
#         },
#         {
#             "index": 2,
#             "text": "Florida. 1969. A Cuban military pilot landed a MiG-17 at Homestead Air Force Base. No warning. No contact. Just a Soviet jet sitting on an American runway.",
#             "image_url": "https://drive.google.com/uc?id=1-aVb5wSvQAjs0mn_oem4bzWjULzbk0yF&export=download"
#         },
#         {
#             "index": 3,
#             "text": "The CIA took him immediately. Months of debriefing. Classified transcripts. Then they released him. New identity. New city. New life. For ten years nothing.",
#             "image_url": "https://drive.google.com/uc?id=1zsMUaTroiFUGnJM83zVx3W3Ibx8a9Fqs&export=download"
#         },
#         {
#             "index": 4,
#             "text": "1979. He hijacked a commercial flight from New York. Forced it to land in Havana. Walked off the plane. And vanished.",
#             "image_url": "https://drive.google.com/uc?id=1LE09yvuIGbBI-sBZ3kSQxCZl0QHBBOI_&export=download"
#         },
#         {
#             "index": 5,
#             "text": "No death certificate. No prison record. No US file. No Cuban file. The CIA debriefing transcripts still partially redacted today.",
#             "image_url": "https://drive.google.com/uc?id=1VGnOR9I9dbNRzdWtut8vqAdPejqq4pnS&export=download"
#         },
#         {
#             "index": 6,
#             "text": "He gave them everything. Then walked back into the country he escaped. And the record just stops. So which side was he actually working for. Not everyone sticks around till the end. But you did. The hunt continues. Don't fall behind.",
#             "image_url": "https://drive.google.com/uc?id=135getYgaPVE9PoVIFIJf9ZzXRGM62-l6&export=download"
#         }
#     ]
# }

# data = {
#     "title": "Georgia's Lost Treasury - 2000 Year Old Computer",
#   "full_audio_url": "https://drive.google.com/uc?id=1RXR1hcJ6HsosIZoSWJi-wD4VHV9C1A9u&export=download",
#       "subtitles": True,
#     "subtitle_style": "word_by_word",
#     "transition": "zoom",
#     "transition_duration": 0.5,

#   "scenes": [
#     {
#       "index": 1,
#       "text": "A cargo ship vanished in 1803, swallowed by the Atlantic. Its wreck, sealed for centuries, held a secret.",
#       "image_url": "https://drive.google.com/uc?id=18BB4RFla_7xrRBLJYWJCKTJDheuKtfZK&export=download"
#     },
#     {
#       "index": 2,
#       "text": "Dr. Elena Martinez stands on the deck of the research vessel.She watches the sonar‑lit hull.",
#       "image_url": "https://drive.google.com/uc?id=1ax2HAB08TrGSX09PHCFgjOqG1g9ILIuV&export=download"
#     },
#     {
#       "index": 3,
#       "text": "Coordinates 34°12′N 58°23′W were logged in a sealed parchment. The recovered logbook described a bronze machine, gears turning without power. The object defies known chronology.",
#       "image_url": "https://drive.google.com/uc?id=1kyzIq2J1MZqka5LiHPKW7B_hF-uVi5SB&export=download"
#     },
#     {
#       "index": 4,
#       "text": "How could a 2,000‑year‑old computer survive in a wooden ship?",
#       "image_url": "https://drive.google.com/uc?id=1rRe2CdFeu8UAn8ErIxJNlUpZARrkxpbh&export=download"
#     },
#     {
#       "index": 5,
#       "text": "Not everyone sticks around till the end. But you did. The hunt continues. Don't fall behind.",
#       "image_url": "https://drive.google.com/uc?id=1v86tPDMNbE12iJGkznWc6OicWwaW4Te1&export=download"
#     },
#     {
#       "index": 6,
#       "text": "The sealed chamber remains, its bronze plates cold. Future dives will test the limits of history.",
#       "image_url": "https://drive.google.com/uc?id=1IlZADJ8YNlRvOioeZeAIc2dk-e7TdJl4&export=download"
#     }
#     ]
# }

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