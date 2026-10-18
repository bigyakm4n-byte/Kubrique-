#!/usr/bin/env python3
"""
KUBRIQUE orbital mark - construction B: hand-drawn ellipses with a clipped weave.

Geometry (all plain python, no numpy)
  ring-crescent : region between an outer ellipse (A1,B1) centred on the mark
                  centre and an inner ellipse (A2,B2) shifted by D toward the
                  opening direction PHI.  Band is widest opposite the opening and
                  tapers to two horns.  The whole crescent is rotated by PHI so
                  the mouth faces up-right (a tilted orbital ring).
  ring-x1       : lens = ellipse (L x S), axis at +42 deg  (upper-left -> lower-right)
  ring-x2       : lens = ellipse (L x S), axis at -42 deg  (lower-left -> upper-right)

Weave (cyclic, like three gimbal rings)
  P0  centre       : x1 OVER x2
  P1  upper-left   : crescent OVER x1
  P2  lower-left   : x2 OVER crescent
  x1's lower-right arm and x2's upper-right arm pass through the crescent's mouth
  and cross nothing.

How the weave is drawn
  * crescent is split into BACK (global y >= Oy) and FRONT (y < Oy) segments with
    two half-plane clip rects.  The cut is the horizontal through the centre; a
    radial facet line sits exactly on the cut so the clip seam is invisible.
  * x2 is split into BACK (local x >= -75, centre + upper-right arm) and FRONT
    (local x < -75, the lower-left arm) with two clip rects rotated -42 deg.  A
    facet line sits on that cut too.
  * x1 is one segment.
  * stack, bottom to top:  glow, x2-back, crescent-back, x1, crescent-front,
    x2-front, seam facets, core.
  * each UNDER segment additionally gets a mask that carves a transparent GAP
    channel along the edges of the ring that passes over it, so the weave still
    reads when the glass is nearly opaque and in the one-colour version.

Run:  python3 gen_mark.py
Writes mark.svg, mark-mono-ink.svg, mark-mono-paper.svg, preview.html, detail.html
next to itself.
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ parameters
OX, OY = 256.0, 256.0        # provisional; re-centred from the bbox below

PHI = -15.0                  # crescent opening direction, degrees (y-down: negative = up-right)
A1, B1 = 168.0, 174.0        # outer ellipse, a along opening direction
A2, B2 = 162.0, 168.0        # inner ellipse
D = 46.0                     # inner ellipse offset along the opening direction

L, S = 200.0, 26.0           # lens semi-axes (400 x 52): tips must clear the crescent
ANG = 42.0                   # lens axis angle

RIM = 1.5                    # edge rim stroke
RIM2 = 1.0                   # second (inner) rim stroke
RIM_OFF = 4.5                # inner rim offset from the edge
GAP = 0.0                    # weave channel half-width (colour version: none, shadows instead)
SHADOW = "#07101F"           # shadow an over ring casts on the ring beneath it
GAP_MONO = 4.5               # weave channel half-width (one-colour version)
CUT_X2 = -75.0               # x2 front/back cut, local x
SEAM_OVERLAP = 0.8           # back segment overlaps front by this much (hides AA seam)
FACET_STEP = 25.0            # lens facet spacing
CRES_FACET_STEP = 12.0       # crescent facet spacing, degrees

GOLD = "#CDA044"             # brass: edge rims (reads on both #0d0e13 and #f5f1e8)
GOLD_DK = "#A87F33"          # darker brass: inner rims, facets
GOLD_HI = "#F6E3A8"          # rim highlight
GLOW_C = "#FFF4D2"
GLOW_E = "#F3C86E"


def f(v):
    s = f"{v:.2f}"
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return "0" if s == "-0" else s


def pt(x, y):
    return f"{f(x)} {f(y)}"


# ------------------------------------------------------------------ crescent maths
def ray_outer(psi):
    c, s = math.cos(psi), math.sin(psi)
    return 1.0 / math.sqrt((c / A1) ** 2 + (s / B1) ** 2)


def ray_inner(psi):
    """Far intersection of the ray from the origin at angle psi with the inner ellipse."""
    c, s = math.cos(psi), math.sin(psi)
    qa = (c / A2) ** 2 + (s / B2) ** 2
    qb = -2.0 * c * D / A2 ** 2
    qc = (D / A2) ** 2 - 1.0
    disc = qb * qb - 4 * qa * qc
    if disc < 0:
        return None
    return (-qb + math.sqrt(disc)) / (2 * qa)


def horn_param():
    """Parameter t on the outer ellipse where it meets the inner ellipse (0 < t < pi)."""
    def g(t):
        x, y = A1 * math.cos(t), B1 * math.sin(t)
        return ((x - D) / A2) ** 2 + (y / B2) ** 2 - 1.0
    lo, hi = 0.01, math.pi - 0.01
    assert g(lo) < 0 < g(hi)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if g(mid) < 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


TH = horn_param()
H1 = (A1 * math.cos(TH), B1 * math.sin(TH))      # lower horn (local y > 0)
H2 = (A1 * math.cos(TH), -B1 * math.sin(TH))     # upper horn
# outer arc H1 -> (through the left) -> H2 : clockwise, span 2pi-2TH
LARGE_O = 1 if (2 * math.pi - 2 * TH) > math.pi else 0
# inner arc H2 -> (through the left) -> H1 : counter-clockwise
U1 = math.atan2(H1[1] / B2, (H1[0] - D) / A2)
LARGE_I = 1 if (2 * math.pi - 2 * U1) > math.pi else 0
CRES_D = (f"M{pt(*H1)} A{f(A1)} {f(B1)} 0 {LARGE_O} 1 {pt(*H2)} "
          f"A{f(A2)} {f(B2)} 0 {LARGE_I} 0 {pt(*H1)} Z")


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def crescent_global(psi, t):
    x, y = t * math.cos(psi), t * math.sin(psi)
    gx, gy = rot(x, y, PHI)
    return OX + gx, OY + gy


# bbox check (relative to the centre), then re-centre the mark in the 512 box ----
def rel_bbox():
    xs, ys = [], []
    for k in range(720):
        t = 2 * math.pi * k / 720
        if TH <= t <= 2 * math.pi - TH:
            gx, gy = rot(A1 * math.cos(t), B1 * math.sin(t), PHI)
            xs.append(gx); ys.append(gy)
    for ang in (ANG, -ANG):
        for sgn in (1, -1):
            xs.append(sgn * L * math.cos(math.radians(ang)))
            ys.append(sgn * L * math.sin(math.radians(ang)))
    return min(xs), min(ys), max(xs), max(ys)


_bb = rel_bbox()
OX = round(256.0 - 0.5 * (_bb[0] + _bb[2]), 1)
OY = round(256.0 - 0.5 * (_bb[1] + _bb[3]), 1)
BBOX = (_bb[0] + OX, _bb[1] + OY, _bb[2] + OX, _bb[3] + OY)

# crossing centres (for the notes) ------------------------------------------
def crossing(theta_deg):
    psi = math.radians(theta_deg - PHI)
    ti, to = ray_inner(psi), ray_outer(psi)
    return crescent_global(psi, 0.5 * (ti + to)), (to - ti)


P1, W1 = crossing(180 + ANG)      # x1 upper-left arm
P2, W2 = crossing(180 - ANG)      # x2 lower-left arm

# ------------------------------------------------------------------ art pieces
def lens_facets(colour, opacity, width=1.0):
    out = []
    k = 1
    while k * FACET_STEP < L - 10:
        for x in (k * FACET_STEP, -k * FACET_STEP):
            h = S * math.sqrt(1 - (x / L) ** 2) - RIM_OFF - 1.0
            if h > 3:
                out.append(f'<line x1="{f(x)}" y1="{f(-h)}" x2="{f(x)}" y2="{f(h)}"/>')
        k += 1
    return (f'<g stroke="{colour}" stroke-width="{f(width)}" stroke-opacity="{opacity}" '
            f'stroke-linecap="round">\n      ' + "\n      ".join(out) + "\n    </g>")


def crescent_facets(colour, opacity, width=1.0):
    out = []
    seam = 180.0 - PHI  # local angle of the global horizontal cut
    for k in range(-20, 21):
        psi_deg = seam + k * CRES_FACET_STEP
        psi = math.radians(psi_deg)
        ti, to = ray_inner(psi), ray_outer(psi)
        if ti is None or to - ti < 9:
            continue
        a = ti + RIM_OFF + 1.0
        b = to - RIM_OFF - 1.0
        if b - a < 2:
            continue
        out.append(f'<line x1="{f(a*math.cos(psi))}" y1="{f(a*math.sin(psi))}" '
                   f'x2="{f(b*math.cos(psi))}" y2="{f(b*math.sin(psi))}"/>')
    return (f'<g stroke="{colour}" stroke-width="{f(width)}" stroke-opacity="{opacity}" '
            f'stroke-linecap="round">\n      ' + "\n      ".join(out) + "\n    </g>")


def seam_lines(colour, opacity, width):
    """The two facet lines that sit on the clip cuts, redrawn unclipped on top."""
    psi = math.radians(180.0 - PHI)
    ti, to = ray_inner(psi), ray_outer(psi)
    a, b = ti + RIM_OFF + 1.0, to - RIM_OFF - 1.0
    c1 = crescent_global(psi, a)
    c2 = crescent_global(psi, b)
    h = S * math.sqrt(1 - (CUT_X2 / L) ** 2) - RIM_OFF - 1.0
    x2a = rot(CUT_X2, -h, -ANG)
    x2b = rot(CUT_X2, h, -ANG)
    return (f'<g id="seam-facets" stroke="{colour}" stroke-width="{f(width)}" '
            f'stroke-opacity="{opacity}" stroke-linecap="round">\n'
            f'    <line x1="{f(c1[0])}" y1="{f(c1[1])}" x2="{f(c2[0])}" y2="{f(c2[1])}"/>\n'
            f'    <line x1="{f(OX+x2a[0])}" y1="{f(OY+x2a[1])}" x2="{f(OX+x2b[0])}" y2="{f(OY+x2b[1])}"/>\n'
            f'  </g>')


TR_C = f"translate({f(OX)} {f(OY)}) rotate({f(PHI)})"
TR_X1 = f"translate({f(OX)} {f(OY)}) rotate({f(ANG)})"
TR_X2 = f"translate({f(OX)} {f(OY)}) rotate({f(-ANG)})"


def shadow(over_href, over_tr, under_clip):
    """Crisp two-step shadow the OVER ring casts on the UNDER ring: strokes centred on the
    over ring's outline, clipped to the under ring's shape.  The half inside the over ring
    is hidden by the over ring itself, which is drawn later."""
    return (f'<g clip-path="url(#{under_clip})" fill="none" stroke="{SHADOW}" stroke-linejoin="round">'
            f'<use href="{over_href}" transform="{over_tr}" stroke-width="20" stroke-opacity="0.22"/>'
            f'<use href="{over_href}" transform="{over_tr}" stroke-width="9" stroke-opacity="0.40"/></g>')


def clip_defs():
    big = 900
    return f'''
    <!-- ring shapes in global coordinates, used to clip the shadows -->
    <clipPath id="g-crescent"><use href="#shape-crescent" transform="{TR_C}"/></clipPath>
    <clipPath id="g-x1"><use href="#shape-lens" transform="{TR_X1}"/></clipPath>
    <clipPath id="g-x2"><use href="#shape-lens" transform="{TR_X2}"/></clipPath>
    <!-- weave clips: half-planes.  The back rect overlaps the front by {f(SEAM_OVERLAP)}px. -->
    <clipPath id="clip-crescent-front"><rect x="0" y="0" width="512" height="{f(OY)}"/></clipPath>
    <clipPath id="clip-crescent-back"><rect x="0" y="{f(OY - SEAM_OVERLAP)}" width="512" height="{f(512 - OY + SEAM_OVERLAP)}"/></clipPath>
    <clipPath id="clip-x2-front"><rect x="{f(-big)}" y="{f(-big/2)}" width="{f(big + CUT_X2)}" height="{f(big)}" transform="{TR_X2}"/></clipPath>
    <clipPath id="clip-x2-back"><rect x="{f(CUT_X2 - SEAM_OVERLAP)}" y="{f(-big/2)}" width="{f(big - CUT_X2)}" height="{f(big)}" transform="{TR_X2}"/></clipPath>'''


def mask_defs(gap):
    sw = f(2 * gap)
    return f'''
    <!-- weave channels: each UNDER segment is masked by "everything except the OVER ring dilated by {f(gap)}px" -->
    <mask id="under-crescent" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use href="#shape-crescent" transform="{TR_C}" fill="#000" stroke="#000" stroke-width="{sw}" stroke-linejoin="round"/>
    </mask>
    <mask id="under-x1" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use href="#shape-lens" transform="{TR_X1}" fill="#000" stroke="#000" stroke-width="{sw}"/>
    </mask>
    <mask id="under-x2" maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
      <rect width="512" height="512" fill="#fff"/>
      <use href="#shape-lens" transform="{TR_X2}" fill="#000" stroke="#000" stroke-width="{sw}"/>
    </mask>'''


def stack(core, gap, shadows):
    m_x1 = ' mask="url(#under-x1)"' if gap > 0 else ''
    m_x2 = ' mask="url(#under-x2)"' if gap > 0 else ''
    m_c = ' mask="url(#under-crescent)"' if gap > 0 else ''
    sh_x1_on_x2 = ('\n    ' + shadow("#shape-lens", TR_X1, "g-x2")) if shadows else ''
    sh_x2_on_c = ('\n    ' + shadow("#shape-lens", TR_X2, "g-crescent")) if shadows else ''
    sh_c_on_x1 = ('\n    ' + shadow("#shape-crescent", TR_C, "g-x1")) if shadows else ''
    return f'''
  <!-- ======================= weave stack, bottom to top ======================= -->
  <!-- x2 BACK segment: centre + upper-right arm.  Under x1 at the centre (P0). -->
  <g id="ring-x2-back" clip-path="url(#clip-x2-back)"{m_x1}>
    <use href="#ring-x2"/>{sh_x1_on_x2}
  </g>
  <!-- crescent BACK segment: lower half.  Under x2 at the lower-left crossing (P2). -->
  <g id="ring-crescent-back" clip-path="url(#clip-crescent-back)"{m_x2}>
    <use href="#ring-crescent"/>{sh_x2_on_c}
  </g>
  <!-- x1: single segment.  Over x2 at the centre (P0), under the crescent at upper-left (P1). -->
  <g id="ring-x1-full"{m_c}>
    <use href="#ring-x1"/>{sh_c_on_x1}
  </g>
  <!-- crescent FRONT segment: upper half.  Over x1 at the upper-left crossing (P1). -->
  <g id="ring-crescent-front" clip-path="url(#clip-crescent-front)"><use href="#ring-crescent"/></g>
  <!-- x2 FRONT segment: lower-left arm.  Over the crescent at the lower-left crossing (P2). -->
  <g id="ring-x2-front" clip-path="url(#clip-x2-front)"><use href="#ring-x2"/></g>
{core}'''


# ------------------------------------------------------------------ colour SVG
def colour_svg():
    lens_art = f'''
    <g id="ring-x1" transform="{TR_X1}">
      <use href="#shape-lens" fill="url(#glass-lens)"/>
      <line x1="{f(-L*0.92)}" y1="0" x2="{f(L*0.92)}" y2="0" stroke="#FFFFFF" stroke-opacity="0.28" stroke-width="1"/>
      {lens_facets(GOLD_DK, 0.45)}
      <ellipse cx="0" cy="0" rx="{f(L-7)}" ry="{f(S-RIM_OFF)}" fill="none" stroke="{GOLD_DK}" stroke-width="{f(RIM2)}" stroke-opacity="0.8"/>
      <use href="#shape-lens" fill="none" stroke="{GOLD}" stroke-width="{f(RIM)}"/>
    </g>
    <g id="ring-x2" transform="{TR_X2}">
      <use href="#shape-lens" fill="url(#glass-lens)"/>
      <line x1="{f(-L*0.92)}" y1="0" x2="{f(L*0.92)}" y2="0" stroke="#FFFFFF" stroke-opacity="0.28" stroke-width="1"/>
      {lens_facets(GOLD_DK, 0.45)}
      <ellipse cx="0" cy="0" rx="{f(L-7)}" ry="{f(S-RIM_OFF)}" fill="none" stroke="{GOLD_DK}" stroke-width="{f(RIM2)}" stroke-opacity="0.8"/>
      <use href="#shape-lens" fill="none" stroke="{GOLD}" stroke-width="{f(RIM)}"/>
    </g>
    <g id="ring-crescent" transform="{TR_C}">
      <use href="#shape-crescent" fill="url(#glass-crescent)"/>
      {crescent_facets(GOLD_DK, 0.45)}
      <g clip-path="url(#band-crescent)" fill="none" stroke="{GOLD_DK}" stroke-width="{f(RIM2)}" stroke-opacity="0.8">
        <ellipse cx="0" cy="0" rx="{f(A1-RIM_OFF)}" ry="{f(B1-RIM_OFF)}"/>
        <ellipse cx="{f(D)}" cy="0" rx="{f(A2+RIM_OFF)}" ry="{f(B2+RIM_OFF)}"/>
      </g>
      <use href="#shape-crescent" fill="none" stroke="{GOLD}" stroke-width="{f(RIM)}" stroke-linejoin="round"/>
    </g>'''

    core = f'''  <!-- luminous core: the bulb / star / engine -->
  <g id="core">
    <circle cx="{f(OX)}" cy="{f(OY)}" r="7" fill="#FFF9E8" stroke="{GOLD}" stroke-width="1.5"/>
    <circle cx="{f(OX-1.5)}" cy="{f(OY-1.5)}" r="2.2" fill="#FFFFFF"/>
  </g>
{seam_lines(GOLD_DK, 0.75, 1.2)}'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="Kubrique mark: a crescent and an X made of three interlocking orbital rings">
  <title>Kubrique orbital mark - construction B</title>
  <!--
    Three orbital rings: ring-crescent (face-on, tilted {f(-PHI)} deg, mouth up-right),
    ring-x1 (+{f(ANG)} deg lens) and ring-x2 (-{f(ANG)} deg lens).
    Weave: x1 over x2 at the centre; crescent over x1 at upper-left (P1 ~ {f(P1[0])},{f(P1[1])});
    x2 over crescent at lower-left (P2 ~ {f(P2[0])},{f(P2[1])}).
    Segments: ring-crescent-back / -front, ring-x2-back / -front, ring-x1-full (see comments below).
    Each ring's artwork lives once in <defs> (ids ring-crescent, ring-x1, ring-x2) and is instanced
    with <use>; animate those three groups to turn the rings.
  -->
  <defs>
    <!-- base shapes, local coordinates (centre 0,0) -->
    <ellipse id="shape-lens" cx="0" cy="0" rx="{f(L)}" ry="{f(S)}"/>
    <path id="shape-crescent" d="{CRES_D}"/>
    <clipPath id="band-crescent"><use href="#shape-crescent"/></clipPath>

    <!-- glass: translucent, cool, lit from the upper edge -->
    <linearGradient id="glass-lens" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0"    stop-color="#2A4461" stop-opacity="0.94"/>
      <stop offset="0.16" stop-color="#7393B4" stop-opacity="0.9"/>
      <stop offset="0.36" stop-color="#D9E6F2" stop-opacity="0.9"/>
      <stop offset="0.55" stop-color="#93AEC8" stop-opacity="0.9"/>
      <stop offset="0.80" stop-color="#547290" stop-opacity="0.9"/>
      <stop offset="1"    stop-color="#243A52" stop-opacity="0.94"/>
    </linearGradient>
    <radialGradient id="glass-crescent" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="{f(A1)}" gradientTransform="scale(1 {f(B1/A1)})">
      <stop offset="0.66" stop-color="#243A52" stop-opacity="0.94"/>
      <stop offset="0.76" stop-color="#547290" stop-opacity="0.9"/>
      <stop offset="0.86" stop-color="#93AEC8" stop-opacity="0.9"/>
      <stop offset="0.93" stop-color="#D9E6F2" stop-opacity="0.9"/>
      <stop offset="0.975" stop-color="#7393B4" stop-opacity="0.9"/>
      <stop offset="1"    stop-color="#2A4461" stop-opacity="0.94"/>
    </radialGradient>
    <radialGradient id="glow" gradientUnits="userSpaceOnUse" cx="{f(OX)}" cy="{f(OY)}" r="60">
      <stop offset="0"   stop-color="{GLOW_C}" stop-opacity="0.95"/>
      <stop offset="0.3" stop-color="{GLOW_E}" stop-opacity="0.45"/>
      <stop offset="1"   stop-color="{GLOW_E}" stop-opacity="0"/>
    </radialGradient>
{clip_defs()}
{mask_defs(GAP) if GAP > 0 else ""}

    <!-- ring artwork, drawn once each -->{lens_art}
  </defs>

  <circle id="core-glow" cx="{f(OX)}" cy="{f(OY)}" r="60" fill="url(#glow)"/>
{stack(core, GAP, True)}
</svg>
'''


# ------------------------------------------------------------------ one-colour SVG
def mono_svg(ink):
    lens_art = f'''
    <g id="ring-x1" transform="{TR_X1}"><use href="#shape-lens" fill="{ink}"/></g>
    <g id="ring-x2" transform="{TR_X2}"><use href="#shape-lens" fill="{ink}"/></g>
    <g id="ring-crescent" transform="{TR_C}"><use href="#shape-crescent" fill="{ink}"/></g>'''
    core = f'''  <circle id="core" cx="{f(OX)}" cy="{f(OY)}" r="7" fill="none" stroke="{ink}" stroke-width="3"/>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="Kubrique mark, one colour">
  <title>Kubrique orbital mark - construction B, one colour</title>
  <defs>
    <ellipse id="shape-lens" cx="0" cy="0" rx="{f(L)}" ry="{f(S)}"/>
    <path id="shape-crescent" d="{CRES_D}"/>
{clip_defs()}
{mask_defs(GAP_MONO)}
{lens_art}
  </defs>
{stack(core, GAP_MONO, False)}
</svg>
'''


# ------------------------------------------------------------------ preview pages
PREVIEW = '''<!doctype html>
<html><head><meta charset="utf-8"><title>B preview</title>
<style>
  html,body{margin:0;padding:0}
  body{display:flex;width:1000px;height:560px;font:11px system-ui,sans-serif}
  .p{width:500px;height:560px;box-sizing:border-box;padding:16px 20px;display:flex;flex-direction:column;align-items:center}
  .dark{background:#0d0e13;color:#9aa}
  .light{background:#f5f1e8;color:#776}
  .row{display:flex;gap:18px;align-items:flex-end;margin-top:14px}
  .row div{display:flex;flex-direction:column;align-items:center;gap:4px}
  img{display:block}
</style></head><body>
<div class="p dark">
  <img src="mark.svg" width="420" height="420">
  <div class="row">
    <div><img src="mark.svg" width="40" height="40"><span>40</span></div>
    <div><img src="mark-mono-paper.svg" width="40" height="40"><span>40 mono</span></div>
    <div><img src="mark.svg" width="32" height="32"><span>32</span></div>
    <div><img src="mark-mono-paper.svg" width="32" height="32"><span>32 mono</span></div>
    <div><img src="mark-mono-paper.svg" width="64" height="64"><span>64 mono</span></div>
  </div>
</div>
<div class="p light">
  <img src="mark.svg" width="420" height="420">
  <div class="row">
    <div><img src="mark.svg" width="40" height="40"><span>40</span></div>
    <div><img src="mark-mono-ink.svg" width="40" height="40"><span>40 mono</span></div>
    <div><img src="mark.svg" width="32" height="32"><span>32</span></div>
    <div><img src="mark-mono-ink.svg" width="32" height="32"><span>32 mono</span></div>
    <div><img src="mark-mono-ink.svg" width="64" height="64"><span>64 mono</span></div>
  </div>
</div>
</body></html>
'''

DETAIL = '''<!doctype html>
<html><head><meta charset="utf-8"><title>B detail</title>
<style>html,body{margin:0;padding:0}body{display:flex;width:1200px;height:600px}
.d{width:600px;height:600px;display:flex;align-items:center;justify-content:center}
.dark{background:#0d0e13}.light{background:#f5f1e8}</style></head><body>
<div class="d dark"><img src="mark.svg" width="580" height="580"></div>
<div class="d light"><img src="mark.svg" width="580" height="580"></div>
</body></html>
'''


def main():
    with open(os.path.join(HERE, "mark.svg"), "w") as fh:
        fh.write(colour_svg())
    with open(os.path.join(HERE, "mark-mono-ink.svg"), "w") as fh:
        fh.write(mono_svg("#14171F"))
    with open(os.path.join(HERE, "mark-mono-paper.svg"), "w") as fh:
        fh.write(mono_svg("#F3EEE2"))
    with open(os.path.join(HERE, "preview.html"), "w") as fh:
        fh.write(PREVIEW)
    with open(os.path.join(HERE, "detail.html"), "w") as fh:
        fh.write(DETAIL)
    print(f"horn t = {math.degrees(TH):.1f} deg, horns at local {pt(*H1)} / {pt(*H2)}")
    print(f"band max width = {A1 - A2 + D:.1f}")
    print(f"P1 (crescent over x1) ~ {pt(*P1)}  band width along arm {W1:.1f}")
    print(f"P2 (x2 over crescent) ~ {pt(*P2)}  band width along arm {W2:.1f}")
    print(f"centre O = ({OX}, {OY});  bbox = {tuple(round(v,1) for v in BBOX)}")


if __name__ == "__main__":
    main()
