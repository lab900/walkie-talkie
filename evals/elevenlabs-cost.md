# What ElevenLabs really costs for prompt dictation (2026-09-28)

Victor, 28 Sep: *"ElevenLabs burns a lot of money for transcribing prompts all day."* Measured
read-only: the usage API, the relay's own logs and Wispr's History. No transcription call was
made and the app was not touched.

**Verdict.** In **dollars**, ElevenLabs is cheap at his real volume: Starter ($6/month) covers an
average month of Scribe + Live at ~72 % of the credits. What burned the credits was the **tests**
(39 % of every credit since 18 Sep, 92 % of 26 Sep) and the **Free-tier per-second rate** (~3.5×
Starter's). Wispr Pro costs **2.5× more** ($15). The case for Wispr rests on the quota cliff and
on accuracy, not on money.

## Sources (S1–S8)

- **S1** `GET /v1/user/subscription` (28 Sep 20:50): `tier starter`, `character_count 2014`, `character_limit 30000`,
  reset `1793091782` (27 Oct 09:03 UTC), `next_invoice 600` cents, `can_extend_character_limit false`.
- **S2** `GET /v1/usage/character-stats?breakdown_type=model|product_type`, day + hour buckets, 60 days: nothing
  before 18 Sep; product `STT` only; models `scribe_v2`, `scribe_v2_realtime`. Consistent with S1 (2 014).
- **S3** `~/.walkie-talkie/relay.log`. Takes are `🎙️ recording stopped — Ns, uploading to ElevenLabs`, corrections are
  `💬 live correction: Ns since the last cut`. A take is a **test** when it records through `🧪 WT Inject` /
  `🎓 TO Wispr` / `🎙️TO Zoom` or follows a `/test/` call by less than 60 s. Each hour's credits are split
  in proportion to seconds. Credits in an hour with no take are **unlogged**.
- **S4** `~/.walkie-talkie/decode-rate.jsonl` (`engine`, `audio`, `decode`, warm only). **S5** Wispr `flow.sqlite`
  `History` (a copy, no `TO Wispr`/`WT Inject`). Jun–Aug is the baseline: Wispr was the only engine then.
- **S6** Google Calendar: the 11 eight-hour training days Jun–Aug. **S7** Web, 28 Sep: [pricing](https://elevenlabs.io/pricing),
  [pricing/api](https://elevenlabs.io/pricing/api), [PAYG](https://elevenlabs.io/docs/overview/administration/pay-as-you-go),
  [billing](https://elevenlabs.io/docs/overview/administration/billing), [wisprflow.ai/pricing](https://wisprflow.ai/pricing).
- **S8** `evals/live-asr-bakeoff.md:80-111`, `~/workspace/voice-distill/reports/night-2026-09-27.md:14-27`.

## 1. Where the credits went (S2 × S3)

| day (local) | plan | Victor s | Victor cr | test cr | unlogged cr | total |
|---|---|---:|---:|---:|---:|---:|
| 18 Sep | Free | 1 791 | 2 140 | 0 | 336 | 2 476 |
| 19 Sep | Free | 391 | 434 | 0 | 839¹ | 1 273 |
| 20 Sep | Free | 170 | 190 | 72 | 0 | 262 |
| 21 Sep | Free | 712 | 787 | 0 | 0 | 787 |
| 25 Sep | Free | 291 | 71 | 0 | 266² | 337 |
| 26 Sep | Free | 100³ | 168 | **4 485** | 210¹ | 4 863 |
| 27 Sep | Free → Starter | 5 | 2 | 33 | 0 | 35 |
| 28 Sep (to 20:50) | Starter | 1 826 | 1 935 | 46 | 0 | 1 981 |
| **all** | | | **5 728 (48 %)** | **4 635 (39 %)** | **1 651 (14 %)** | **12 014** |

¹ Live-caption build sessions (19 Sep 16–17 h, deliveries `test → ttys999`; 26 Sep 01–07 h, the
commits `Live caption: …`), so development, not dictation. ² Hour-bucket lag next to his 19 h takes,
probably his own. ³ 668 s logged, but the 568 s at 23 h were the Wispr teacher batch riding the chord
(journal *Night 26→27 Sep*), and they billed **0**: by 21 h the Free quota already stood at 9 998 / 10 000 (S2 hourly).

Two claims in the notes do not hold. **The 26 Sep host tests emptied the Free quota, not the
teacher batch** (`harness.py:53` has the 4 561 right; `docs/journal.md:13445` blames the batch).
**The 28 Sep morning was not tests.** The 07 h and 09 h test takes billed 0 (fake Scribe). The
08 h burst (497 cr) was 19 takes on the Elgato Wave XLR, delivered to `ttys002`.

## 2. Credits per second (measured, S2 ÷ S3)

| regime | credits | seconds | rate |
|---|---:|---:|---:|
| Free, Scribe v2 batch only (21 Sep, all Victor) | 787 | 712 | **1.11 cr/s** |
| Free, Scribe + Live (26 Sep 15 h, tests) | 2 340 | 689 | 3.4 cr / dictated s |
| Starter, `scribe_v2_realtime` (28 Sep, Victor) | 1 079 | 1 826 streamed | **0.59 cr/s** |
| Starter, `scribe_v2` batch (28 Sep, Victor) | 855 | 2 966 uploaded (1 826 final + 1 140 corrections) | **0.29 cr/s** |
| **Starter, Scribe + Live, per dictated second** | 1 935 | 1 826 | **1.06 cr/s** |

Scribe + Live bills each second **three times**: the realtime stream (`ElevenLabsLive.swift:308`),
the correction spans (`:454`) and the full final upload (`ElevenLabsSource.swift:893`). Batch
alone would be ~0.29 cr/s, **3.6× cheaper**. S7's "330 credits per minute" and its per-plan
hours (Starter 4 h 30 batch / 2 h 30 realtime) do not match what the account bills. S1/S2 are the truth.

## 3. One day of dictation (S5 × S6 × §2 Starter rates)

| day | audio | Scribe + Live | Scribe batch only | realtime only |
|---|---:|---:|---:|---:|
| working day, median (n=37) | 855 s (14 min) | 906 cr | 248 cr | 504 cr |
| working day, mean | 1 135 s (19 min) | 1 203 cr | 329 cr | 670 cr |
| training day, median (n=11) | 1 298 s (22 min) | 1 376 cr | 376 cr | 766 cr |
| heavy day (28 Sep, measured) | 1 826 s (30 min) | **1 935 cr** | 530 cr | 1 077 cr |

## 4. Per month vs the plan (Starter 30 000 cr, $6, resets 27 Oct, S1)

| volume (S5) | Scribe + Live | batch only | fits |
|---|---:|---:|---|
| Jun–Aug mean: 20 340 s = 5.65 h/month | 21 560 cr (72 %) | 5 900 cr (20 %) | Starter; batch-only fits even **Free** (10 000) |
| June (peak): 26 597 s = 7.4 h | 28 190 cr (94 %) | 7 710 cr | Starter, barely |
| every weekday like 28 Sep: 21 × 1 826 s | 40 660 cr (136 %) | 11 120 cr | needs Creator |

The next tiers (S7): **Creator** $22 for 121 000 cr, **Pro** $99 for 600 000, **Scale** $299 for 1.8 M.
Starter **cannot overrun** (`can_extend_character_limit false`, S1): past the quota, dictation
stops with `401 quota_exceeded` (journal:13445) unless PAYG credits were topped up. Those are
prepaid, $20 by default, valid 12 months, billed at the API rates. Usage-based billing is legacy
and closed to new self-serve plans (S7). At API rates Scribe + Live costs $0.39 × 1.2 (keyterms,
`ElevenLabsCost.swift:27-28`) + $0.22 × 1.62 = **$0.83 per dictated hour**, or **$4.70** for an average month.

## 5. Wispr Flow (S7)

**Pro: $15/month, or $12 billed annually. "Unlimited dictations"**, so no word cap. Free is capped
at **2 000 words/week** on desktop. Victor dictated **8 300 words/week** Jun–Aug (108 141 words /
13 weeks, S5), 4× the free cap, so Pro is required. Per day that is $0.50 (30-day month), against
**$0.20** for ElevenLabs Starter, or $0.26 per average working day at API rates. If he already pays
for Wispr Pro, its marginal cost is **$0**.

## 6. The three engines

| | ElevenLabs (Scribe + Live) | Wispr Flow | local Whisper |
|---|---|---|---|
| $/month at real usage | **$6** (Starter, 72 % used); $22 on heavy months; ≈$4.70 at API rates | **$15** ($12 annual), flat, unlimited; $0 marginal if already paid | **$0** |
| latency, mic close → text (S4, warm, 22–28 Sep) | p50 **1.28 s**, p90 4.61 s (n=161); live caption while speaking | p50 **1.03 s**, p90 2.52 s (n=781, median clip 30 s) | turbo-A p50 **0.84 s**, p90 3.60 s (n=143); large-C 1.3 s vs 0.9 s per 10 s of audio (S8 night:27) |
| WER on his RO+EN corpus (733 clips, vs Wispr raw, S8) | **not measured**; published RO 3.1 % FLEURS for v1 (journal:10453) | it is the ruler's reference (0 by construction, not a measurement) | large-C **17.8 %** (RO 21.4, EN 9.6); turbo-C 20.4; turbo-A (shipped) 22.0 |
| dependency risk | hard stop at the quota; credits drained by any test that forgets the fake; network; key scopes | closed app: the relay reads its SQLite and suppresses its ⌘V; cloud; plan terms can change | none external; GPU contention with other jobs (bakeoff:111); ~2–4 GB RAM |

**Where the numbers point.** Money does not separate the three at his volume ($0 / $6 / $15). What
does: (1) the **quota cliff**. Tests and one Free-tier day emptied a month in 9 days, and Starter
cannot be extended. Wispr is flat and has no cap. (2) The **live caption triples the bill**: Scribe
batch alone is 0.29 cr/s and would fit even the Free plan. (3) **Accuracy on his voice is known
only relative to Wispr**. Nobody has measured ElevenLabs on the 733-clip ruler, and that is the one
number still missing before choosing between ElevenLabs and Wispr.
