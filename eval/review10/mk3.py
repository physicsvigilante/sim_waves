S="f: 500 Hz, A: 1, phase: 0, spreading: none"
def med(v=340,w=None): return "media: {air: {type: gas, v: %s m/s%s}}"%(v, (", wind: %s"%w) if w else "")
scenes={
"c1_perp": f"""
{med()}
sources: {{car: {{on: air, at: [-100 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}}}
points: {{O: [0 m, 50 m], M: {{at: [0 m, 50 m], velocity: [0 m/s, -12 m/s]}}}}
rays: {{r: {{from: car, to: O}}, m: {{from: car, to: M}}}}
observe:
  t5: "frequency(r, t=5[s])"    # 501.7361
  e5: "frequency(r, emitted=5[s])"   # 500
  arr5: "arrives_at(r, emitted=5[s])"  # 5.1470588
  t1: "frequency(r, t=1[s])"   # 526.776
  t12: "frequency(r, t=12[s])"  # 473.936
  te5: "emitted_at(r, t=5[s])"  # 4.852686
  m2: "frequency(m, t=2[s])"   # 535.8427
  m7: "frequency(m, t=7[s])"   # 467.7946
  mte: "emitted_at(m, t=7[s])"  # 6.852116
  rt: "arrives_at(m, emitted=emitted_at(m, t=7[s]))"
""",
"c2_windangle": f"""
{med(w='[6 m/s, 8 m/s]')}
sources: {{car: {{on: air, at: [-100 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}}}
points: {{O: [0 m, 50 m]}}
rays: {{r: {{from: car, to: O}}}}
observe:
  t3: "frequency(r, t=3[s])"    # 519.6163
  arr5: "arrives_at(r, emitted=5[s])"  # 5.1437000
  e5: "frequency(r, emitted=5[s])"   # 499.49326
  wl: "wavelength(r, t=3[s])"
""",
"c4_3d": f"""
{med()}
sources: {{car: {{on: air, at: [-100 m, 0 m, 0 m], velocity: [20 m/s, 0 m/s, 5 m/s], {S}}}, z: {{on: air, at: [0 m, 0 m, 0 m], velocity: [0 m/s, 0 m/s, 30 m/s], {S}}}}}
points: {{M: {{at: [0 m, 50 m, 30 m], velocity: [3 m/s, -12 m/s, 4 m/s]}}, Z: [0 m, 0 m, 100 m]}}
rays: {{r: {{from: car, to: M}}, z: {{from: z, to: Z}}}}
observe:
  t2: "frequency(r, t=2[s])"    # 529.78123
  t9: "frequency(r, t=9[s])"    # 472.91242
  te9: "emitted_at(r, t=9[s])"  # 8.7685118
  arr1: "arrives_at(r, emitted=1[s])"  # 1.28112772
  z: "frequency(z, emitted=0[s])"   # 548.387
  d: "distance(car, M, t=2[s])"
""",
"c5_3dwind": f"""
{med(w='[5 m/s, -7 m/s, 9 m/s]')}
sources: {{car: {{on: air, at: [-100 m, 0 m, 0 m], velocity: [20 m/s, 0 m/s, 5 m/s], {S}}}}}
points: {{M: {{at: [0 m, 50 m, 30 m], velocity: [3 m/s, -12 m/s, 4 m/s]}}}}
rays: {{r: {{from: car, to: M}}}}
observe:
  t2: "frequency(r, t=2[s])"    # 529.71585
  t9: "frequency(r, t=9[s])"    # 472.88206
""",
"c6_wind2d_3dpos": f"""
{med(w='[5 m/s, -7 m/s]')}
sources: {{car: {{on: air, at: [-100 m, 0 m, 0 m], velocity: [20 m/s, 0 m/s, 5 m/s], {S}}}}}
points: {{M: [0 m, 50 m, 30 m]}}
rays: {{r: {{from: car, to: M}}}}
observe:
  t2: "frequency(r, t=2[s])"    # refuse
""",
"d1_circ": f"""
{med()}
sources: {{toy: {{on: air, at: [2 m, 0 m], circle: {{center: [0 m, 0 m], speed: 30 m/s, sense: ccw}}, {S}}}, lin: {{on: air, at: [-50 m, 1 m], velocity: [25 m/s, 0 m/s], {S}}}}}
points: {{O: [10 m, 0 m], C: {{at: [10 m, 3 m], circle: {{center: [10 m, 0 m], speed: 20 m/s, sense: cw}}}}}}
rays: {{r: {{from: toy, to: O}}, b: {{from: toy, to: C}}, l: {{from: lin, to: C}}}}
observe:
  a: "frequency(r, t=0.3[s])"    # 530.97322
  b: "frequency(r, t=1[s])"      # 465.07605
  te: "emitted_at(r, t=1[s])"    # 0.96792872
  arr: "arrives_at(r, emitted=0.2[s])"  # 0.235245027
  rt: "arrives_at(r, emitted=emitted_at(r, t=1[s]))"
  both1: "frequency(b, t=0.3[s])"   # 544.25071
  both2: "frequency(b, t=1[s])"     # 436.47190
  l1: "frequency(l, t=0.5[s])"      # 571.08561
  l2: "frequency(l, t=3[s])"        # 477.42890
  fe: "frequency(b, emitted=0.2[s])"
  wl: "wavelength(r, t=1[s])"
""",
"d4_circwind": f"""
{med(w='[8 m/s, -5 m/s]')}
sources: {{toy: {{on: air, at: [2 m, 0 m], circle: {{center: [0 m, 0 m], speed: 30 m/s, sense: ccw}}, {S}}}}}
points: {{O: [10 m, 0 m], C: {{at: [10 m, 3 m], circle: {{center: [10 m, 0 m], speed: 20 m/s, sense: cw}}}}}}
rays: {{r: {{from: toy, to: O}}, b: {{from: toy, to: C}}}}
observe:
  a: "frequency(r, t=0.3[s])"    # 530.00073
  b: "frequency(b, t=1[s])"      # 437.88224
""",
"e1_starts": f"""
{med(350)}
sources: {{S: {{on: air, at: [0 m, 0 m], velocity: [10 m/s, 0 m/s], starts: 5 s, emits_from: 0 s, {S}}}}}
points: {{P: [100 m, 40 m], M: {{at: [100 m, 40 m], velocity: [-20 m/s, 5 m/s], starts: 2 s}}, X: [350 m, 0 m]}}
rays: {{r: {{from: S, to: P}}, m: {{from: S, to: M}}, x: {{from: S, to: X}}}}
observe:
  a: "frequency(r, t=5.2[s])"   # 500
  b: "frequency(r, t=5.4[s])"   # 513.60688
  c: "frequency(r, t=9[s])"     # 512.30613
  m1: "frequency(m, t=1[s])"    # 500
  m3: "frequency(m, t=3[s])"    # 521.40029
  m8: "frequency(m, t=8[s])"    # 470.47424
  mte: "emitted_at(m, t=8[s])"  # 7.7581699
  early: "frequency(x, t=0.9[s])"   # no sound yet (arrives at 1.0)
  just: "frequency(x, t=1.001[s])"  # 500
  exact: "frequency(x, t=1[s])"     # te = 0 = emits_from: ok 500 or refuse
  before: "frequency(x, emitted=-1[s])"  # no sound
  jump: "frequency(x, t=6[s])"   # emitted exactly at 5s: refuse
  at5: "frequency(x, t=5[s])"    # source starts at t=5; listener hears te=4 -> 500
  post: "frequency(x, t=6.5[s])"  # 500*350/340 = 514.7059
  d4: "distance(S, M, t=4[s])"
""",
}
for k,v in scenes.items():
    open(k+".yaml","w").write(v)
