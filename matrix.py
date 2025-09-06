#!/usr/bin/env python3
# High-density terminal “point cloud” / ray painter for Wi-Fi motion.
# Reads CSV lines: mac,rssi,motion  (one per packet)
# Usage:
#   python3 -u wifi_sensing.py | python3 wifi_room_ascii.py
#
# Tips:
# - Enlarge the terminal (160x50+). Unicode Braille gives 2x4 subpixels per cell.
# - Works with plain ANSI; no external deps.

import sys, time, math, hashlib, random, shutil, signal, collections

# ---------------- Tunables ----------------
TARGET_FPS          = 20.0

# Range mapping (RSSI -> radius)
RSSI_NEAR           = -30.0
RSSI_FAR            = -90.0

# Deposition
BASE_SAMPLES        = 24     # micro-pts per sample baseline
SAMPLES_PER_MOTION  = 10     # + per unit of motion
SAMPLES_PER_DRSSI   = 30     # + per unit |dRSSI| (dBm/s), capped
MAX_SAMPLES_PER     = 600    # hard cap per line (protect CPU)
JITTER_ARC_DEG      = 22.0   # angular jitter per micro-pt
JITTER_R_FRAC       = 0.10   # radial jitter fraction
RAY_STEPS_PER_M     = 9.0    # how many deposits along the radial path per meter

# Memories (fast “trail” vs slow “map”)
FAST_DECAY_PER_SEC  = 0.88
SLOW_DECAY_PER_SEC  = 0.995
SLOW_GAIN           = 0.25   # fraction of ink that feeds slow map

# Rendering
BORDER              = True
HEADER_LINES        = 2
CHAR_FG_RAMP        = [240, 71, 184, 208, 196]  # grey->green->yellow->orange->red
GLYPHS              = " .:-=+*#%@"

# Equalization (avoid single hotspot dominating)
HISTO_EQ_FRACTION   = 0.95   # scale to 95th percentile instead of absolute max

# Per-MAC smoothing
EMA_RSSI_ALPHA      = 0.35
EMA_MOTION_ALPHA    = 0.4
DRSSI_CLAMP         = 8.0     # cap |dRSSI/dt| used for ink boost
# ------------------------------------------

def term_dims():
    sz = shutil.get_terminal_size(fallback=(180, 56))
    W  = max(120, sz.columns)
    H  = max(40,  sz.lines)
    l = 1 if BORDER else 0
    r = 1 if BORDER else 0
    t = HEADER_LINES + (1 if BORDER else 0)
    b = 1 if BORDER else 0
    # Braille grid packs 2x4 pixels in 1 char. We'll keep chars wide but with 4 subrows per char row.
    w_chars = W - l - r
    h_chars = H - t - b
    # subpixel resolution
    w_sub = w_chars * 2
    h_sub = h_chars * 4
    return W, H, w_chars, h_chars, w_sub, h_sub, l, t

def mac_angle(mac:str)->float:
    # stable per-MAC azimuth in radians
    h = int(hashlib.md5(mac.encode()).hexdigest(), 16)
    return (h % 360) * math.pi / 180.0

def rssi_to_radius_pix(rssi:float, Rsub:float)->float:
    if rssi > RSSI_NEAR: rssi = RSSI_NEAR
    if rssi < RSSI_FAR:  rssi = RSSI_FAR
    t = (RSSI_NEAR - rssi) / (RSSI_NEAR - RSSI_FAR)  # 0..1
    return 2.0 + t * (Rsub - 4.0)

def color_for(u):
    if u <= 0: return "\033[38;5;240m"
    if u >= 1: return f"\033[38;5;{CHAR_FG_RAMP[-1]}m"
    segs = len(CHAR_FG_RAMP) - 1
    x = u * segs
    i = int(x)
    t = x - i
    c1 = CHAR_FG_RAMP[i]
    c2 = CHAR_FG_RAMP[min(i+1, segs)]
    return f"\033[38;5;{(c2 if t>0.5 else c1)}m"

def clamp(a, lo, hi): return lo if a<lo else (hi if a>hi else a)

class BrailleCanvas:
    """A subpixel canvas: width x height in *subpixels* (2x4 per char cell).
       We accumulate two layers (fast and slow), then render as Braille cells.
    """
    def __init__(self):
        self.resize()
        self.last_fast = time.time()
        self.last_slow = self.last_fast

    def resize(self):
        (self.W, self.H, self.wc, self.hc,
         self.ws, self.hs, self.left, self.top) = term_dims()
        # centers in subpixel coords
        self.cx = self.ws // 2
        self.cy = self.hs // 2
        self.R  = min(self.cx, self.cy) - 4

        # layers
        self.fast = [0.0]*(self.ws*self.hs)
        self.slow = [0.0]*(self.ws*self.hs)
        self.hit  = [0]  *(self.ws*self.hs)   # congestion hint

        # precompute circle mask for char cells, to trim edges
        self.cell_mask = [True]*(self.wc*self.hc)
        for j in range(self.hc):
            for i in range(self.wc):
                # cell center in subpixel coords
                cx_sub = i*2 + 1
                cy_sub = j*4 + 2
                dx = cx_sub - self.cx
                dy = cy_sub - self.cy
                inside = (dx*dx + dy*dy) <= (self.R*self.R)
                self.cell_mask[j*self.wc + i] = inside

    def _idx(self, x, y): return y*self.ws + x

    def _in_circle_sub(self, x, y):
        dx = x - self.cx
        dy = y - self.cy
        return (dx*dx + dy*dy) <= (self.R*self.R)

    def decay(self, now):
        dtf = now - self.last_fast
        if dtf > 0:
            f = FAST_DECAY_PER_SEC ** dtf
            self.fast = [v*f for v in self.fast]
            self.hit  = [int(h*f) for h in self.hit]
            self.last_fast = now
        dts = now - self.last_slow
        if dts > 0:
            g = SLOW_DECAY_PER_SEC ** dts
            self.slow = [v*g for v in self.slow]
            self.last_slow = now

    def splat_subpixel(self, x, y, ink, rng):
        if x<0 or x>=self.ws or y<0 or y>=self.hs: return
        if not self._in_circle_sub(x, y): return
        idx = self._idx(x, y)
        # congestion-aware push to one of 8 neighbors if heavily loaded
        best_i = idx; best_h = self.hit[idx]
        for _ in range(4):
            nx = x + rng.randint(-1,1); ny = y + rng.randint(-1,1)
            if nx<0 or nx>=self.ws or ny<0 or ny>=self.hs: continue
            if not self._in_circle_sub(nx, ny): continue
            ii = self._idx(nx, ny)
            hh = self.hit[ii]
            if hh < best_h:
                best_h = hh; best_i = ii
                if hh == 0: break
        self.fast[best_i] += ink
        self.slow[best_i] += ink * SLOW_GAIN
        self.hit[best_i]  += 1

    def deposit_ray(self, theta, r_pix, k, rng):
        # march from 20% out to r, so near-center doesn’t over-bloom
        start = int(0.2 * r_pix)
        steps = max(1, int((r_pix - start) * (RAY_STEPS_PER_M/8.0)))  # coarser near, fine far
        for s in range(steps):
            t = (s / max(1, steps-1))
            r = start + t * (r_pix - start)
            # jitter per step
            dth = math.radians(rng.uniform(-JITTER_ARC_DEG, +JITTER_ARC_DEG))
            rr  = r * (1.0 + rng.uniform(-JITTER_R_FRAC, +JITTER_R_FRAC))
            th  = theta + dth
            x   = int(round(self.cx + rr*math.cos(th)))
            y   = int(round(self.cy + rr*math.sin(th)))
            if 0<=x<self.ws and 0<=y<self.hs and self._in_circle_sub(x,y):
                self.splat_subpixel(x, y, k, rng)

    def render(self):
        # histogram equalization-ish scale
        merged = [f + s for f, s in zip(self.fast, self.slow)]
        if not merged:
            return ""
        vals = sorted(merged)
        q_idx = int(HISTO_EQ_FRACTION*len(vals))-1
        q_idx = clamp(q_idx, 0, len(vals)-1)
        q = vals[q_idx] if vals else 1.0
        if q <= 1e-9: q = max(vals[-1], 1.0)

        # build frame
        out = []
        out.append("\033[H\033[J")  # home + clear
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        out.append(f" Wi-Fi Room Mapper — {stamp}   near≈{int(RSSI_NEAR)} dBm  far≈{int(RSSI_FAR)} dBm    fps≈{int(TARGET_FPS)}\n")
        out.append(" Fast = motion (bright),  Slow = persistent structure (dim). Ray-painted paths; density adaptively scaled.\n")

        # border top
        if BORDER:
            out.append("┌" + "─"*self.wc + "┐\n")
        # rows
        for j in range(self.hc):
            if BORDER: out.append("│")
            line = []
            for i in range(self.wc):
                if not self.cell_mask[j*self.wc + i]:
                    line.append(" ")
                    continue
                # gather 2x4 subpixels -> braille dot mask
                # Braille dots bit layout:
                # (x,y) subcells: (0..1, 0..3)
                # dot numbers:
                # (0,0)->1, (0,1)->2, (0,2)->3, (0,3)->7
                # (1,0)->4, (1,1)->5, (1,2)->6, (1,3)->8
                base_x = i*2; base_y = j*4
                bits = 0
                agg  = 0.0
                for sy in range(4):
                    for sx in range(2):
                        x = base_x+sx; y = base_y+sy
                        idx = self._idx(x, y)
                        v = merged[idx] / q
                        if v > 1: v = 1.0
                        agg += v
                        if v > 0.12:  # threshold to set a dot
                            # map (sx,sy) -> dot bit
                            if sx==0 and sy==0: bits |= 0x01
                            if sx==0 and sy==1: bits |= 0x02
                            if sx==0 and sy==2: bits |= 0x04
                            if sx==0 and sy==3: bits |= 0x40
                            if sx==1 and sy==0: bits |= 0x08
                            if sx==1 and sy==1: bits |= 0x10
                            if sx==1 and sy==2: bits |= 0x20
                            if sx==1 and sy==3: bits |= 0x80
                u = clamp(agg/8.0, 0.0, 1.0)
                col = color_for(u)
                ch = chr(0x2800 + bits) if bits else " "
                line.append(col + ch)
            out.append("".join(line) + "\033[0m")
            if BORDER: out.append("│")
            out.append("\n")
        if BORDER:
            out.append("└" + "─"*self.wc + "┘\n")
        return "".join(out)

class Engine:
    def __init__(self):
        self.cv = BrailleCanvas()
        self.last_draw = 0.0
        self.min_dt = 1.0 / TARGET_FPS
        self.seed_counter = 0
        self.state = {}  # per-mac: {rssi_ema, motion_ema, last_t, last_rssi}
        sys.stdout.write("\033[?25l")  # hide cursor
        sys.stdout.flush()
        try:
            signal.signal(signal.SIGWINCH, lambda *_: self.cv.resize())
        except Exception:
            pass

    def _get_mac_state(self, mac):
        s = self.state.get(mac)
        if s is None:
            s = dict(rssi_ema=None, motion_ema=None, last_t=None, last_rssi=None)
            self.state[mac] = s
        return s

    def ingest(self, mac, rssi, motion):
        # EMA update and dRSSI/dt
        now = time.time()
        st = self._get_mac_state(mac)
        if st["rssi_ema"] is None:
            st["rssi_ema"] = rssi
            st["motion_ema"]= motion
            st["last_t"]    = now
            st["last_rssi"] = rssi
            d_rs = 0.0
        else:
            st["rssi_ema"]  = EMA_RSSI_ALPHA*rssi + (1-EMA_RSSI_ALPHA)*st["rssi_ema"]
            st["motion_ema"]= EMA_MOTION_ALPHA*motion + (1-EMA_MOTION_ALPHA)*st["motion_ema"]
            dt = max(1e-3, now - st["last_t"])
            d_rs = (rssi - st["last_rssi"]) / dt
            st["last_t"] = now
            st["last_rssi"] = rssi

        # how much to “ink” this sample?
        motion_u = max(0.0, st["motion_ema"])
        drssi_u  = clamp(abs(d_rs), 0.0, DRSSI_CLAMP) / DRSSI_CLAMP
        # sample count
        k = BASE_SAMPLES \
            + int(SAMPLES_PER_MOTION * motion_u) \
            + int(SAMPLES_PER_DRSSI * drssi_u)
        if k > MAX_SAMPLES_PER: k = MAX_SAMPLES_PER

        # map to angle/radius
        theta = mac_angle(mac)
        r_pix = rssi_to_radius_pix(st["rssi_ema"], self.cv.R)

        # deposit: rays + jitter
        rng = random.Random(hash((mac, self.seed_counter, int(time.time()*5))))
        # Distribute ink over all micro-deposits
        ink_per = (0.9*motion_u + 0.1*drssi_u) / max(1, k)
        for _ in range(k):
            dth = math.radians(rng.uniform(-JITTER_ARC_DEG, +JITTER_ARC_DEG))
            rr  = r_pix * (1.0 + rng.uniform(-JITTER_R_FRAC, +JITTER_R_FRAC))
            self.cv.deposit_ray(theta + dth, rr, ink_per, rng)
        self.seed_counter += 1

    def tick(self):
        now = time.time()
        # decay both layers
        self.cv.decay(now)
        # draw at target FPS
        if now - self.last_draw >= self.min_dt:
            frame = self.cv.render()
            sys.stdout.write(frame)
            sys.stdout.flush()
            self.last_draw = now

def main():
    eng = Engine()
    try:
        for line in sys.stdin:
            s = line.strip()
            if not s or s.startswith("cnt"):
                eng.tick()
                continue
            parts = s.split(",")
            if len(parts) < 3: 
                eng.tick()
                continue
            mac = parts[0].strip().lower()
            try:
                rssi   = float(parts[1])
                motion = float(parts[2])
            except ValueError:
                eng.tick()
                continue
            eng.ingest(mac, rssi, motion)
            eng.tick()
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\033[0m")  # show cursor, reset color
        sys.stdout.flush()

if __name__ == "__main__":
    main()
