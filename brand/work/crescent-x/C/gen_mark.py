#!/usr/bin/env python3
"""
CRESCENT X mark for KUBRIQUE - construction C (stroke-based / variable-width strokes).

Every ring is a *variable-width stroke* realised as an outline composed of arcs:
the stroke's two edges are an outer conic and an inner conic that is slightly
smaller and offset toward the thin side, so the band swells on one side and
tapers calligraphically on the other.  The weave gaps are *strokes*: each
UNDER ring is masked by a copy of the OVER ring that is fattened with a
background-coloured stroke of width 2*GAP, so the whole mark stays a single
flat colour and can be recoloured by changing one fill.

Units: everything is designed in units of R (the crescent's outer radius),
then scaled to the 512 box and re-centred on the union bounding box.

    ring-crescent : outer circle (R) minus an inner ellipse (A2 x B2) whose
                    centre is pushed D toward the opening.  The two curves
                    cross at the horns, so the band thins to a sharp point
                    there (classic crescent, not a cut ring).  Rotated by
                    CRES_ROT so the thick side sits a touch below 3 o'clock.
    ring-x1       : descending ring, tilt +X1_TILT.  A genuine variable-width
                    stroke: a slim lens ellipse (L1A x L1B) is offset outward by
                    w(theta), which swells to W1_THICK on the lower-left edge,
                    thins to a W1_THIN hairline on the upper-right edge and is
                    W1_TIP at the tips (so the thick band wraps round rounded
                    tips).  A shallow parabolic bend (X1_BEND) keeps the thick
                    band running through the X centre while the tips sit on
                    the reference's tip-to-tip line.  Emitted as a smooth
                    cubic-Bezier outline.
    ring-x2       : ascending ring, tilt X2_TILT.  Outer (A2x,B2x), inner
                    (A2xi,B2xi) offset E2 toward the lower-right edge, so the
                    upper-left edge is a little heavier (a ring seen from
                    slightly above).

Weave (matches the reference):
    centre       : x1's thick band OVER both bands of x2;
                   x1's hairline far edge UNDER x2 (x2 threads through x1).
    lower-right  : x1's tip OVER the crescent (gap cut round the tip).
    upper-right  : x2's tip OVER the crescent's inner edge (small notch).
    crescent horns and the two left ring ends cross nothing.

Run:  python3 gen_mark.py   -> mark.svg, mark-light.svg, preview.html, overlay.svg
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REF = ("/tmp/claude-0/-home-user-Kubrique-/1089e9da-6911-5cb8-8308-49f4fb2445d5/"
       "scratchpad/orbital/target-crop.png")

# ------------------------------------------------------------------ parameters (R units)
R = 220.0                      # crescent outer radius in viewBox px

# crescent
A2, B2 = 0.968, 0.915          # inner ellipse semi-axes (x along the opening axis)
D = 0.113                      # inner ellipse centre offset toward the opening (left)
CRES_ROT = 3.0                 # deg, clockwise: thick side slightly below 3 o'clock

# X centre relative to the crescent centre
XC = (-0.165, 0.05)

# x1 - descending ring: a variable-width stroke around a slim lens
X1_TILT = 36.0
L1A, L1B = 1.0, 0.105          # lens (hole) ellipse semi-axes
W1_THICK = 0.225               # stroke width at the middle of the lower-left edge
W1_THIN = 0.006                # stroke width at the middle of the upper-right edge (fades to a hairline)
W1_TIP = 0.045                 # stroke width at the two tips
W1_TAPER = 0.40                # thick edge thins by this fraction toward the lower-right tip (swoosh taper)
X1_SHIFT = -0.12               # ring centre shift along local +y (lower-left); negative = up-right
X1_BEND = 0.14                 # parabolic bend: tips pulled back toward local +y by this much
X1_SWAY = -0.22                # S-sway (odd term): upper-left half bows to local +y, lower-right half to local -y
X1_SWAY2 = -0.22               # extra sweep (even term, zero slope at the centre) so the lower-right half
                               # sweeps further to local -y than the upper-left half bows to +y
A1 = L1A + W1_TIP              # outer half-length (for bbox / tip maths)
B1 = L1B + W1_THICK            # outer half-width on the thick side

# x2 - ascending ring (slightly heavier upper-left edge)
X2_TILT = -34.0
A2x, B2x = 1.005, 0.250        # outer ellipse
A2xi, B2xi = 0.930, 0.155      # inner ellipse (the lens)
E2 = 0.012                     # inner ellipse offset toward the lower-right edge
X2_LENS_ROT = -2.0             # deg: the lens is turned a touch inside the band, so the upper-left edge thins
                               # toward the upper-right tip and the lower-right edge thickens there (perspective)
X2_SHIFT = 0.015               # ring centre shift along local +y (lower-right)
X2_AXIAL = 0.03                # ring centre shift along local +x (toward the upper-right tip, which sits in the crescent band)

GAP = 0.040                    # weave gap (background) each side of the over ring
SPLIT = X1_SHIFT               # x1 local y that separates the thick (near) side from the hairline (far) side

INK = "#111111"
LIGHT = "#F3E7C3"


# ------------------------------------------------------------------ helpers
def f(v):
    s = f"{v:.2f}"
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return "0" if s == "-0" else s


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def ellipse_path(cx, cy, rx, ry, sweep=1, deg=0.0):
    """closed ellipse as two arcs, optionally turned by deg about its centre."""
    dx, dy = rot(rx, 0, deg)
    return (f"M{f(cx - dx)} {f(cy - dy)} "
            f"A{f(rx)} {f(ry)} {f(deg)} 1 {sweep} {f(cx + dx)} {f(cy + dy)} "
            f"A{f(rx)} {f(ry)} {f(deg)} 1 {sweep} {f(cx - dx)} {f(cy - dy)} Z")


# ------------------------------------------------------------------ crescent outline
def crescent_horn():
    """angle t (0<t<pi, y-up) on the outer unit circle where it meets the inner ellipse."""
    def g(t):
        x, y = math.cos(t), math.sin(t)
        return ((x + D) / A2) ** 2 + (y / B2) ** 2 - 1.0
    lo, hi = 0.05, math.pi - 0.05       # g(lo) > 0 (outside inner ellipse), g(hi) < 0 (inside)
    assert g(lo) > 0 > g(hi), (g(lo), g(hi))
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if g(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


T_HORN = crescent_horn()
# horns in local coords (y down in SVG, so flip y): upper horn at (cos t, -sin t)
HU = (math.cos(T_HORN), -math.sin(T_HORN))
HL = (math.cos(T_HORN), math.sin(T_HORN))
# outer arc: upper horn -> through the right -> lower horn, clockwise on screen (sweep 1).
# span = 2*T_HORN in the y-up sense; large-arc if that exceeds pi.
LARGE_O = 1 if 2 * T_HORN > math.pi else 0
# inner arc back from lower horn to upper horn along the inner ellipse (counter-clockwise on screen).
# inner ellipse centre at (-D, 0); the arc goes through the right side again.
u_l = math.atan2(HL[1] / B2, (HL[0] + D) / A2)        # param of lower horn on inner ellipse (y down)
span_in = 2 * abs(u_l)
LARGE_I = 1 if span_in > math.pi else 0
CRES_LOCAL = (f"M{f(HU[0]*R)} {f(HU[1]*R)} "
              f"A{f(R)} {f(R)} 0 {LARGE_O} 1 {f(HL[0]*R)} {f(HL[1]*R)} "
              f"A{f(A2*R)} {f(B2*R)} 0 {LARGE_I} 0 {f(HU[0]*R)} {f(HU[1]*R)} Z")


def crescent_thickness(deg):
    """band thickness along the ray at angle deg (y-up, local frame)."""
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    qa = (c / A2) ** 2 + (s / B2) ** 2
    qb = 2 * c * D / A2 ** 2
    qc = (D / A2) ** 2 - 1
    disc = qb * qb - 4 * qa * qc
    if disc < 0:
        return 1.0
    r_in = (-qb + math.sqrt(disc)) / (2 * qa)
    return max(0.0, 1.0 - r_in)


# ------------------------------------------------------------------ ring outlines (local)
def ring_path(a, b, ai, bi, e, shift, lens_deg=0.0):
    """outer ellipse minus inner ellipse offset by e along local +y and turned by lens_deg (evenodd)."""
    return (ellipse_path(0, shift, a * R, b * R, 1) + " " +
            ellipse_path(0, shift + e * R, ai * R, bi * R, 0, lens_deg))


def ring_check(a, b, ai, bi, e, deg=0.0):
    """min clearance of the inner ellipse inside the outer one (R units) - must be > 0."""
    worst = 9
    for k in range(720):
        t = 2 * math.pi * k / 720
        x, y = rot(ai * math.cos(t), bi * math.sin(t), deg)
        y += e
        # radial scale factor to the outer ellipse
        s = 1 / math.sqrt((x / a) ** 2 + (y / b) ** 2) if (x or y) else 9
        worst = min(worst, (s - 1) * math.hypot(x, y))
    return worst


def smooth_path(pts, closed=True):
    """Catmull-Rom style cubic Bezier through the points (local coords, px)."""
    n = len(pts)
    out = [f"M{f(pts[0][0])} {f(pts[0][1])}"]
    for i in range(n if closed else n - 1):
        p0 = pts[(i - 1) % n]; p1 = pts[i]; p2 = pts[(i + 1) % n]; p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}")
    return " ".join(out) + (" Z" if closed else "")


def bend(x, y):
    """x1's local frame warp: a shallow parabolic bend (tips move toward local +y) plus an
    S-sway that vanishes at the centre and the tips."""
    t = x / (L1A * R)
    return x, y + R * (X1_BEND * t * t + (X1_SWAY * t + X1_SWAY2 * t * t) * (1 - t * t))


def x1_width(th):
    """stroke width (R units) at lens parameter th: thick side is sin>0 (local +y)."""
    s_ = math.sin(th)
    g = lambda v: 2 * v - v * v          # g(0)=0, g(1)=1, finite slope at 0
    if s_ >= 0:
        # cos(th) > 0 is the lower-right tip: lighter there, heavier toward the upper-left
        return W1_TIP + (W1_THICK - W1_TIP) * g(s_) * (1 - W1_TAPER * max(0.0, math.cos(th)))
    return W1_TIP + (W1_THIN - W1_TIP) * s_ * s_


def x1_outline():
    """outer boundary = lens + w(th) * outward normal; inner boundary = lens.  Both bent."""
    a, b = L1A * R, L1B * R
    outer, inner = [], []
    for k in range(96):
        th = 2 * math.pi * k / 96
        px, py = a * math.cos(th), X1_SHIFT * R + b * math.sin(th)
        nx, ny = b * math.cos(th), a * math.sin(th)
        nl = math.hypot(nx, ny); nx, ny = nx / nl, ny / nl
        w = x1_width(th) * R
        outer.append(bend(px + w * nx, py + w * ny))
        if k % 2 == 0:
            inner.append(bend(px, py))
    inner.reverse()                      # opposite winding -> hole with evenodd
    return smooth_path(outer) + " " + smooth_path(inner)


X1_PATH = x1_outline()
X2_PATH = ring_path(A2x, B2x, A2xi, B2xi, E2, X2_SHIFT * R, X2_LENS_ROT)     # thin edge at local +y


# ------------------------------------------------------------------ placement
def ring_bbox(a, b, shift, tilt, centre, axial=0.0):
    xs, ys = [], []
    for k in range(360):
        t = 2 * math.pi * k / 360
        x, y = axial * R + a * R * math.cos(t), shift * R + b * R * math.sin(t)
        gx, gy = rot(x, y, tilt)
        xs.append(centre[0] + gx)
        ys.append(centre[1] + gy)
    return min(xs), min(ys), max(xs), max(ys)


def crescent_bbox(centre):
    xs, ys = [], []
    for k in range(720):
        t = 2 * math.pi * k / 720
        if abs(t) <= T_HORN or abs(t - 2 * math.pi) <= T_HORN:
            x, y = R * math.cos(t), -R * math.sin(t)
            gx, gy = rot(x, y, CRES_ROT)
            xs.append(centre[0] + gx)
            ys.append(centre[1] + gy)
    return min(xs), min(ys), max(xs), max(ys)


def x1_bbox(centre):
    xs, ys = [], []
    a, b = L1A * R, L1B * R
    for k in range(360):
        th = 2 * math.pi * k / 360
        px, py = a * math.cos(th), X1_SHIFT * R + b * math.sin(th)
        nx, ny = b * math.cos(th), a * math.sin(th)
        nl = math.hypot(nx, ny)
        w = x1_width(th) * R
        x, y = bend(px + w * nx / nl, py + w * ny / nl)
        gx, gy = rot(x, y, X1_TILT)
        xs.append(centre[0] + gx); ys.append(centre[1] + gy)
    return min(xs), min(ys), max(xs), max(ys)


def union_bbox(c):
    xc = (c[0] + XC[0] * R, c[1] + XC[1] * R)
    bb = [crescent_bbox(c), x1_bbox(xc), ring_bbox(A2x, B2x, X2_SHIFT, X2_TILT, xc, X2_AXIAL)]
    return (min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb))


_bb = union_bbox((0.0, 0.0))
CX = round(256.0 - 0.5 * (_bb[0] + _bb[2]), 2)
CY = round(256.0 - 0.5 * (_bb[1] + _bb[3]), 2)
BBOX = (_bb[0] + CX, _bb[1] + CY, _bb[2] + CX, _bb[3] + CY)
XCX, XCY = CX + XC[0] * R, CY + XC[1] * R

TR_C = f"translate({f(CX)} {f(CY)}) rotate({f(CRES_ROT)})"
TR_X1 = f"translate({f(XCX)} {f(XCY)}) rotate({f(X1_TILT)})"
TR_X2 = f"translate({f(XCX)} {f(XCY)}) rotate({f(X2_TILT)}) translate({f(X2_AXIAL*R)} 0)"


def tip_radius(a, shift, tilt, sign, bent=False, axial=0.0):
    """distance of a ring tip from the crescent centre (R units) and its angle (deg, y-up)."""
    x, y = axial * R + sign * a * R, shift * R
    if bent:
        x, y = bend(x, y)
    gx, gy = rot(x, y, tilt)
    px, py = XCX + gx - CX, XCY + gy - CY
    return math.hypot(px, py) / R, math.degrees(math.atan2(-py, px))


# ------------------------------------------------------------------ SVG
def svg(ink, title, overlay=False):
    g = GAP * R
    big = 2000
    # half-planes in x1's local frame: near (thick) side = local y >= SPLIT*R
    # the split line y = SPLIT (local) warped like the ring, as a polyline; closed far below / far above
    seam = [bend(x, SPLIT * R) for x in range(-int(1.3 * R), int(1.3 * R) + 1, 8)]
    seam_d = " L".join(f"{f(x)} {f(y)}" for x, y in seam)
    near_rect = f'<path d="M{f(-big)} {f(seam[0][1])} L{seam_d} L{f(big)} {f(seam[-1][1])} L{f(big)} {f(big)} L{f(-big)} {f(big)} Z" transform="{TR_X1}"/>'
    far_rect = f'<path d="M{f(-big)} {f(seam[0][1])} L{seam_d} L{f(big)} {f(seam[-1][1])} L{f(big)} {f(-big)} L{f(-big)} {f(-big)} Z" transform="{TR_X1}"/>'
    opacity = ' fill-opacity="0.55"' if overlay else ''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="Crescent X mark">
  <title>{title}</title>
  <!--
    CRESCENT X - construction C.  Three variable-width strokes drawn as outlines.
    ring-crescent: circle R={f(R)} minus an inner ellipse ({f(A2*R)} x {f(B2*R)}) pushed {f(D*R)} toward the mouth
                   (two arcs; the band thins to sharp horns at {f(math.degrees(T_HORN)-CRES_ROT)} / {f(-(math.degrees(T_HORN)+CRES_ROT))} deg).
    ring-x1: descending ring, +{f(X1_TILT)} deg.  A slim lens ellipse ({f(L1A*R)} x {f(L1B*R)}) offset outward by a smooth
             width function: {f(W1_THICK*R)} on the lower-left edge, fading to a {f(W1_THIN*R)} hairline on the upper-right
             edge, {f(W1_TIP*R)} at the tips; with a shallow bend and sway so the heavy band runs through the X
             centre (cubic Bezier outline generated by gen_mark.py).
    ring-x2: ascending ring, {f(X2_TILT)} deg.  Outer ellipse ({f(A2x*R)} x {f(B2x*R)}) minus a lens ({f(A2xi*R)} x {f(B2xi*R)})
             offset {f(E2*R)} toward the lower-right edge and turned {f(X2_LENS_ROT)} deg (four arcs, evenodd).
    Weave gaps are background strokes ({f(2*g)} wide, i.e. {f(g)} each side) applied as masks:
      crescent  <- under x1 and x2 (tips at lower-right / upper-right)
      x2        <- under x1's thick band (centre)
      x1        <- its hairline far edge passes under x2 (x2 threads through x1)
    Recolour: change the fill on #mark.
  -->
  <defs>
    <path id="shape-crescent" d="{CRES_LOCAL}" transform="{TR_C}"/>
    <path id="shape-x1" fill-rule="evenodd" d="{X1_PATH}" transform="{TR_X1}"/>
    <path id="shape-x2" fill-rule="evenodd" d="{X2_PATH}" transform="{TR_X2}"/>
    <clipPath id="x1-near">{near_rect}</clipPath>
    <clipPath id="x1-far">{far_rect}</clipPath>
    <mask id="cut-crescent" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <g fill="#000" stroke="#000" stroke-width="{f(2*g)}" stroke-linejoin="round">
        <use href="#shape-x1"/>
        <use href="#shape-x2"/>
      </g>
    </mask>
    <mask id="cut-x2" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <g clip-path="url(#x1-near)" fill="#000" stroke="#000" stroke-width="{f(2*g)}">
        <use href="#shape-x1"/>
      </g>
    </mask>
    <mask id="cut-x1" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <g clip-path="url(#x1-far)" fill="#000" stroke="#000" stroke-width="{f(2*g)}">
        <use href="#shape-x2"/>
      </g>
    </mask>
  </defs>
  <g id="mark" fill="{ink}"{opacity}>
    <use id="ring-crescent" href="#shape-crescent" mask="url(#cut-crescent)"/>
    <use id="ring-x2" href="#shape-x2" mask="url(#cut-x2)"/>
    <use id="ring-x1" href="#shape-x1" mask="url(#cut-x1)"/>
  </g>
</svg>
'''


# ------------------------------------------------------------------ preview pages
# reference: mark spans x 220..981 of a 1170 px image (65.0 %); ours spans the bbox of 512.
REF_MARK_FRAC = (981 - 220) / 1170.0
MARK_W = 262.0                                     # on-screen width of the mark in both panels


def preview():
    ref_w = MARK_W / REF_MARK_FRAC
    ref_h = ref_w * 1191 / 1170
    our_w = MARK_W / ((BBOX[2] - BBOX[0]) / 512.0)
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Crescent X - C review</title>
<style>
  html,body{{margin:0;padding:0;background:#fff}}
  body{{width:1200px;height:673px;display:flex;gap:14px;padding:12px;box-sizing:border-box;font:11px/1.3 system-ui,sans-serif;color:#666}}
  .col{{display:flex;flex-direction:column;align-items:center;gap:6px}}
  .ref img{{display:block;width:{f(ref_w)}px;height:{f(ref_h)}px}}
  .ours{{width:{f(our_w + 20)}px}}
  .ours .big{{width:{f(our_w)}px;height:{f(our_w)}px;display:block;margin-top:{f((ref_h - our_w)/2 - 60)}px}}
  .dark{{background:#0d0e13;color:#889;padding:14px;border-radius:4px;width:420px;height:620px;box-sizing:border-box}}
  .row{{display:flex;gap:22px;align-items:flex-end;margin-top:14px}}
  .row div{{display:flex;flex-direction:column;align-items:center;gap:4px}}
  img{{display:block}}
</style></head><body>
<div class="col ref">
  <img src="file://{REF}">
  <span>reference (approved)</span>
</div>
<div class="col ours">
  <img class="big" src="mark.svg">
  <span>C - mark.svg on white, same mark width</span>
  <div class="row">
    <div><img src="mark.svg" width="40" height="40"><span>40</span></div>
    <div><img src="mark.svg" width="24" height="24"><span>24</span></div>
    <div><img src="mark.svg" width="96" height="96"><span>96</span></div>
  </div>
</div>
<div class="col dark">
  <img src="mark-light.svg" width="392" height="392">
  <span>mark-light.svg on #0d0e13</span>
  <div class="row">
    <div><img src="mark-light.svg" width="40" height="40"><span>40</span></div>
    <div><img src="mark-light.svg" width="24" height="24"><span>24</span></div>
    <div><img src="mark-light.svg" width="64" height="64"><span>64</span></div>
  </div>
</div>
</body></html>
'''


def overlay_html():
    """our mark (red, translucent) over the reference, circles registered."""
    s = R / 370.5
    ref_w = 1170 * s
    left = CX - 611.2 * s
    top = CY - 530.2 * s
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>overlay</title>
<style>html,body{{margin:0;background:#fff}}
.wrap{{position:relative;width:512px;height:512px;overflow:hidden;transform:scale(1.3);transform-origin:0 0}}
.wrap img{{position:absolute;display:block}}</style></head><body>
<div class="wrap">
  <img src="file://{REF}" style="left:{f(left)}px;top:{f(top)}px;width:{f(ref_w)}px;opacity:0.45">
  <img src="overlay.svg" style="left:0;top:0;width:512px;height:512px">
</div></body></html>
'''


def main():
    with open(os.path.join(HERE, "mark.svg"), "w") as fh:
        fh.write(svg(INK, "Crescent X mark - construction C"))
    with open(os.path.join(HERE, "mark-light.svg"), "w") as fh:
        fh.write(svg(LIGHT, "Crescent X mark - construction C, light"))
    with open(os.path.join(HERE, "preview.html"), "w") as fh:
        fh.write(preview())
    with open(os.path.join(HERE, "overlay.svg"), "w") as fh:
        fh.write(svg("#d02020", "overlay", overlay=True))
    with open(os.path.join(HERE, "overlay.html"), "w") as fh:
        fh.write(overlay_html())
    print(f"horn angle {math.degrees(T_HORN):.1f} deg (y-up), rotated -> {math.degrees(T_HORN)-CRES_ROT:.1f} / {-(math.degrees(T_HORN)+CRES_ROT):.1f}")
    print("crescent thickness (R):", {d: round(crescent_thickness(d), 3) for d in (0, 30, 45, 60, 90, 120, -45, -60, -90, -120)})
    print(f"x1 stroke: thick {W1_THICK} thin {W1_THIN} tip {W1_TIP}; lens {L1A}x{L1B}; band centreline at centre = {X1_SHIFT + L1B + W1_THICK/2:+.3f}R from the X centre")
    print(f"x2 inner clearance {ring_check(A2x, B2x, A2xi, B2xi, E2, X2_LENS_ROT):.3f}R  thick {B2x-B2xi+E2:.3f} thin {B2x-B2xi-E2:.3f} tip {A2x-A2xi:.3f}")
    for name, a, sh, tilt, bent, ax in (("x1", A1, X1_SHIFT, X1_TILT, True, 0.0), ("x2", A2x, X2_SHIFT, X2_TILT, False, X2_AXIAL)):
        for sign, lab in ((1, "right"), (-1, "left")):
            r, ang = tip_radius(a, sh, tilt, sign, bent, ax)
            t = crescent_thickness(ang - CRES_ROT)
            print(f"{name} {lab} tip: r={r:.3f}R at {ang:.1f} deg; crescent band there spans {1-t:.3f}..1.000 (t={t:.3f})")
    print(f"centre ({CX},{CY}); X centre ({XCX:.1f},{XCY:.1f}); bbox {tuple(round(v,1) for v in BBOX)}; gap {GAP*R:.1f}px")


if __name__ == "__main__":
    main()
