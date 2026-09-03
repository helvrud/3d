"""
Edit this file and save -> watcher.py auto re-runs it in the running
Blender instance.

Simplified redesign of ~/3d/perplexity/slidingpuzzle.scad:
  - coaxial_body(): two cones facing each other through a thin cylindrical
    neck (big cone base 12.5mm dia, small cone base 7mm dia, neck 3.5mm
    dia x 3.5mm long). The letter is engraved into the big cone's flat
    base face. No middle rib / end caps -- the plate is now thin (3.5mm,
    == neck length) so the neck alone captures the piece in the slot.
  - 11 tokens in a row spelling "PHYSCHEM.CZ".
  - a red board with a single main lane (all 11 tokens) plus two plain
    half-circle "tram siding" dead-ends at two different branch points,
    each parking a spare token. The two lanes are mirrored two ways:
      * side (+Y vs -Y): Lane A bulges toward +Y, Lane B toward -Y.
      * branch tangent (+X vs -X): Lane A starts tangent +X (matching
        the main lane's own direction of travel there); Lane B starts
        tangent -X. Both are collinear with the main lane, just
        pointing opposite ways, so both are equally smooth -- a
        horizontal tangent means the same Y-Z cross-section either way.
        It's only a *perpendicular* tangent (a T-junction) that
        misaligns cross-sections and breaches retention.
    Net effect: Lane A bulges right and faces back; Lane B bulges left
    and faces forward -- genuinely opposite tangents at both ends.
    Each lane is swept as ONE continuous, tangent-continuous path
    (never two independently-swept channels crossing at a hard angle).
    Verified via a static ray-cast check (Object.ray_cast against the
    finished board mesh, sampling the actual hole radius around each
    junction) rather than rigid-body physics -- Bullet's GImpact
    concave-dynamic collision (needed since the token's neck waist is
    genuinely non-convex) crashed Blender outright when tried. Both
    junctions measure the same retention margin -- arc_r (2.8*R_BIG)
    was pushed well past the first attempt (1.6, then 1.92*R_BIG) to
    get it from a thin 0.12mm/0.50mm up to a comfortable 0.70mm (vs.
    0.90mm on an undisturbed straight lane -- the theoretical max).
    build_board() derives the board's Y size FROM arc_r so there's
    always room for the full U-turn.
  - Every genuine dead end (both pocket tips, and both ends of the main
    lane itself) is capped with a dome (dome_taper: progressively
    scaled+shrunk copies of the channel's own cross-section) instead of
    a flat cut-off face. Branch points are never rounded this way --
    that would break the tangent continuity the retention margin
    depends on.
  - The board itself is a rounded-rectangle prism (build_rounded_box),
    not a plain cube -- all 4 corners filleted to a 6mm radius. Its
    footprint is computed from the actual bounding box of every channel
    path (centerline +/- the channel's own half-width) plus ONE even
    BORDER_MARGIN on all sides -- not separate, mismatched X/Y margin
    formulas (which used to leave a lot of dead space on one side and
    almost none on another).
  - channel_profile()'s small-cone zone (below the neck) tapers at
    exactly 45 degrees (H_SMALL == R_SMALL-NECK_R by construction) --
    the max angle printable without support, and, given that fixed
    height budget, the widest the bottom opening can safely be. No
    separate rim/lip to remove: nothing narrows there until the neck
    actually needs it to. Captivity never depended on the bottom's
    width anyway -- full removal either way is blocked by the SAME
    bottleneck, the neck-width hole at the plate's TOP surface.
  - set_units_to_mm() points the scene's unit display at millimeters
    (everything here is built as if 1 Blender unit == 1mm).
  - KNOWN UNRESOLVED ISSUE: a thorough ray-cast scan (many points along
    BOTH the main lane and each branch's arc, not just the branch
    center that earlier checks used) found that 5-20mm off each branch
    center, on the main lane, at diagonal angles, the union of the main
    lane's cut and the branch's cut opens up completely. A wide-radius
    re-scan (0.3 to 30mm, since two earlier attempts just hit a search
    cutoff without finding the real wall) found the TRUE gap size:
    up to 15.1mm at Junction B, x=38.8mm, 225 degrees -- genuinely huge
    relative to the token itself (R_BIG=4.75mm). Two fix attempts so
    far, both wrong:
      1. UNION the main lane's own tube back over its full length --
         subtracting a shape then unioning that same shape back
         cancels the subtraction outright (A - X + X = A), refilling
         the entire main lane solid, not just the excess. Reverted.
      2. Raise R_SMALL (widen the small cone, shorten NECK_LEN to
         compensate) -- helps the TOP surface (raises channel_profile's
         z_waist, less remaining plate height to widen back out) but
         widens r_bottom=R_SMALL+OF by the same amount, and the
         junction's worst point turned out to be governed by the
         BOTTOM of the plate, not the top -- margin went from -2.05mm
         to -4.89mm. Reverted. Given the confirmed 15.1mm gap, no
         viable R_SMALL increase can close it anyway (would need
         R_SMALL~14.75mm, far past R_BIG=4.75mm).
      3. Push arc_r from 2.8*R_BIG to 4.5*R_BIG (gentler divergence) --
         made it WORSE (15.1mm -> 19.3mm), not better: a gentler curve
         lowers peak severity at any one point but SPREADS the
         main-lane/branch overlap zone over more distance, and the
         wide-radius scan found the new worst point in that larger
         zone was bigger than the old peak. Board also grew
         substantially (Y: 87.6 -> 101.6mm) for no benefit. Reverted.
         arc_r is NOT a reliable lever in either direction -- every
         single-point check made it look consistently helpful, but a
         thorough wide-area scan says otherwise.
    Simple parameter tuning (R_SMALL, NECK_LEN, arc_r, PLATE_THICKNESS,
    R_BIG) never worked in either direction on any attempt -- confirmed
    AGAIN by a real print: tokens genuinely fall out at both junctions.
    Best pure tuning found (R_BIG=6mm, PLATE_THICKNESS=5mm, NECK_LEN=0.4,
    arc_r=1.15*R_BIG) only got the worst margin to -13.28mm.

    Follow-up investigation (same session) found the ROOT CAUSE precisely
    and confirmed it is NOT fixable by reshaping the branch's curve at
    all, single-radius or compound:
      - A constant-radius arc folds back on itself in X exactly halfway
        through its own sweep; two very-different-Y points of the tube
        share that X there, and since the tube's own width (~R_BIG+OF)
        is comparable to the Y-gap between them, they merge into one
        wide opening. See compound_arc_path()'s docstring. Building a
        proper two-radius compound arc (large r1 first to clear Y before
        r1's own fold) to avoid this fold-merge made things WORSE
        (-17.62mm), not better: a large r1 diverges in Y too slowly per
        mm of X, so it just spends longer "close but full width." A
        SMALL r1~r2 (~1.2x the channel's own half-width, the smallest
        that doesn't self-intersect) does about as well as the old
        single-arc tuning (-14.17mm) but no better.
      - The REAL mechanism (see clip_from_main_lane_collar()'s
        docstring): right after ANY branch starts, its own centerline
        has barely moved off main_y yet (Y grows ~quadratically from a
        tangent-horizontal start) while its tube must stay FULL WIDTH
        the whole way (the cone needs that clearance to physically
        slide through) -- so for a good ~10mm past every junction, the
        branch's own necessarily-full-width bore keeps reaching back
        across the main lane's own retention radius. This isn't excess
        material; the branch's tube at that width is genuinely minimal
        for passage. clip_from_main_lane_collar() (subtracting the
        region within R_SMALL of main_y from the branch cutter, outside
        a small handoff window at the junction itself) was built to
        test this directly, and the result is conclusive: a NARROW
        handoff window (~3mm) gets the worst retention margin to
        -1.75mm (only 15/1568 samples still breach, all small) -- real
        progress -- but the SAME narrow window that fixes retention also
        cuts the branch's own passage down to ~0.06mm where the cone
        needs 4.38mm to physically pass. Widening the window enough to
        restore passage (~10-13mm) undoes almost the entire retention
        fix (back to ~-14mm). Every handoff_window value tested trades
        one requirement directly for the other; none satisfies both.
        clip_from_main_lane_collar() is left DEFINED but NOT applied
        (see the `and False` guard in build_board()'s cutters loop) --
        applying it with a small window is a genuine partial fix if a
        different passage mechanism is ever adopted for the branches.

    CONCLUSION: full cone-clearance passage into a branch and vertical
    lift-retention right there are in direct physical conflict at the
    same (x, y) location, for THIS token/channel design (a rigid
    two-cone token needing its full base radius to slide horizontally,
    retained only by a channel narrowing at one Z-band). No channel
    reshaping or subtractive patch fixes this; it needs either a
    different retention mechanism (not solely a channel collar -- e.g.
    a discrete catch/detent only at parking spots, not continuous along
    the travel path) or accepting the tokens can be lifted out right at
    the branches (contradicts "print-in-place, non-disassemblable").
"""

import bpy
import bmesh
import math
import mathutils

COLLECTION_NAME = "Scripted"
TEST_RIGHT_ANGLE_BRANCH = False  # TESTED: a 90-degree T-junction branch gives a
                                  # similarly-severe breach (-14.00mm) to the
                                  # tangent-matched curve (-14.17mm), just
                                  # concentrated at a single point (X=branch_x,
                                  # ALL z equally bad) instead of spread over
                                  # ~10mm -- not an improvement, and a hard
                                  # 90-degree corner is also a real concern for
                                  # a rigid token actually navigating the turn
                                  # (separate from retention). Left as an
                                  # option (set True to rebuild) but not used.

# ---- Parameters ----
# Shrinks the whole model to a more souvenir-friendly size (board was
# 158mm wide at scale 1.0). OF and EPS are PRINT TOLERANCES, not
# geometry -- deliberately left UNSCALED below so clearances don't get
# printed-unreliably thin; only the bulk/structural dimensions shrink.
# PLATE_THICKNESS and NECK_LEN are ALSO left unscaled (see below) --
# both fixed, absolute mm values now, not proportional to MODEL_SCALE.
MODEL_SCALE = 0.76

R_BIG = 5.0   # top cone's own capped/max radius (10mm dia), shrunk down
              # further per direct request so the tokens fit the board.
              # Still the taper TARGET radius (H_BIG = R_BIG - NECK_R,
              # same 45-degree-taper convention as everywhere else). The
              # row spacing pitch (2*R_BIG+OF) derives from this same
              # constant, so tokens automatically sit closer together too.
R_SMALL = 4.749067164179104   # bottom cone radius, left at its scaled-down
                               # 120mm-board value -- only the top cone
                               # was asked to grow.
NECK_R = 1.75 * MODEL_SCALE     # neck radius (3.5mm dia) -- kept at full,
                                 # un-scaled-down size, unlike R_BIG/R_SMALL.

PLATE_THICKNESS = 5.51   # tuned so the board+logo-bump bounding box comes
                        # out to a round 6.0mm total (LOGO_DEPTH=0.5 sits
                        # on top of this), per direct request for round
                        # board dimensions. Independent of NECK_LEN (was
                        # tied to NECK_LEN earlier when the channel matched
                        # the token's own profile exactly; no longer
                        # applies now that the channel is a fixed two-cone
                        # shape).

NECK_LEN = 0.0   # neck fully removed per direct request -- token_profile()
                  # was rewritten to a single-point waist (matching
                  # channel_profile()'s own single-point waist exactly),
                  # so this no longer feeds a degenerate zero-length
                  # fillet segment; it now only sizes TOTAL_HEIGHT, where
                  # 0.0 is exactly correct (no flat shaft to add). Fixed
                  # absolute value, not scaled by MODEL_SCALE.
H_SMALL = R_SMALL - NECK_R   # 45-degree taper: height = radius drop
H_BIG = R_BIG - NECK_R       # 45-degree taper: height = radius drop

TOP_TIERS = [(R_BIG, 0.8)]   # single straight-walled cylindrical band, all
    # at R_BIG's own radius (10mm dia) -- "several layers" meant one
    # consistent radius, not a stepped-down stack, purely so the
    # cone-to-flat-top transition is a rounded edge (via the fillet at
    # each end of this band) instead of a sharp point. 0.8mm tall so it
    # prints as at least 3 layers even at a coarse 0.25-0.3mm layer
    # height (4 layers at the common 0.2mm). The top stays FLAT, with
    # the letter embossed on it.

TOTAL_HEIGHT = H_SMALL + NECK_LEN + H_BIG + sum(h for _, h in TOP_TIERS)
PLATE_Z_BOTTOM = 0.0   # flush with the small cone's base, for print-in-place
                       # (bed-facing) printing -- no floating gap under the plate

LETTER_DEPTH = 1.0 * MODEL_SCALE
OF = 0.2    # NOT scaled -- print clearance; raised back up slightly now that
            # the waist corner below is filleted (the fillet itself already
            # widens the tightest point beyond this nominal value)
B = 2.0 * MODEL_SCALE
EPS = 0.01  # NOT scaled -- tiny boolean-safety epsilon, unrelated to scale

# Shifts the whole token row (and the branch points, which stay locked to
# their respective tokens) to the right relative to the channel geometry
# (main lane extent, board footprint), WITHOUT moving the channel itself
# -- so it just widens Token_00's clearance from the board's left edge
# (was 4.7mm) without touching anything else. Right side had ~14.7mm to
# spare, so this comes out of that.
TOKEN_ROW_X_SHIFT = 5.0 * MODEL_SCALE
SEGMENTS = 48
FILLET_R = 0.5 * MODEL_SCALE   # rounds every sharp edge of the profile (cone/cap and cone/neck)
FILLET_SEGS = 6  # arc segments per rounded corner

LETTERS = ["P", "H", "Y", "S", "C", "H", "E", "M", ".", "C", "Z"]

LOGO_SVG_PATH = "/home/kvint/3d/perplexity/logo_monogram.svg"
LOGO_DEPTH = 0.5  # fixed absolute groove depth (like OF/EPS) -- NOT scaled by
                   # MODEL_SCALE. Everything in the SVG (monogram + ring) is cut
                   # to this same uniform depth, no separate backdrop disk anymore.
LOGO_DIAMETER = 38.0 * MODEL_SCALE  # sized so the ring (fixed ~1.7% of diameter from the
                                     # source art) clears a 0.4mm Prusa nozzle: measured
                                     # ~0.33mm ring width at the old 26x size, ~0.44mm here
LOGO_MARGIN = 4.0 * MODEL_SCALE  # gap from the logo's own edge to the board's border


def fillet_corner(p_prev, p_corner, p_next, radius, n=FILLET_SEGS):
    """Replace a sharp corner (p_prev -> p_corner -> p_next, all (z, r) points)
    with n+1 points tracing a tangent arc of the given radius -- the 2D
    equivalent of rounding the edge with a cylindrical cutter of that radius."""
    cz, cr = p_corner
    d1 = (p_prev[0] - cz, p_prev[1] - cr)
    d2 = (p_next[0] - cz, p_next[1] - cr)
    len1, len2 = math.hypot(*d1), math.hypot(*d2)
    d1n = (d1[0] / len1, d1[1] / len1)
    d2n = (d2[0] / len2, d2[1] / len2)

    dot = max(-1.0, min(1.0, d1n[0] * d2n[0] + d1n[1] * d2n[1]))
    theta = math.acos(dot)
    t = min(radius / math.tan(theta / 2), len1 * 0.95, len2 * 0.95)

    t1 = (cz + d1n[0] * t, cr + d1n[1] * t)
    t2 = (cz + d2n[0] * t, cr + d2n[1] * t)

    bis = (d1n[0] + d2n[0], d1n[1] + d2n[1])
    bis_len = math.hypot(*bis)
    bisn = (bis[0] / bis_len, bis[1] / bis_len)
    center_dist = t / math.cos(theta / 2)  # == radius / sin(theta/2)
    center = (cz + bisn[0] * center_dist, cr + bisn[1] * center_dist)

    a1 = math.atan2(t1[1] - center[1], t1[0] - center[0])
    a2 = math.atan2(t2[1] - center[1], t2[0] - center[0])
    diff = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi  # shortest signed turn

    r = math.hypot(t1[0] - center[0], t1[1] - center[1])
    pts = []
    for i in range(n + 1):
        a = a1 + diff * (i / n)
        pts.append((center[0] + r * math.cos(a), center[1] + r * math.sin(a)))
    return pts


def fillet_polyline(points, radius, virtual_before=None, virtual_after=None):
    """Round every interior corner of a (z, r) polyline with fillet_corner,
    generalizing the old one-call-per-known-corner style to an arbitrary
    number of corners (needed for TOP_TIERS' variable-length stack).
    virtual_before/virtual_after add one more neighbour so the very first
    /last real point gets filleted too (matching how the bottom/top caps
    were always filleted against their own virtual cap-center point)."""
    pts = list(points)
    if virtual_before is not None:
        pts = [virtual_before] + pts
    if virtual_after is not None:
        pts = pts + [virtual_after]
    out = []
    for i in range(1, len(pts) - 1):
        out += fillet_corner(pts[i - 1], pts[i], pts[i + 1], radius)
    return out


def token_profile():
    """(z, radius) points of the coaxial_body silhouette, bottom to top:
    small cone base -> single-point waist -> big cone base (capped at
    R_BIG, 11mm dia) -> TOP_TIERS' decorative stepped cylindrical layers,
    with every sharp transition replaced by a small filleted arc. The
    neck is fully removed (not just shortened) per direct request -- no
    flat NECK_R shaft, just the two cones meeting at one point, mirroring
    channel_profile()'s own single-point waist as closely as possible so
    the radial gap stays at the nominal OF everywhere, not OF+NECK_LEN
    near the top cone."""
    p_bottom = (0.0, R_SMALL)
    p_waist = (H_SMALL, NECK_R)
    p_top = (H_SMALL + H_BIG, R_BIG)

    corners = [p_bottom, p_waist, p_top]
    z, r = p_top
    for tier_r, tier_h in TOP_TIERS:
        if tier_r != r:
            corners.append((z, tier_r))   # flat shoulder, stepping the radius
        z += tier_h
        corners.append((z, tier_r))       # straight-walled cylindrical band
        r = tier_r

    virtual_before = (0.0, 0.0)   # bottom cap center
    virtual_after = (z, 0.0)      # top cap center (now above all tiers)

    return fillet_polyline(corners, FILLET_R, virtual_before, virtual_after)


def get_or_create_collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def clear_collection(coll):
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def link_only(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def build_revolve(name, profile, segments, location):
    bm = bmesh.new()
    rings = []
    for (z, r) in profile:
        ring = []
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            v = bm.verts.new((r * math.cos(theta), r * math.sin(theta), z))
            ring.append(v)
        rings.append(ring)

    for k in range(len(rings) - 1):
        ra, rb = rings[k], rings[k + 1]
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))

    bm.faces.new(reversed(rings[0]))
    bm.faces.new(rings[-1])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    return obj


def engrave_letter(body, letter, x0, y0, z0):
    if not letter:
        return

    engrave_depth = LETTER_DEPTH
    embed_depth = 0.3   # how far the letter's own volume reaches BELOW the
        # token's flat top face -- needs real 3D overlap, not just a
        # boolean-safety sliver: a thin ~0.01mm sliver against the top
        # cap's own big flat N-gon face is nearly coplanar, which made
        # Blender's exact boolean solver silently drop the letter
        # entirely (UNION applied with no error, but no bump in the
        # resulting mesh -- confirmed by checking the token's own max
        # vertex Z, which sat exactly at the flat top with no letter
        # sticking up at all). 0.3mm of genuine embedment fixes it.
    font_size = R_BIG * 2.4

    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.text_add(location=(0, 0, 0))
    txt = bpy.context.active_object
    txt.data.body = letter
    txt.data.font = bpy.data.fonts.load(
        "/usr/share/fonts/TTF/Comfortaa-Bold.ttf", check_existing=True)
    txt.data.size = font_size
    txt.data.align_x = 'CENTER'
    txt.data.align_y = 'CENTER'
    txt.data.extrude = (engrave_depth + embed_depth) / 2
    # Raised (embossed) letter, not a carved groove: the extruded-text
    # volume spans [TOTAL_HEIGHT-embed_depth, TOTAL_HEIGHT+engrave_depth]
    # -- genuinely embedded into the body, protruding engrave_depth above
    # its flat top face.
    txt.location = (x0, y0, z0 + TOTAL_HEIGHT + (engrave_depth - embed_depth) / 2)

    bpy.context.view_layer.objects.active = txt
    txt.select_set(True)
    bpy.ops.object.convert(target='MESH')

    # Blender's font-metric align_x/align_y='CENTER' centers on the font's
    # own advance-width/line metrics, not the glyph's actual ink -- for an
    # asymmetric shape like "C" that visibly lands off-center. Recompute
    # from the real converted-mesh bounding box and shift to compensate.
    xs = [v.co.x for v in txt.data.vertices]
    ys = [v.co.y for v in txt.data.vertices]
    if xs:
        txt.location.x -= (max(xs) + min(xs)) / 2
        txt.location.y -= (max(ys) + min(ys)) / 2

    mod = body.modifiers.new(name="EmbossLetter", type='BOOLEAN')
    mod.operation = 'UNION'
    mod.object = txt

    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=mod.name)

    bpy.data.objects.remove(txt, do_unlink=True)


def build_token(name, letter, x0, y0, z0=0.0):
    body = build_revolve(name, token_profile(), SEGMENTS, (x0, y0, z0))
    engrave_letter(body, letter, x0, y0, z0)
    return body


def channel_profile():
    """The channel's inner wall is two plain 45-degree cones meeting at a
    single waist point, with that ONE meeting point filleted -- every wall
    segment keeps the same 45-degree incline (the max angle printable
    without support) right up to the fillet's tangent points, so the slope
    itself is unchanged; only the sharp V at the very tip is rounded off.

    That waist corner is the profile's only concave vertex (both
    neighbours have a LARGER radius, so it's a valley, not a peak) --
    rounding a valley cuts the tip off and replaces it with an arc whose
    lowest point sits strictly above the original sharp corner, i.e. the
    fillet itself widens the tightest point of the channel beyond the
    nominal NECK_R+OF. The z_bottom/z_top corners are the opposite
    (convex peaks against their flat cap segments); filleting those would
    narrow the channel there instead, so they're left sharp.

    Still fully encloses the token: within the plate's own thickness
    (z=0..PLATE_THICKNESS-EPS), the token's radius tapers from R_SMALL
    down to NECK_R by z=H_SMALL and then stays AT NECK_R for the rest of
    the neck's span (the big cone doesn't start widening again until
    z=H_SMALL+NECK_LEN=5.25, well above the plate's own top z~3.49) --
    so the channel only needs to narrow to NECK_R+OF at the single z
    where it's tightest (z_waist=H_SMALL) and can be wider everywhere
    else in that span without ever exposing a gap the token could pass
    through. This also SHRINKS how much of the channel sits at minimum
    width (a point instead of the full NECK_LEN), which should reduce
    how much a crossing branch can widen it at a junction."""
    r_bottom = R_SMALL + OF
    r_waist = NECK_R + OF
    r_top = R_BIG + OF
    z_waist = H_SMALL
    z_bottom = z_waist - (r_bottom - r_waist)  # == 0, by construction
    z_top = z_waist + (r_top - r_waist)

    p_bottom = (z_bottom, r_bottom)
    p_waist = (z_waist, r_waist)
    p_top = (z_top, r_top)

    pts = [(z_bottom - OF, r_bottom), p_bottom]
    pts += fillet_corner(p_bottom, p_waist, p_top, FILLET_R)
    pts += [p_top, (z_top + OF, r_top)]
    return pts


def straight_path(p0, p1, n=2):
    """List of (x, y, tx, ty) samples along a straight segment, unit tangent."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    tx, ty = dx / length, dy / length
    return [(x0 + dx * i / (n - 1), y0 + dy * i / (n - 1), tx, ty) for i in range(n)]


def arc_path(center, radius, angle_start_deg, angle_end_deg, n=16):
    """List of (x, y, tx, ty) samples along a circular arc.

    Parameterized so the path starts tangent to angle_start_deg's direction
    and turns smoothly (no kink) into angle_end_deg's direction -- this is
    what keeps a branch tangent-continuous with whatever it grows out of."""
    cx, cy = center
    a0 = math.radians(angle_start_deg)
    a1 = math.radians(angle_end_deg)
    samples = []
    for i in range(n):
        t = i / (n - 1)
        a = a0 + (a1 - a0) * t
        rx = math.cos(a) * radius
        ry = math.sin(a) * radius
        x = cx + rx
        y = cy + ry
        # tangent = d/da (rx, ry) rotated by sign of sweep direction
        sign = 1.0 if a1 >= a0 else -1.0
        tx = -math.sin(a) * sign
        ty = math.cos(a) * sign
        samples.append((x, y, tx, ty))
    return samples


def compound_arc_path(start_x, start_y, start_tangent_deg, turn_deg,
                       r1, r2, split_frac=0.45, n1=20, n2=20):
    """Two-radius compound turn: covers `turn_deg` total (signed: positive
    = counterclockwise), starting at (start_x, start_y) tangent to
    start_tangent_deg. The first split_frac of the turn uses radius r1,
    the rest uses r2, joined tangent-continuously.

    Why two radii: ANY constant-radius circular turn folds back on itself
    in X exactly halfway through its own sweep (the point where the
    tangent turns perpendicular to the start direction). At that fold,
    two very-different-Y points of the swept tube land at the SAME X --
    and since the tube's own width (~R_BIG+OF, several mm) is comparable
    to the Y-gap between those two points there, they merge into one
    much wider opening than either point's own local width. This was
    confirmed both by the validated ray-cast retention scan (a real
    breach, matching a live 3D print failure) and by the underlying
    geometry: Y-gap at a shared-X pair = 2*r*sin(alpha), which -> 0 as
    the fold point (alpha=0) is approached, for ANY r -- so no single
    radius can avoid it. Using a LARGE r1 for roughly the first half of
    the turn (so the tube's own Y-displacement is already safely past
    the main lane's own half-width by the time r1's fold would occur)
    keeps that fold far from the danger zone; r2 for the remainder can
    be smaller, since by then the path is already far enough from the
    main lane's own Y that ITS fold no longer threatens main-lane
    retention (only self-retention on the branch itself, not addressed
    here)."""
    turn1 = turn_deg * split_frac
    turn2 = turn_deg - turn1

    t0 = math.radians(start_tangent_deg)
    tx0, ty0 = math.cos(t0), math.sin(t0)
    if turn1 >= 0:
        c1x, c1y = start_x + r1 * (-ty0), start_y + r1 * tx0
    else:
        c1x, c1y = start_x + r1 * ty0, start_y + r1 * (-tx0)
    a0 = math.degrees(math.atan2(start_y - c1y, start_x - c1x))
    arc1 = arc_path((c1x, c1y), r1, a0, a0 + turn1, n=n1)

    e1x, e1y, e1tx, e1ty = arc1[-1]
    if turn2 >= 0:
        c2x, c2y = e1x + r2 * (-e1ty), e1y + r2 * e1tx
    else:
        c2x, c2y = e1x + r2 * e1ty, e1y + r2 * (-e1tx)
    b0 = math.degrees(math.atan2(e1y - c2y, e1x - c2x))
    arc2 = arc_path((c2x, c2y), r2, b0, b0 + turn2, n=n2)

    return concat_paths(arc1, arc2)


def concat_paths(*paths):
    """Join path sample lists end-to-start, dropping duplicate shared points."""
    result = list(paths[0])
    for p in paths[1:]:
        result.extend(p[1:])
    return result


def dome_taper(outline, n=8, max_angle_deg=85):
    """Progressively narrowed copies of a closed (perp, z) outline,
    shrinking ONLY the radial (perp) coordinate toward the centerline --
    z is left untouched. Used to cap a swept channel with a rounded
    taper instead of a flat cut-off face.

    Earlier this scaled toward the outline's own centroid in BOTH
    dimensions, which works for a simple convex cross-section but broke
    down once the channel profile became a sharp-waisted hourglass (two
    45-degree cones meeting at a point): the centroid doesn't sit at the
    waist, so scaling toward it pulled points in a way that could
    self-intersect. Shrinking perp only, per point, at that point's own
    z, can't self-intersect for ANY cross-section shape, convex or not.

    Returns a list of (points, along) pairs, `along` being how far past
    the flat position that step's ring should sit."""
    depth_ref = max(abs(p) for (p, _) in outline)
    steps = []
    for k in range(1, n + 1):
        angle = math.radians(max_angle_deg * k / n)
        scale = math.cos(angle)
        along = math.sin(angle) * depth_ref
        pts = [(p * scale, z) for (p, z) in outline]
        steps.append((pts, along))
    return steps


def sweep_channel(name, path_samples, round_start=False, round_end=False):
    """Sweep the (offset-token) cross-section along an arbitrary 2D path
    (straight or curved) so a branch can peel away from another channel
    with a continuously-varying width instead of two full-width channels
    crossing at a hard angle.

    round_start/round_end cap that end with a dome (dome_taper) instead
    of a flat cut-off face -- only where the path is a genuine dead end.
    Never set True on an end that connects to another channel (like a
    branch point matched to the main lane): that would break the
    tangent-continuity the retention margin depends on."""
    base = channel_profile()
    right = [(r, z) for (z, r) in base]
    left = [(-r, z) for (z, r) in reversed(base)]
    outline = right + left  # closed (perp, z) loop
    n = len(outline)

    bm = bmesh.new()
    rings = []

    def add_ring(pts, x, y, tx, ty):
        nx, ny = -ty, tx  # left-hand normal to the tangent
        ring = [bm.verts.new((x + p * nx, y + p * ny, z)) for (p, z) in pts]
        rings.append(ring)

    if round_start:
        x0, y0, tx0, ty0 = path_samples[0]
        for pts, along in reversed(dome_taper(outline)):
            add_ring(pts, x0 - tx0 * along, y0 - ty0 * along, tx0, ty0)

    for (x, y, tx, ty) in path_samples:
        add_ring(outline, x, y, tx, ty)

    if round_end:
        x1, y1, tx1, ty1 = path_samples[-1]
        for pts, along in dome_taper(outline):
            add_ring(pts, x1 + tx1 * along, y1 + ty1 * along, tx1, ty1)

    for k in range(len(rings) - 1):
        ra, rb = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))

    bm.faces.new(reversed(rings[0]))
    bm.faces.new(rings[-1])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def rounded_rect_points(x0, y0, x1, y1, cr, n=8):
    """Closed outline of a rectangle with its 4 corners rounded to
    radius cr, as a list of (x, y) points."""
    corners = [
        (x1 - cr, y0 + cr, -90, 0),    # bottom-right
        (x1 - cr, y1 - cr, 0, 90),     # top-right
        (x0 + cr, y1 - cr, 90, 180),   # top-left
        (x0 + cr, y0 + cr, 180, 270),  # bottom-left
    ]
    pts = []
    for (cx, cy, a0, a1) in corners:
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + cr * math.cos(a), cy + cr * math.sin(a)))
    return pts


def build_rounded_box(name, x0, y0, x1, y1, z0, height, corner_radius, n=8):
    """A box with its 4 vertical corners rounded, built by extruding a
    rounded-rectangle 2D outline straight up -- same bmesh technique as
    sweep_channel, just a flat (non-curving) sweep."""
    pts = rounded_rect_points(x0, y0, x1, y1, corner_radius, n)

    bm = bmesh.new()
    verts = [bm.verts.new((px, py, z0)) for (px, py) in pts]
    face = bm.faces.new(verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    new_verts = [g for g in res['geom'] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=new_verts, vec=(0.0, 0.0, height))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def build_logo_cutter(target_cx, target_cy, target_z_top):
    """Import the department logo (logo_monogram.svg -- the monogram
    plus the outer ring, the ring's original stroke converted to an
    actual filled path via Inkscape's "stroke to path" since Blender's
    own SVG import doesn't turn stroke-width into geometry) as curves,
    extrude them into ONE uniform-depth engraving cutter sized to
    LOGO_DIAMETER and centred at (target_cx, target_cy) -- same recipe as
    engrave_letter, just built from imported curves instead of a text
    object. Every shape in the SVG becomes a plain LOGO_DEPTH groove;
    there's no separate backdrop depth anymore."""
    before = set(bpy.data.objects.keys())
    before_colls = set(bpy.data.collections.keys())
    bpy.ops.import_curve.svg(filepath=LOGO_SVG_PATH)
    new_objs = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    if not new_objs:
        return None

    depth = LOGO_DEPTH
    for obj in new_objs:
        obj.data.extrude = (depth + 0.02) / 2
        obj.data.fill_mode = 'BOTH'

    bpy.ops.object.select_all(action='DESELECT')
    for obj in new_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = new_objs[0]
    bpy.ops.object.convert(target='MESH')

    if len(new_objs) > 1:
        bpy.ops.object.join()
    logo_obj = bpy.context.view_layer.objects.active

    # Use LOCAL bound_box (not world-space) to derive the fit -- imported
    # SVG curves can land with a non-zero starting object.location, and
    # combining a world-space centre with a "+=" offset silently baked in
    # that starting offset TWICE, leaving the monogram several mm away
    # from where the disk (built directly at the target point) ended up.
    local_bbox = [mathutils.Vector(c) for c in logo_obj.bound_box]
    xs = [v.x for v in local_bbox]
    ys = [v.y for v in local_bbox]
    cur_diam = max(max(xs) - min(xs), max(ys) - min(ys))
    scale = LOGO_DIAMETER / cur_diam
    local_cx = (max(xs) + min(xs)) / 2
    local_cy = (max(ys) + min(ys)) / 2

    logo_obj.scale = (scale, scale, 1.0)
    logo_obj.location.x = target_cx - local_cx * scale
    logo_obj.location.y = target_cy - local_cy * scale
    logo_obj.location.z = target_z_top - depth / 2

    bpy.ops.object.select_all(action='DESELECT')

    # Clean up the empty collection the SVG importer creates for itself --
    # its objects have already been re-parented under the current
    # collection by convert/join, so it's just an empty leftover.
    for cname in set(bpy.data.collections.keys()) - before_colls:
        coll = bpy.data.collections.get(cname)
        if coll and len(coll.objects) == 0:
            bpy.data.collections.remove(coll)

    return [logo_obj]


def build_word_label(text, cx, cy, target_z_top, font_size, depth=0.5, font_path=None):
    """A flat word (not a single glyph) embossed on the board's own top
    surface, same recipe as engrave_letter()/build_logo_cutter()'s bump
    conversion -- with ONE fix baked in from the start this time: a real
    embed_depth (not a ~0.01mm sliver) below the surface. A too-thin
    sliver against a big flat cap face is nearly coplanar, and Blender's
    exact boolean solver silently drops the raised geometry rather than
    erroring -- confirmed on the token letters, fixed there the same
    way. Returns the built (unlinked-from-scene-selection) mesh object,
    or None if the text came out empty."""
    if not text:
        return None

    embed_depth = 0.3

    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.text_add(location=(0, 0, 0))
    txt = bpy.context.active_object
    txt.data.body = text
    if font_path:
        font = bpy.data.fonts.load(font_path, check_existing=True)
        txt.data.font = font
    txt.data.size = font_size
    txt.data.align_x = 'CENTER'
    txt.data.align_y = 'CENTER'
    txt.data.extrude = (depth + embed_depth) / 2
    txt.location = (cx, cy, target_z_top + (depth - embed_depth) / 2)

    bpy.context.view_layer.objects.active = txt
    txt.select_set(True)
    bpy.ops.object.convert(target='MESH')

    xs = [v.co.x for v in txt.data.vertices]
    ys = [v.co.y for v in txt.data.vertices]
    if not xs:
        bpy.data.objects.remove(txt, do_unlink=True)
        return None
    # Recenter on the real ink bounding box, same font-metric-vs-ink
    # mismatch fix as engrave_letter().
    txt.location.x -= (max(xs) + min(xs)) / 2
    txt.location.y -= (max(ys) + min(ys)) / 2

    return txt


def clip_from_main_lane_collar(cutter, main_y, branch_x, x_lo, x_hi,
                                protect_radius, handoff_window):
    """Subtract, from `cutter` (a branch's own swept tube), the region
    within protect_radius of the MAIN LANE's own Y axis (main_y), for X
    outside a small handoff window around branch_x.

    Root cause this addresses (distinct from compound_arc_path's fold
    issue): the branch's tube must stay FULL WIDTH along its whole path
    -- the token's cone needs that clearance to physically slide through
    -- but right after the junction the branch's own centerline has
    barely moved away from main_y yet (Y grows ~quadratically from a
    tangent-horizontal start), so for a good few mm past the junction
    the branch's still-wide tube keeps reaching back across main_y's own
    retention radius even though a token already committed to the
    branch there doesn't need anything AT main_y -- confirmed by both
    the validated ray-cast scan and a real print failing at exactly
    this kind of junction. No curve shape fixes this (any branch must
    start at zero Y-divergence); the fix has to remove material access
    directly. This leaves the genuine shared cross-section right at the
    junction (|x - branch_x| <= handoff_window) untouched -- that's the
    one place the two channels are SUPPOSED to be identical -- and clips
    the branch's own reach into the main lane's collar everywhere else."""
    z_lo, z_hi = -1.0, PLATE_THICKNESS + 1.0
    y_lo, y_hi = main_y - protect_radius, main_y + protect_radius
    segments = []
    if x_lo < branch_x - handoff_window:
        segments.append((x_lo, branch_x - handoff_window))
    if branch_x + handoff_window < x_hi:
        segments.append((branch_x + handoff_window, x_hi))

    for i, (xa, xb) in enumerate(segments):
        prot = build_rounded_box(f"ProtectCollar{i}", xa, y_lo, xb, y_hi,
                                  z_lo, z_hi - z_lo, corner_radius=0.05)
        mod = cutter.modifiers.new(name=f"Clip{i}", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = prot
        bpy.context.view_layer.objects.active = cutter
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(prot, do_unlink=True)


def build_board():
    main_y = 4 * R_BIG
    dome_reach = max(r for (_, r) in channel_profile())

    # Single-radius arc_r tuning history (validated Y-half-width scan,
    # matches a control point to 0.0000mm) -- kept for context:
    #   2.8*R_BIG: -23.67mm.  4.5*R_BIG: worse.  1.3*R_BIG: -16.16mm.
    #   1.15*R_BIG: -14.74mm, the best a SINGLE radius can do before the
    #   tube (half-width ~R_BIG+OF) self-intersects the turn.
    # None of those reach a safe margin -- confirmed by a real print
    # failing at the junctions. Root cause (see compound_arc_path's own
    # docstring): a constant-radius turn folds back on itself in X at
    # its own halfway point, where the Y-gap between the two tube
    # positions sharing that X shrinks to 0 as the fold is approached,
    # for ANY radius -- so a single arc can't avoid it. Fixed instead
    # with a two-radius compound turn: a large, gentle r1 for the first
    # part (reaching safe Y-clearance from the main lane before ITS
    # fold would occur), then a smaller r2 for the rest.
    # UPDATE: a large r1 (tried 1.7x) made things WORSE (-17.62mm), not
    # better -- turns out the fold-merge fix doesn't matter as much as
    # simply how LONG the branch stays close to main_y, and a bigger
    # radius diverges in Y more SLOWLY per mm of X, spending more X
    # length "dangerously close but full width" even without folding.
    # Smaller radius (just above the self-intersection floor) wins on
    # that axis instead -- matches the single-arc finding that smaller
    # was better too. So both arcs now use nearly the same small radius;
    # the split is kept mostly for interface compatibility.
    # Reverted to the simple single-radius arc used in the last physical
    # print (arc_r = 2.8*R_BIG) per direct request -- none of today's
    # geometry variants (small-radius compound arc, tight single arc, a
    # 90-degree T-junction) got the margin to a genuinely safe value
    # anyway (best was -13.28mm), so there's no longer a strong reason to
    # keep the more complex, still-broken compound turn over the
    # original, simpler, equally-broken one.
    arc_r = 2.8 * R_BIG
    pocket_depth = 2 * R_BIG

    main_x0 = -R_BIG
    main_x1 = -R_BIG + 24 * R_BIG
    # The domed end caps (round_start/round_end below) extend the channel
    # further than a flat end would, by up to the profile's own max radius
    # -- inset the flat path by that amount so main_x0..main_x1 stays the
    # TOTAL reach (dome included) instead of ballooning past the board.
    main_path = straight_path((main_x0 + dome_reach, main_y),
                               (main_x1 - dome_reach, main_y), n=2)

    def hook_dead_end_path(branch_x, side, tangent_sign=+1):
        """side=+1 curves into the +Y region, side=-1 into -Y.

        tangent_sign=+1 starts tangent +X, matching the main lane's own
        direction of travel there; tangent_sign=-1 starts tangent -X --
        collinear with the main lane just pointing the other way, which
        is EQUALLY smooth (the cross-section at a horizontal tangent is
        the same Y-Z plane either way -- it's only a *perpendicular*
        tangent, like a T-junction, that misaligns cross-sections and
        breaches retention). tangent_sign=-1 bulges toward -X instead of
        +X, and always ends with the tangent opposite the one it started
        with, so the two lanes end up with genuinely opposite tangents
        both at the branch and at the pocket.

        Reverted (per direct request) to the simple single-radius arc
        from the last physical print, instead of today's compound-arc or
        T-junction experiments -- see the arc_r comment above for why."""
        if TEST_RIGHT_ANGLE_BRANCH:
            # kept as an option (set True to rebuild) -- see its own
            # comment above for the measured result, not an improvement.
            end_y = main_y + side * pocket_depth
            return straight_path((branch_x, main_y), (branch_x, end_y), n=24)
        arc_center = (branch_x, main_y + side * arc_r)
        a_start = -90 if side > 0 else 90
        if tangent_sign > 0:
            a_end = -a_start                                     # short way: bulge +X
        else:
            a_end = a_start + (180 if side < 0 else -180)         # long way: bulge -X
        arc = arc_path(arc_center, arc_r, a_start, a_end, n=24)
        end_x, end_y, end_tx, end_ty = arc[-1]
        tail_len = pocket_depth if end_tx > 0 else -pocket_depth
        tail = straight_path((end_x, end_y), (end_x + tail_len, end_y), n=2)
        return concat_paths(arc, tail)

    # Two branch points, well apart along the main lane.
    branch_x_a = TOKEN_ROW_X_SHIFT + 0.5 * (5 * (2 * R_BIG + OF) + 6 * (2 * R_BIG + OF))  # between tokens 5 & 6
    branch_x_b = TOKEN_ROW_X_SHIFT + 4 * (2 * R_BIG + OF)  # at token 4's rest position (the first "C")

    # Both lanes are plain half-circles, mirrored across the main lane's
    # own axis (A bulges +Y, B bulges -Y) AND with opposite branch
    # tangents (A starts +X, B starts -X) -- so A bulges right/faces
    # back, B bulges left/faces forward.
    # (path, round_start, round_end) -- only round a genuine dead end,
    # never an end that connects to another channel (branch points).
    # 4th element: the branch_x to clip against (None = don't clip, used
    # for the main lane itself, which IS the collar reference).
    cutters = [
        ("ChannelMain", main_path, True, True, None),
        ("DeadEndA", hook_dead_end_path(branch_x_a, +1, tangent_sign=+1), False, True, branch_x_a),
        ("DeadEndB", hook_dead_end_path(branch_x_b, -1, tangent_sign=-1), False, True, branch_x_b),
    ]

    # Board footprint = the actual bounding box of every channel path
    # (centerline +/- the channel's own half-width) plus one even
    # border margin on all sides -- so the layout is evenly framed
    # instead of using separate, mismatched X/Y margin formulas (which
    # left lots of dead space on one side and almost none on another).
    BORDER_MARGIN = 4.0 * MODEL_SCALE
    all_xs = [x for _, path, _, _, _ in cutters for (x, y, tx, ty) in path]
    all_ys = [y for _, path, _, _, _ in cutters for (x, y, tx, ty) in path]
    board_x0 = min(all_xs) - dome_reach - BORDER_MARGIN
    board_x1 = max(all_xs) + dome_reach + BORDER_MARGIN
    # Y is kept SYMMETRIC around main_y (so the main lane runs through the
    # board's own vertical centre) instead of fitting each side
    # independently -- take the larger of what the channels themselves
    # need and what the logo (top-left corner, above the main lane) needs,
    # and apply that SAME half-height to both the top and bottom edge.
    channel_half_h = max(main_y - min(all_ys), max(all_ys) - main_y) + dome_reach + BORDER_MARGIN
    logo_half_h = (dome_reach + 3.0 + LOGO_MARGIN + LOGO_DIAMETER)
    board_half_h = max(channel_half_h, logo_half_h)
    board_y0 = main_y - board_half_h
    board_y1 = main_y + board_half_h

    # NOTE: this used to be force-snapped to an exact 120x80mm here,
    # re-centering the naturally-derived box onto hardcoded +-60/+-40
    # half-widths. That's what caused a real bug: the snap doesn't know
    # about BORDER_MARGIN, so once R_BIG changed again after the snap
    # was calibrated, it silently pushed the board edge flush against
    # the channel's own dome cap (measured 0.00mm margin at both main-
    # lane ends). Reverted to the naturally-derived box below, which
    # bakes BORDER_MARGIN in correctly by construction -- it won't land
    # on an exact round number any more, but it won't clip the channel
    # either. See the printed board size after this change if an exact
    # dimension is wanted again -- worth re-deriving on purpose, not
    # forcing blindly.

    board_size = (board_x1 - board_x0, board_y1 - board_y0, PLATE_THICKNESS - EPS)
    board_corner_radius = 6.0 * MODEL_SCALE

    board = build_rounded_box(
        "Board",
        board_x0, board_y0, board_x1, board_y1,
        PLATE_Z_BOTTOM, board_size[2],
        board_corner_radius,
    )

    mat = bpy.data.materials.get("PuzzleBoardRed")
    if mat is None:
        mat = bpy.data.materials.new("PuzzleBoardRed")
    mat.diffuse_color = (0.8, 0.05, 0.05, 1.0)
    board.data.materials.clear()
    board.data.materials.append(mat)

    # Hanging hole, top-right corner, per direct request -- enlarged
    # further per follow-up request. Margin (12mm, bumped up along with
    # the radius) keeps it clear of both the corner fillet
    # (board_corner_radius, ~4.6mm) and the board's own straight edges,
    # leaving ~7.5mm of solid material around the hole on every side.
    HOLE_RADIUS = 4.5
    HOLE_MARGIN = 12.0
    hole_cx = board_x1 - HOLE_MARGIN
    hole_cy = board_y1 - HOLE_MARGIN
    bpy.ops.mesh.primitive_cylinder_add(
        radius=HOLE_RADIUS, depth=board_size[2] + 1.0,
        location=(hole_cx, hole_cy, board_size[2] / 2), vertices=SEGMENTS)
    hole_cutter = bpy.context.active_object
    mod = board.modifiers.new(name="HangHole", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = hole_cutter
    bpy.context.view_layer.objects.active = board
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(hole_cutter, do_unlink=True)

    for cname, path, round_start, round_end, clip_branch_x in cutters:
        cutter = sweep_channel(cname, path, round_start=round_start, round_end=round_end)
        # clip_from_main_lane_collar is NOT applied here by default -- see
        # its docstring and the module docstring's KNOWN UNRESOLVED ISSUE
        # section. Tested extensively: a narrow handoff_window (~3mm)
        # gets retention breaches down to a worst of -1.75mm (from
        # -14.17mm), but the SAME narrow window that fixes retention
        # also cuts the branch's own passage down to ~0.06mm (need
        # 4.38mm for the cone to slide through) -- widening the window
        # enough to restore passage (~10-13mm) undoes almost all of the
        # retention fix. The two needs are in direct conflict at the
        # same (x, y) location near any branch; no handoff_window value
        # found gets both a safe margin AND a passable branch. Left
        # unapplied (uncut) rather than shipping a puzzle that's either
        # unsafe or physically unplayable.
        if clip_branch_x is not None and False:
            clip_from_main_lane_collar(
                cutter, main_y, clip_branch_x,
                x_lo=board_x0 - 5, x_hi=board_x1 + 5,
                protect_radius=R_SMALL + 0.6, handoff_window=3.0,
            )
        mod = board.modifiers.new(name=cname, type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter

        bpy.context.view_layer.objects.active = board
        bpy.ops.object.modifier_apply(modifier=mod.name)

        bpy.data.objects.remove(cutter, do_unlink=True)

    # Department logo, top-left corner, with EQUAL margins to the board's
    # left edge and top edge (both == BORDER_MARGIN, same margin the
    # channel itself keeps) per direct request. logo_cx's BORDER_MARGIN
    # gap happens to already match main_x0's own distance from board_x0
    # (main_x0 == board_x0 + BORDER_MARGIN, by construction), so this is
    # the same left-flush position as before -- only the top formula
    # changed, from "flush with DeadEndA's turn + an arbitrary shift" to
    # a margin that's provably equal to the left one.
    logo_cx = board_x0 + BORDER_MARGIN + LOGO_DIAMETER / 2
    logo_cy = board_y1 - BORDER_MARGIN - LOGO_DIAMETER / 2

    # No raised platform anymore -- the logo sits directly on the plain
    # board top surface, protruding LOGO_DEPTH above it (a plain bump,
    # "выпуклость"), no intermediate pedestal.
    logo_cutters = build_logo_cutter(logo_cx, logo_cy, board_size[2]) or []
    for i, cutter in enumerate(logo_cutters):
        cutter.location.z += LOGO_DEPTH  # was centred for a cut (mostly
                                          # below target_z_top); shift up
                                          # a full depth so it instead
                                          # sits mostly ABOVE it, as a bump
        mod = board.modifiers.new(name=f"Logo{i}", type='BOOLEAN')
        mod.operation = 'UNION'
        mod.object = cutter

        bpy.context.view_layer.objects.active = board
        bpy.ops.object.modifier_apply(modifier=mod.name)

        bpy.data.objects.remove(cutter, do_unlink=True)

    # "physchem.cz" label, starting at the center of DeadEndB's own hook
    # (branch_x_b, main_y - arc_r -- the circle the U-turn is swept
    # from) and spanning to the right margin, per direct request. Bigger
    # font, sized to fill that width -- validated with a ray-cast scan
    # (not guessed): at x=branch_x_b the open band is y=[-3.15, 15.15],
    # centered right on the hook's own arc-center Y (6.0), consistent at
    # least out to x=branch_x_b+15, so there's no risk of capping over
    # the channel's own bore even starting this far left.
    label_x0 = branch_x_b
    label_x1 = board_x1 - BORDER_MARGIN
    label_cx = (label_x0 + label_x1) / 2
    label_cy = main_y - arc_r   # hook's own arc-center Y
    label_txt = build_word_label("physchem.cz", label_cx, label_cy, board_size[2],
                                  font_size=16.5, depth=LOGO_DEPTH,
                                  font_path="/usr/share/fonts/TTF/Comfortaa-Regular.ttf")
    if label_txt is not None:
        mod = board.modifiers.new(name="Label", type='BOOLEAN')
        mod.operation = 'UNION'
        mod.object = label_txt
        bpy.context.view_layer.objects.active = board
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(label_txt, do_unlink=True)

    return board


def animate_escape(token, x0, y0):
    """Keyframed demo (not a physics sim) of a token escaping through the
    confirmed junction breach at (x0, y0). Earlier version added sideways
    drift + rotation "for visual flair" and that was a mistake: those
    intermediate positions/orientations were never actually measured, and
    the token visibly clipped through the board there. This version only
    ever moves straight up in Z, at the FIXED (x0, y0) verify_retention
    already sampled, through the exact z heights that were individually
    measured clear (channel Y half-width ~24-28mm there vs the token's
    own R_SMALL=4.18mm) -- so every point on this path is one that was
    actually checked, not interpolated across untested territory. Linear
    interpolation between them (not Blender's default Bezier) so the
    in-between frames can't overshoot outside the verified band either.

    No physics engine involved: Blender's rigid-body/GImpact
    concave-dynamic collision already crashed the whole application once
    this session when tried on this exact non-convex neck shape."""
    token.rotation_mode = 'XYZ'
    token.rotation_euler = (0.0, 0.0, 0.0)

    prev_interp = bpy.context.preferences.edit.keyframe_new_interpolation_type
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'

    # (frame, z) -- z values are exactly the heights verify_retention
    # measured clear at this (x0, y0): 0.3, 1.2, 2.0, H_SMALL, H_SMALL+0.4,
    # PLATE_THICKNESS-0.05, then well above the board (nothing there at all).
    keys = [
        (1, 0.0),
        (10, 0.3),
        (25, 1.2),
        (40, 2.0),
        (55, H_SMALL),
        (65, H_SMALL + 0.4),
        (75, PLATE_THICKNESS - 0.05),
        (100, 20.0),
        (115, 20.0),
    ]
    for frame, z in keys:
        token.location = (x0, y0, z)
        token.keyframe_insert(data_path="location", frame=frame)

    bpy.context.preferences.edit.keyframe_new_interpolation_type = prev_interp

    token.location = (x0, y0, 0.0)  # reset to rest so a fresh reload starts clean

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 115
    scene.frame_current = 1


def build_scene(coll):
    escape_token = None
    for k, letter in enumerate(LETTERS):
        x0 = TOKEN_ROW_X_SHIFT + k * (2 * R_BIG + OF)
        y0 = 4 * R_BIG
        token = build_token(f"Token_{k:02d}_{letter}", letter, x0, y0, 0.0)
        link_only(token, coll)
        if k == 3:  # "S" -- sits at x=32.9mm, ~0.2mm from the worst measured breach (x=33.1mm)
            escape_token = (token, x0, y0)

    if escape_token is not None:
        animate_escape(*escape_token)

    board = build_board()
    link_only(board, coll)
    return board


def verify_retention(board):
    """TEMPORARY diagnostic (validated: control point matches nominal to
    0.0000mm). The channel is a SLOT (uniform cross-section along its own
    path direction), so retention only depends on the channel's Y
    half-width at a given absolute Z, measured from the MAIN LANE's own
    centerline -- not full angular closure. Scan near each branch and
    report the worst (smallest) breach margin found."""
    import mathutils as _mu

    main_y = 4 * R_BIG
    branch_x_a = TOKEN_ROW_X_SHIFT + 0.5 * (5 * (2 * R_BIG + OF) + 6 * (2 * R_BIG + OF))
    branch_x_b = TOKEN_ROW_X_SHIFT + 4 * (2 * R_BIG + OF)

    mw = board.matrix_world
    mw_inv = mw.inverted()

    def wall_y(x, z, side):
        origin_world = _mu.Vector((x, main_y + side * 0.05, z))
        origin_local = mw_inv @ origin_world
        dir_local = (mw_inv.to_3x3() @ _mu.Vector((0.0, float(side), 0.0))).normalized()
        success, loc, normal, idx = board.ray_cast(origin_local, dir_local, distance=30.0)
        if not success:
            return None
        loc_world = mw @ loc
        return abs(loc_world.y - main_y)

    test_zs = sorted(set([0.3, 1.2, 2.0, H_SMALL, H_SMALL + 0.15, H_SMALL + 0.4,
                           (H_SMALL + PLATE_THICKNESS) / 2, PLATE_THICKNESS - 0.05]))

    results = []
    for label, branch_x in [("A", branch_x_a), ("B", branch_x_b)]:
        for dx in range(-24, 25, 1):
            x = branch_x + dx
            for z in test_zs:
                for side in (+1, -1):
                    w = wall_y(x, z, side)
                    margin = None if w is None else (R_SMALL - w)
                    results.append((margin if margin is not None else -999.0,
                                     label, x, z, side, w))

    results.sort(key=lambda t: t[0])
    print(f"[verify] R_SMALL={R_SMALL:.2f}mm", flush=True)
    print("[verify] worst 10 (margin<0 = breach):", flush=True)
    for margin, label, x, z, side, w in results[:10]:
        w_s = f"{w:.2f}" if w is not None else "NONE(>30mm)"
        print(f"[verify]  margin={margin:+.2f}mm  junction={label}  x={x:.1f}  "
              f"z={z:.2f}  side={'+Y' if side > 0 else '-Y'}  measured={w_s}", flush=True)
    n_breach = sum(1 for m, *_ in results if m < 0)
    print(f"[verify] samples={len(results)}  breaches(margin<0)={n_breach}", flush=True)


def set_units_to_mm():
    """All geometry here treats 1 Blender unit as 1mm -- point the scene's
    unit display at millimeters so the UI (dimensions, N-panel, rulers)
    matches instead of showing everything as fractions of a meter."""
    units = bpy.context.scene.unit_settings
    units.system = 'METRIC'
    units.length_unit = 'MILLIMETERS'
    units.scale_length = 0.001


def purge_orphans():
    """Remove stray objects/collections left behind by earlier reloads that
    crashed partway through (an exception between creating a helper object
    -- SVG import curves, LogoDisk, debug cameras/suns -- and this script's
    own cleanup of it skips that cleanup, and since those helpers get
    linked into whatever collection was active at the time rather than
    "Scripted", clear_collection() never sees them either). Anything
    matching the names/collections this script itself creates, but that
    isn't currently inside "Scripted", is leftover clutter -- safe to
    delete. Real user objects (default Camera/Light, anything else with an
    unrelated name) are left alone."""
    scripted = bpy.data.collections.get(COLLECTION_NAME)
    scripted_objs = set(scripted.objects.keys()) if scripted else set()

    stray_prefixes = ("Board", "Token_", "LogoDisk", "DebugCam", "DebugSun", "Curve", "path",
                       "Phys")  # PhysLower_/PhysUpper_/PhysCon_ -- leftover physics-test rigs
    for obj in list(bpy.data.objects):
        if obj.name in scripted_objs:
            continue
        if obj.name.startswith(stray_prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)

    for coll in list(bpy.data.collections):
        if coll.name == COLLECTION_NAME:
            continue
        if ".svg" in coll.name or coll.name.startswith("logo_"):
            for obj in list(coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(coll)

    # A past physics test cranked scene.gravity to 500 (x50 normal) for
    # diagnostics and never reset it -- harmless with no rigid bodies
    # left in the scene, but reset it back to normal Earth gravity
    # anyway so nothing is left in a surprising state.
    if tuple(bpy.context.scene.gravity) != (0.0, 0.0, -9.81):
        bpy.context.scene.gravity = (0.0, 0.0, -9.81)


def main():
    purge_orphans()
    set_units_to_mm()
    coll = get_or_create_collection(COLLECTION_NAME)
    clear_collection(coll)
    build_scene(coll)
    # verify_retention(board) is available (validated, see its docstring)
    # but not run every reload -- it adds a few seconds per save. Call it
    # manually (board = build_scene(coll); verify_retention(board)) when
    # checking a retention-geometry change.


main()
