S="f: 500 Hz, A: 1, phase: 0, spreading: none"
def med(v=340,w=None): return "media: {air: {type: gas, v: %s m/s%s}}"%(v, (", wind: %s"%w) if w else "")
scenes={
# unknown source speed from beats: two forks f=500; one still near listener, one moving away at u; beats 10 Hz: 500 - 500*340/(340+u)=10 -> u=340*10/490=6.93878
"f1_unknown_u": f"""
{med()}
unknowns: {{u: positive}}
sources: {{a: {{on: air, at: [-1 m, 0 m], {S}}}, b: {{on: air, at: [10 m, 0 m], velocity: [u, 0 m/s], {S}}}}}
points: {{O: [0 m, 0 m]}}
rays: {{ra: {{from: a, to: O}}, rb: {{from: b, to: O}}}}
given:
  - {{fact: "beat_frequency(ra, rb, t=1[s]) == 10[Hz]", source: stated}}
observe: {{u: "u"}}
""",
# same but velocity sign unknown (real): ambiguous -> two solutions (approach u=-340*10/510=-6.667, recede 6.9388)
"f2_unknown_u_real": f"""
{med()}
unknowns: {{u: real}}
sources: {{a: {{on: air, at: [-1 m, 0 m], {S}}}, b: {{on: air, at: [1000 m, 0 m], velocity: [u, 0 m/s], {S}}}}}
points: {{O: [0 m, 0 m]}}
rays: {{ra: {{from: a, to: O}}, rb: {{from: b, to: O}}}}
given:
  - {{fact: "beat_frequency(ra, rb, t=5[s]) == 10[Hz]", source: stated}}
observe: {{u: "u"}}
""",
# unknown wall speed: still source+listener, wall approaching at u: f' = f (v+u)/(v-u) = 520 -> u = 340*20/1020 = 6.6667
"f3_unknown_wall": f"""
{med()}
unknowns: {{u: positive}}
sources: {{a: {{on: air, at: [0 m, 0 m], {S}}}}}
points: {{O: [1 m, 0 m]}}
reflectors: {{wall: {{point: [500 m, 0 m], normal: [-1, 0], boundary: rigid, velocity: [-u, 0 m/s]}}}}
rays: {{e: {{from: a, to: O, via: wall}}, d: {{from: a, to: O}}}}
given:
  - {{fact: "frequency(e, t=5[s]) == 520[Hz]", source: stated}}
observe: {{u: "u", beats: "beat_frequency(e, d, t=5[s])"}}
""",
# symbolic speeds: result formula
"f4_symbolic": f"""
{med()}
symbols: {{vs: positive, vo: positive, D: positive}}
sources: {{a: {{on: air, at: [0 m, 0 m], velocity: [vs, 0 m/s], {S}}}}}
points: {{O: {{at: [D, 0 m], velocity: [-vo, 0 m/s]}}}}
rays: {{r: {{from: a, to: O}}}}
observe: {{f: "frequency(r, emitted=0[s])", ft: "frequency(r, t=1[s])", arr: "arrives_at(r, emitted=0[s])"}}
""",
# arbitrary + Doppler ratio; and one depending on arbitrary
"f5_arbitrary": f"""
{med()}
arbitrary: {{D: 100 m, f0: 400 Hz}}
sources: {{a: {{on: air, at: [0 m, 0 m], velocity: [34 m/s, 0 m/s], f: f0, A: 1, phase: 0, spreading: none}}}}
points: {{O: [D, 0 m], B: [-D, 0 m], side: [0 m, D]}}
rays: {{r: {{from: a, to: O}}, b: {{from: a, to: B}}, s: {{from: a, to: side}}}}
observe:
  ratio: "frequency(r, emitted=0[s])/frequency(b, emitted=0[s])"   # (374)/(306) = 11/9
  dep: "frequency(r, emitted=0[s])"       # depends on f0
  wlr: "wavelength(r, emitted=0[s])/wavelength(b, emitted=0[s])"  # 9/11
  fixt: "frequency(r, t=5[s])/frequency(b, t=5[s])"   # at D*89 source hasn't passed; at D/97 passed -> depends
  side: "frequency(s, emitted=0[s])/frequency(a)"   # 1
""",
# beat between rays of different sources with different f, moving
"f6_beat_two": f"""
{med()}
sources:
  a: {{on: air, at: [-100 m, 0 m], velocity: [17 m/s, 0 m/s], f: 500 Hz, A: 1, phase: 0, spreading: none}}
  b: {{on: air, at: [100 m, 0 m], velocity: [17 m/s, 0 m/s], f: 510 Hz, A: 1, phase: 0, spreading: none}}
points: {{O: [0 m, 0 m]}}
rays: {{ra: {{from: a, to: O}}, rb: {{from: b, to: O}}}}
observe:
  beat: "beat_frequency(ra, rb, t=1[s])"   # 500*340/323=526.316 ; 510*340/357=485.714 -> 40.602
  nob: "beat_frequency(ra, rb)"
  mix: "beat_frequency(ra, 500[Hz], t=1[s])"
  ri: "relative_intensity(ra, rb)"
  pd: "phase_difference(ra, rb)"
  mx: "resultant_amplitude(ra, rb)"
  amp: "amplitude(ra)"
  ph: "phase(ra, t=1[s])"
""",
# still wall off line with moving source: image method. source moving parallel to wall: (x=-100+20t, y=10), wall y=0, listener (0,30): image at y=-10
"g1_image": f"""
{med()}
sources: {{car: {{on: air, at: [-100 m, 10 m], velocity: [20 m/s, 0 m/s], {S}}}}}
points: {{O: [0 m, 30 m]}}
reflectors: {{wall: {{point: [0 m, 0 m], normal: [0, 1], boundary: rigid}}, mv: {{point: [0 m, 0 m], normal: [0, 1], boundary: rigid, velocity: [0 m/s, 1 m/s]}}, bad: {{point: [0 m, 0 m], normal: [0, 1], boundary: rigid, velocity: [1 m/s, 0 m/s]}}}}
rays: {{e: {{from: car, to: O, via: wall}}, m: {{from: car, to: O, via: mv}}}}
observe:
  e: "frequency(e, t=2[s])"
  e5: "frequency(e, emitted=5[s])"    # 500
  m: "frequency(m, t=2[s])"   # refuse
""",
"g2_image_wind": f"""
{med(w='[0 m/s, 3 m/s]')}
sources: {{car: {{on: air, at: [-100 m, 10 m], velocity: [20 m/s, 0 m/s], {S}}}}}
points: {{O: [0 m, 30 m]}}
reflectors: {{wall: {{point: [0 m, 0 m], normal: [0, 1], boundary: rigid}}}}
rays: {{e: {{from: car, to: O, via: wall}}}}
observe:
  e: "frequency(e, t=2[s])"   # refuse
""",
"h1_supersonic": f"""
{med()}
sources: {{car: {{on: air, at: [-100 m, 0 m], velocity: [340 m/s, 0 m/s], {S}}}, w: {{on: air, at: [-100 m, 0 m], velocity: [300 m/s, 200 m/s], {S}}}, c: {{on: air, at: [2 m, 0 m], circle: {{center: [0 m, 0 m], speed: 400 m/s, sense: ccw}}, {S}}}, ok: {{on: air, at: [0 m, 0 m], {S}}}}}
points: {{O: [0 m, 50 m], F: {{at: [0 m, 50 m], velocity: [0 m/s, -350 m/s]}}}}
reflectors: {{wall: {{point: [0 m, 500 m], normal: [0, -1], boundary: rigid, velocity: [0 m/s, -400 m/s]}}}}
rays: {{r: {{from: car, to: O}}, w: {{from: w, to: O}}, c: {{from: c, to: O}}, f: {{from: ok, to: F}}, wl: {{from: ok, to: O, via: wall}}}}
observe:
  a: "frequency(r, t=1[s])"
  b: "frequency(w, t=1[s])"
  c: "frequency(c, t=1[s])"
  d: "frequency(f, t=0.01[s])"
  e: "frequency(wl, t=0.01[s])"
""",
# supersonic relative to air because of wind: source 330 with headwind -20
"h2_super_wind": f"""
{med(w='[-20 m/s, 0 m/s]')}
sources: {{car: {{on: air, at: [-100 m, 0 m], velocity: [330 m/s, 0 m/s], {S}}}}}
points: {{O: [0 m, 0 m]}}
rays: {{r: {{from: car, to: O}}}}
observe:
  a: "frequency(r, emitted=0[s])"
""",
# stated-length ray from moving source; listener co-located
"h3_leaks": f"""
{med()}
sources: {{car: {{on: air, at: [-100 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}}}
points: {{O: [0 m, 0 m], same: {{at: [-100 m, 0 m], velocity: [20 m/s, 0 m/s]}}, here: [-100 m, 0 m]}}
rays: {{tube: {{from: car, length: 3 m}}, own: {{from: car, to: same}}, r: {{from: car, to: O}}, h: {{from: car, to: here}}}}
observe:
  a: "frequency(tube)"
  b: "frequency(tube, t=1[s])"
  own: "frequency(own, t=1[s])"
  ownL: "length(own)"
  per: "period(r)"
  h0: "frequency(h, t=0[s])"
  h1: "frequency(h, emitted=0[s])"
  h2: "frequency(h, t=1[s])"   # source moved away from 'here': 500*340/360
  fsrc: "frequency(car)"
  srct: "frequency(car, t=1[s])"
  both: "frequency(r, t=1[s], emitted=0[s])"
  dist: "distance(car, O)"
""",
# wall overtakes listener / source crosses wall
"h4_wallcross": f"""
{med()}
sources: {{st: {{on: air, at: [0 m, 0 m], {S}}}}}
points: {{P: [50 m, 0 m], N: [-50 m, 0 m]}}
reflectors: {{app: {{point: [200 m, 0 m], normal: [-1, 0], boundary: rigid, velocity: [-5 m/s, 0 m/s]}}}}
rays: {{e: {{from: st, to: P, via: app}}, n: {{from: st, to: N, via: app}}}}
observe:
  ok: "frequency(e, t=5[s])"     # 500*345/335
  past_listener: "frequency(e, t=35[s])"   # wall at 25 < P=50: P behind wall: refuse
  past_source: "frequency(e, t=50[s])"   # wall at -50: refuse
  n_past_source: "frequency(n, t=45[s])"  # wall at -25, between N and source: refuse
  arr: "arrives_at(e, emitted=29.9[s])"    # wall at 50.5 ; fine. 
  arr2: "arrives_at(e, emitted=35[s])"    # wall at 25, P behind -> refuse
""",
}
for k,v in scenes.items():
    open(k+".yaml","w").write(v)
