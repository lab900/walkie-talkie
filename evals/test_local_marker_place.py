#!/usr/bin/env python3
"""Screenshot markers land inline on the LOCAL engine (2026-10-04).

    python3 evals/test_local_marker_place.py

Until 2026-10-04 the local model returned prose only and `LocalWhisperSource`
had no `audioOffset(of:)`, so no cue was ever reserved and every picture of a
local dictation went to the footer (outbox: 135 local dictations, 224 shots,
0 inline). Now the helper sends `words[]` and the source answers the clock.

This drives the real halves without a microphone or a speaker:
`POST /test/local-fallback {"wav"}` decodes a corpus WAV with whatever local
model is loaded and answers its `words`; those words go back through
`POST /test/shot-marker` (the real `ShotMarker.place`) with presses placed in
the gaps between them. Nothing is delivered. The third half — that a real
press is measured on the WAV's clock — is `MicRecorder.offset(of:)`, the same
call ElevenLabs has used since 2026-09-19.
"""

import json
import os
import sys
import unittest
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_marker_place import BASE, PORTS  # noqa: E402

CORPUS = os.path.expanduser("~/.walkie-talkie/voice-corpus")
CLIPS = ["2026-10-01/12-16-04-wispr204.wav", "2026-10-01/15-10-02-wispr84.wav",
         "2026-10-01/13-22-49-wispr549.wav"]


def post(path, body, timeout=200):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


@unittest.skipIf(BASE is None, "no relay listening on %s" % (PORTS,))
class LocalInline(unittest.TestCase):

    def test_every_press_between_two_words_lands_before_the_second(self):
        placed = total = 0
        for clip in CLIPS:
            wav = os.path.join(CORPUS, clip)
            if not os.path.exists(wav):
                continue
            answer = post("/test/local-fallback", {"wav": wav, "words": True})
            self.assertTrue(answer.get("ok"), answer)
            words = answer.get("words") or []
            self.assertTrue(words, "the local model sent no word timings for %s" % clip)
            self.assertEqual("".join(w["text"] for w in words).strip(), answer["text"])
            # Asked without a cue, the helper sends none: they cost +45 % decode time.
            if clip == CLIPS[0]:
                bare = post("/test/local-fallback", {"wav": wav})
                self.assertEqual(bare.get("words"), [], "word timings sent with no marker cued")
            # A press half-way between word k's end and word k+1's start,
            # for every third gap.
            for k in range(0, len(words) - 1, 3):
                at = (words[k]["end"] + words[k + 1]["start"]) / 2
                text = post("/test/shot-marker", {"words": words, "available": [1],
                                                  "cues": [{"kind": "shot", "index": 1, "at": at}]})["text"]
                total += 1
                self.assertIn("[📸1]", text, "footer, not inline: %r" % text)
                after = text.split("[📸1]", 1)[1].strip()
                if after.startswith(words[k + 1]["text"].strip()):
                    placed += 1
                else:
                    self.fail("press at %.2f s landed before %r, expected %r"
                              % (at, after[:20], words[k + 1]["text"]))
        print("\n%d/%d presses inline, each before the word that followed the press" % (placed, total))
        self.assertGreater(total, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
