# Test plan run — 2026-09-27 08:35

Verdicts: **PASS** = the app does what the plan expects · **BUG** = the plan's prediction of a defect was confirmed · **FAIL** = neither the expectation nor the prediction · **SKIP** / **ERROR**.

PASS 1

| case | verdict | s | expectation | observed |
|---|---|---|---|---|
| TG40 | **PASS** | 63 | 🔽 in the settle of a relay prompt says the words are in flight (or nothing). Predicted defect: the misleading `Back click ignored — finish the sentence you are dictating first` banner. Since Q12 (batch 6, `state.sentenceQueue`): it starts the next plain sentence, no refusal | queue on · refused line=False (before the delivery=False), 'words still in flight' line=False, state just after: listening=True settling=False, a new sentence opened=True · sent forward-right@4.628s forward-right@11.659s back-click@12.789s |
