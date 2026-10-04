import re, unicodedata
def normalise(text):
    """Lowercase, strip diacritics, strip punctuation, collapse whitespace.

    The hyphen goes to a **space**, not to nothing, and that is a judgement call
    worth naming: the baseline writes `back-end` where Wispr writes `backend`,
    and neither reading costs an agent anything. Splitting them makes that a
    two-token miss instead of a one-token miss, which understates the model
    slightly and is at least symmetric across the four configs. Joining them
    would have been the other defensible choice and would flatter `backend`
    while breaking `walkie-talkie`.
    """
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Romanian comma-below survives NFD on some fonts; fold it by hand.
    text = text.replace("ș", "s").replace("ț", "t").replace("ş", "s").replace("ţ", "t")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text):
    return normalise(text).split()

def wer(ref_tokens, hyp_tokens):
    """Levenshtein over words, divided by the reference length.

    Iterative two-row DP: the longest clip here is twenty minutes, and a full
    matrix for it is 3000×3000 ints for no reason.
    """
    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0
    prev = list(range(len(hyp_tokens) + 1))
    for i, r in enumerate(ref_tokens, 1):
        cur = [i] + [0] * len(hyp_tokens)
        for j, h in enumerate(hyp_tokens, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h))
        prev = cur
    return prev[-1] / len(ref_tokens)


