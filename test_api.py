import requests
import json

url = "http://localhost:5000/build"

data = {
    "title": "Greek Fire - The Weapon That Burned Wate",
  "full_audio_url": "https://drive.google.com/file/d/1QfBGW5-Oznrgn7WKEtB7vkcKaKuUCpDD/view?usp=drive_link",
  "webhook_url": "https://hook.eu1.make.com/nstc6yoms1rrcbagk15e8jynywtf87to",
  "subtitles": True,           
  "subtitle_style": "word_by_word", 
"transition": "fade",
  "transition_duration": 0.5,
  "overlay_opacity": 0.2, 

  "scenes": [
    {
      "index": 1,
      "text": "They called it fire that ate the sea. A weapon no enemy could douse. Invisible, unstoppable.",
      "image_url": "https://drive.google.com/uc?id=1L7MtccgOwmNYgGhbgrwD-1XBMQD8UiBE&export=download",
       "transition": "fade",
      "ken_burns_effect": "zoom_in",
      # "overlay": "documentary.mp4",
      "evidence_card": {
        "title": "",
        "date": "",
        "excerpt": ""
      }
},
    {
      "index": 2,
      "text": "Byzantine Empire. 7th century. Invented under Emperor Leo III. Mixed sulfur, quicklime, oil. Launched from siphon tubes. To protect Constantinople. During the Arab siege of 674.",
      "image_url": "https://drive.google.com/uc?id=1bDdOuKBrYLvwtbWfNkGcYBUR5MN4hL0O&export=download",
"transition": "fade_black",
      "ken_burns_effect": "pan_right",
      "overlay": "documentary_2.mp4",
    "evidence_card": {
        "title": "",
        "date": "",
        "excerpt": ""
      }
    },
    {
      "index": 3,
      "text": "A captured Arabic chronicler described the blaze. Found in the Byzantine Naval Logbook of 674. The navy feared yet deployed it. Even water turned to flame.",
      "image_url": "https://drive.google.com/uc?id=1qw1S4-W8TRjcb3jmbKMW59NG7-1Lc6Lh&export=download",
 "transition": "zoom",
      "ken_burns_effect": "zoom_in",
      "overlay": "dust.mp4",
            "evidence_card": {
        "title": "NAVAL LOGBOOK 674",
        "date": "674 AD",
        "excerpt": "Entry describes fiery weapon extinguishing enemy ships."
      }

    },
    {
      "index": 4,
      "text": "The original siphon rests sealed in a Turkish museum. The logbook survives in the Vatican archive. The formula remained a guarded state secret.",
      "image_url": "https://drive.google.com/uc?id=1EPUrUxqetxYTovl-ePxqJzZ2K_QnPoRi&export=download",
"transition": "slide_left",
      "ken_burns_effect": "zoom_out",
      # "overlay": "documentary_3.mp4",
      "evidence_card": {
        "title": "",
        "date": "",
        "excerpt": ""
      }
    },
    {
      "index": 5,
      "text": "Could the secret of Greek fire still be hidden today? The mystery lingers.",
      "image_url": "https://drive.google.com/uc?id=1F85yMzImPK-bCY7N949zXn6gvhBOQ3FU&export=download",
"transition": "fade",
      "ken_burns_effect": "pan_up",
      "overlay": "documentary_2.mp4",
      "evidence_card": {
        "title": "",
        "date": "",
        "excerpt": ""
      }
    },
    {
      "index": 6,
      "text": "Not everyone sticks around till the end. But you did.",
      "image_url": "https://drive.google.com/uc?id=1Jqm_XD1UQnQ2yHDcTEl0F5OSSnAcfga_&export=download",
"transition": "fade_black",
      "ken_burns_effect": "",
      "overlay": "documentary_4.mp4",
     "evidence_card": {
        "title": "",
        "date": "",
        "excerpt": ""
      }
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