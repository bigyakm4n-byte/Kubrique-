#!/usr/bin/env python3
"""
CRESCENT X mark for KUBRIQUE - construction A (hand-authored geometry, exact arcs).

Geometry (viewBox 0 0 512 512, plain python maths, no numpy)
  ring-crescent : circle (O, R) minus an offset circle (O + (-D, 0), R2).  The two
                  circles intersect, so the shape is written as two exact arcs
                  (outer arc tip->tip through 3 o'clock, inner arc back) rather
                  than an evenodd pair (evenodd would also fill the lune of the
                  inner circle that pokes out on the left).
  ring-x1       : descending ring.  Outer ellipse (a,b) at +THETA minus a lens
                  ellipse (a2,b2) that is smaller, shifted perpendicular to the
                  long axis and rotated by a few degrees.  The lens pokes through
                  the upper-right edge, so the ring reads as a thick lower-left
                  band, a thin horn at the upper-left end and a pointed tip at the
                  lower-right end (as in the reference).  Written as outer arc +
                  lens arc between the two intersection points.
  ring-x2       : ascending ring, same recipe at -THETA; its lens stays inside the
                  outer ellipse, so it is an evenodd pair of whole ellipses.

Weave (checked against the reference)
  x1 over x2 at both centre crossings; x1 over the crescent at its lower-right tip;
  x2 over the crescent at its upper-right tip.  All other ends and the crescent
  tips pass through open space.  Stacking: crescent, x2, x1.  Gaps are explicit
  cut shapes: each under-ring is masked by the over-ring's visible outline drawn
  with a black stroke of width 2*GAP (and black fill).  Recolour the whole mark
  by changing the single fill on <g id="mark">.

Run:  python3 gen_mark.py   -> mark.svg, mark-light.svg, preview.html (next to it)
"""
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ parameters
INK   = "#111111"
LIGHT = "#F3E7C3"
GAP   = 7.5                     # weave gap width (units)

# crescent: outer circle (O, R) minus an inner cut-out whose centre is shifted CD to the
# left.  The cut-out is a circle stretched 3% horizontally (CRX x CRY): a pure circle with
# the same tips (10.8 / 7.2 o'clock) came out ~25% thinner at 12 and 6 o'clock than the
# reference; the slight stretch restores that weight while keeping the smooth taper.
OX, OY, R = 265.0, 256.0, 222.0
CD, CRX, CRY = 27.0, 213.0, 206.5

# x1 (descending, upper-left -> lower-right).  Outer ellipse E and lens L, absolute.
# The lens is longer, narrower, lower-right-shifted and rotated a few degrees flatter
# than the outer ellipse, so it pokes out through the upper-right edge from about a
# third of the way along: that leaves a thin horn at the upper-left end, an open upper
# edge, and a thick band that tapers to a point on the crescent at the lower right.
X1 = dict(E=(236.8, 259.3, 236.0, 56.0, 27.0),
          L=(286.0, 250.8, 310.0, 36.0, 29.0))
X2 = dict(E=(234.1, 267.8, 230.0, 54.8, -32.4),
          L=(231.9, 272.9, 197.3, 35.1, -34.2))


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ------------------------------------------------------------------ ellipse helpers
class Ell:
    def __init__(self, cx, cy, a, b, th_deg):
        self.cx, self.cy, self.a, self.b, self.th = cx, cy, a, b, th_deg
        self.c, self.s = math.cos(math.radians(th_deg)), math.sin(math.radians(th_deg))

    def pt(self, t):
        x, y = self.a * math.cos(t), self.b * math.sin(t)
        return (self.cx + x * self.c - y * self.s, self.cy + x * self.s + y * self.c)

    def local(self, p):
        dx, dy = p[0] - self.cx, p[1] - self.cy
        return (dx * self.c + dy * self.s, -dx * self.s + dy * self.c)

    def inside(self, p):
        x, y = self.local(p)
        return (x / self.a) ** 2 + (y / self.b) ** 2 < 1.0

    def param_of(self, p):
        x, y = self.local(p)
        return math.atan2(y / self.b, x / self.a)

    def arc(self, t1, t2, ccw=False):
        """SVG 'A' command from pt(t1) to pt(t2) travelling in +t (clockwise on
        screen, sweep=1) or -t (sweep=0)."""
        if ccw:
            span = (t1 - t2) % (2 * math.pi)
        else:
            span = (t2 - t1) % (2 * math.pi)
        large = 1 if span > math.pi else 0
        sweep = 0 if ccw else 1
        x, y = self.pt(t2)
        return f"A{f(self.a)} {f(self.b)} {f(self.th)} {large} {sweep} {f(x)} {f(y)}"


def ring(p):
    """(outer, lens) ellipses of ring p."""
    return Ell(*p["E"]), Ell(*p["L"])


def intersections(E, L, n=4000):
    """Parameters t on E where E crosses L (bisection on sign changes)."""
    ts = []
    prev = None
    for i in range(n + 1):
        t = -math.pi + 2 * math.pi * i / n
        v = L.inside(E.pt(t))
        if prev is not None and v != prev[1]:
            lo, hi = prev[0], t
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                if L.inside(E.pt(mid)) == prev[1]:
                    lo = mid
                else:
                    hi = mid
            ts.append(0.5 * (lo + hi))
        prev = (t, v)
    return ts


def band_path(E, L):
    """Outline of E minus L.  Returns (d, kind)."""
    ts = intersections(E, L)
    if not ts:
        # lens wholly inside: evenodd pair of whole ellipses
        p0 = E.pt(0.0); q0 = L.pt(0.0)
        d = (f"M{f(p0[0])} {f(p0[1])} {E.arc(0.0, math.pi)} {E.arc(math.pi, 0.0)} Z "
             f"M{f(q0[0])} {f(q0[1])} {L.arc(0.0, math.pi)} {L.arc(math.pi, 0.0)} Z")
        return d, "evenodd"
    assert len(ts) == 2, f"expected 2 crossings, got {len(ts)}"
    t1, t2 = ts
    # outer arc from t1 to t2 (+t) must lie outside the lens; otherwise go the other way
    mid = t1 + ((t2 - t1) % (2 * math.pi)) / 2
    if L.inside(E.pt(mid)):
        t1, t2 = t2, t1
    p1, p2 = E.pt(t1), E.pt(t2)
    # lens arc from p2 back to p1, choosing the side that lies inside E
    u1, u2 = L.param_of(p2), L.param_of(p1)
    midl = u1 + ((u2 - u1) % (2 * math.pi)) / 2
    ccw = not E.inside(L.pt(midl))
    d = (f"M{f(p1[0])} {f(p1[1])} {E.arc(t1, t2)} {L.arc(u1, u2, ccw=ccw)} Z")
    return d, "nonzero"


def crescent_path():
    O = Ell(OX, OY, R, R, 0.0)
    I = Ell(OX - CD, OY, CRX, CRY, 0.0)
    d, kind = band_path(O, I)
    return d, kind, O, I


# ------------------------------------------------------------------ build
E1, L1 = ring(X1)
E2, L2 = ring(X2)
d1, k1 = band_path(E1, L1)
d2, k2 = band_path(E2, L2)
dc, kc, CO, CI = crescent_path()


def diagnostics():
    print("-- diagnostics (units) --")
    for name, E, L in (("x1", E1, L1), ("x2", E2, L2)):
        tipA, tipB = E.pt(math.pi), E.pt(0.0)
        off = E.local((L.cx, L.cy))
        print(f"{name}: outer tips {tuple(round(v,1) for v in tipA)} -> {tuple(round(v,1) for v in tipB)}; "
              f"lens tips {tuple(round(v,1) for v in L.pt(math.pi))} -> {tuple(round(v,1) for v in L.pt(0.0))}; "
              f"lens offset in outer frame (along, perp) = ({off[0]:.1f}, {off[1]:.1f}), dtheta = {L.th - E.th:.1f}")
        # band thickness on each side at stations along the axis
        rows = []
        for x in [round(E.a * k) for k in (-0.95, -0.85, -0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7, 0.85, 0.95)]:
            h = E.b * math.sqrt(1 - (x / E.a) ** 2)
            # scan local y from -h..h for lens membership
            n = 400
            ins = []
            for i in range(n + 1):
                y = -h + 2 * h * i / n
                c, s = E.c, E.s
                P = (E.cx + x * c - y * s, E.cy + x * s + y * c)
                ins.append(L.inside(P))
            # thickness of the -y side (upper-right for x1 / upper-left for x2) and +y side
            top = 0
            while top <= n and not ins[top]:
                top += 1
            bot = 0
            while bot <= n and not ins[n - bot]:
                bot += 1
            if top > n:
                rows.append((x, round(2 * h, 1), "solid"))
            else:
                rows.append((x, round(top * 2 * h / n, 1), round(bot * 2 * h / n, 1)))
        print(f"   band (-y side, +y side) by local x: {rows}")
    for name, E, L in (("x1", E1, L1), ("x2", E2, L2)):
        pts = [tuple(round(v, 1) for v in E.pt(t)) for t in intersections(E, L)]
        print(f"{name}: outer/lens crossings (horn end, pointed tip) {pts}")
    # ring tips vs crescent band
    def band_depth(p):
        """how far p lies inside the crescent band, measured along the ray from O (units; <0 = in the hole)"""
        t = math.atan2(p[1] - OY, p[0] - OX)
        r = R
        while r > 0 and not CI.inside((OX + r * math.cos(t), OY + r * math.sin(t))):
            r -= 0.25
        return math.hypot(p[0] - OX, p[1] - OY) - r, R - math.hypot(p[0] - OX, p[1] - OY)
    x1tip = sorted(intersections(E1, L1), key=lambda t: E1.pt(t)[0])
    for name, p in (("x1 pointed tip", E1.pt(x1tip[-1]) if x1tip else E1.pt(0.0)), ("x2 upper-right tip", E2.pt(0.0)), ("x2 lens UR tip", L2.pt(0.0))):
        di, do = band_depth(p)
        print(f"{name} at {tuple(round(v,1) for v in p)}: {round(di,1)} past crescent inner edge, {round(do,1)} inside outer edge")
    # crescent tips
    for t in intersections(CO, CI):
        p = CO.pt(t)
        ang = math.degrees(math.atan2(p[1] - OY, p[0] - OX))
        print(f"crescent tip at {tuple(round(v,1) for v in p)}  angle {round(ang,1)}  clock {round(((ang+90)%360)/30,1)}")
    for ang in (0, 45, 90, -45, -90, 110, -110):
        t = math.radians(ang)
        r = R
        while r > 0 and not CI.inside((OX + r * math.cos(t), OY + r * math.sin(t))):
            r -= 0.25
        print(f"crescent thickness at {ang:4d} deg: {round(R - r,1)}")
    # bbox
    xs, ys = [], []
    for E in (E1, E2, CO):
        for i in range(720):
            p = E.pt(2 * math.pi * i / 720)
            xs.append(p[0]); ys.append(p[1])
    print(f"bbox x {round(min(xs),1)}..{round(max(xs),1)}  y {round(min(ys),1)}..{round(max(ys),1)}  "
          f"centre ({round((min(xs)+max(xs))/2,1)}, {round((min(ys)+max(ys))/2,1)})")


def svg(ink):
    g2 = f(2 * GAP)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512">
  <title>KUBRIQUE - Crescent X</title>
  <defs>
    <!-- visible outlines of the rings (exact arcs); reused by the masks as cut shapes -->
    <path id="cx-crescent" fill-rule="{kc}" d="{dc}"/>
    <path id="cx-x1" fill-rule="{k1}" d="{d1}"/>
    <path id="cx-x2" fill-rule="{k2}" d="{d2}"/>
    <!-- weave gaps: each under-ring is cut by the over-ring's outline, stroked 2*GAP wide -->
    <mask id="cx-under-x1" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use xlink:href="#cx-x1" fill="#000" stroke="#000" stroke-width="{g2}" stroke-linejoin="round"/>
    </mask>
    <mask id="cx-under-x1-x2" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use xlink:href="#cx-x1" fill="#000" stroke="#000" stroke-width="{g2}" stroke-linejoin="round"/>
      <use xlink:href="#cx-x2" fill="#000" stroke="#000" stroke-width="{g2}" stroke-linejoin="round"/>
    </mask>
  </defs>
  <g id="mark" fill="{ink}">
    <use id="ring-crescent" xlink:href="#cx-crescent" mask="url(#cx-under-x1-x2)"/>
    <use id="ring-x2" xlink:href="#cx-x2" mask="url(#cx-under-x1)"/>
    <use id="ring-x1" xlink:href="#cx-x1"/>
  </g>
</svg>
'''


PREVIEW = '''<!doctype html>
<html><head><meta charset="utf-8"><title>Crescent X - A review</title>
<style>
  body{margin:0;background:#fff;font:12px/1.3 Helvetica,Arial,sans-serif;color:#333}
  .row{display:flex;gap:14px;align-items:flex-start;padding:10px 10px 0}
  .box{position:relative;overflow:hidden;background:#fff}
  .lab{position:absolute;left:6px;top:4px;font-size:11px;color:#888;z-index:2}
  .ref{width:320px;height:311px}
  .ref img{position:absolute;left:-63px;top:-42px;width:435px}
  .mine{width:320px;height:311px}
  .mine img{position:absolute;left:1px;top:-5px;width:318px;height:318px}
  .ovl{width:320px;height:311px}
  .ovl img.r{position:absolute;left:-63px;top:-42px;width:435px;opacity:.35}
  .ovl img.m{position:absolute;left:1px;top:-5px;width:318px;height:318px;opacity:.75;filter:invert(1) sepia(1) saturate(30) hue-rotate(-20deg)}
  .dark{width:420px;height:420px;background:#0d0e13}
  .dark img{width:420px;height:420px;display:block}
  .smalls{display:flex;flex-direction:column;gap:8px}
  .sm{display:flex;gap:8px;align-items:center;padding:6px;background:#fff}
  .sm.d{background:#0d0e13}
  .zoom{width:220px;height:200px;overflow:hidden;position:relative;background:#fff}
  .zoom img{position:absolute;width:640px;height:640px}
</style></head><body>
<div class="row">
  <div class="box ref"><span class="lab">reference</span><img src="file://REF"></div>
  <div class="box mine"><span class="lab">A / mark.svg</span><img src="mark.svg"></div>
  <div class="box ovl"><span class="lab">overlay (mine = orange)</span><img class="r" src="file://REF"><img class="m" src="mark.svg"></div>
  <div class="box dark"><img src="mark-light.svg"></div>
  <div class="smalls">
    <div class="sm"><img src="mark.svg" width="40" height="40"><img src="mark.svg" width="24" height="24"></div>
    <div class="sm d"><img src="mark-light.svg" width="40" height="40"><img src="mark-light.svg" width="24" height="24"></div>
    <div class="sm"><img src="mark.svg" width="64" height="64"></div>
    <div class="sm d"><img src="mark-light.svg" width="64" height="64"></div>
  </div>
</div>
<div class="row">
  <div class="zoom"><span class="lab">centre x2</span><img src="mark.svg" style="left:-190px;top:-250px"></div>
  <div class="zoom"><span class="lab">x1 tip / crescent x2</span><img src="mark.svg" style="left:-370px;top:-390px"></div>
  <div class="zoom"><span class="lab">x2 tip / crescent x2</span><img src="mark.svg" style="left:-370px;top:-80px"></div>
  <div class="zoom"><span class="lab">x1 horn x2</span><img src="mark.svg" style="left:-10px;top:-100px"></div>
  <div class="zoom"><span class="lab">x2 lower-left x2</span><img src="mark.svg" style="left:-10px;top:-380px"></div>
</div>
</body></html>
'''

if __name__ == "__main__":
    diagnostics()
    with open(os.path.join(HERE, "mark.svg"), "w") as fh:
        fh.write(svg(INK))
    with open(os.path.join(HERE, "mark-light.svg"), "w") as fh:
        fh.write(svg(LIGHT))
    ref = "/tmp/claude-0/-home-user-Kubrique-/1089e9da-6911-5cb8-8308-49f4fb2445d5/scratchpad/orbital/target-crop.png"
    with open(os.path.join(HERE, "preview.html"), "w") as fh:
        fh.write(PREVIEW.replace("REF", ref))
    print("wrote mark.svg, mark-light.svg, preview.html")
