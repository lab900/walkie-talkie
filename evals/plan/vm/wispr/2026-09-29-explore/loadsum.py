"""loadsum.py HOSTLOG — host load (1-min average) mean / max per phase window (UTC)."""
import sys
P = [("boot+build", "03:33:30", "03:36:10"), ("E0 fallback table", "03:36:10", "03:50:35"), ("W6 batch 5", "03:55:00", "03:59:30"),
     ("E1 TE1-8", "04:01:10", "04:06:15"), ("E2 TE9-16", "04:07:05", "04:16:10"), ("E3 TE2,17-25", "04:19:25", "04:29:05")]
P += [tuple(a.split(",")) for a in sys.argv[2:]]
rows = []
for l in open(sys.argv[1]):
    p = l.split()
    if len(p) >= 3:
        rows.append((p[0], float(p[2])))
for name, a, b in P:
    xs = [v for t, v in rows if a <= t < b]
    if xs:
        print("%-18s %s–%s  n=%2d  mean %.1f  max %.1f" % (name, a, b, len(xs), sum(xs) / len(xs), max(xs)))
