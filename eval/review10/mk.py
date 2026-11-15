import sys,subprocess,os,textwrap
S="f: 500 Hz, A: 1, phase: 0, spreading: none"
scenes={
"a1_both": f"""
media: {{air: {{type: gas, v: 340 m/s}}}}
sources: {{car: {{on: air, at: [-100 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}}}
points: {{bike: {{at: [80 m, 0 m], velocity: [-15 m/s, 0 m/s]}}}}
rays: {{r: {{from: car, to: bike}}}}
observe:
  before: "frequency(r, emitted=0[s])"      # 554.6875
  before_t: "frequency(r, t=1[s])"          # 554.6875
  after: "frequency(r, t=20[s])"            # 451.3889
  after_e: "frequency(r, emitted=20[s])"
  atcross: "frequency(r, t=180/35[s])"
  te: "emitted_at(r, t=20[s])"
  rt: "arrives_at(r, emitted=emitted_at(r, t=20[s]))"   # 20
  rt2: "emitted_at(r, t=arrives_at(r, emitted=1[s]))"   # 1
  straddle: "frequency(r, t=5.3[s])"   # emitted before crossing? heard after crossing
  wl: "wavelength(r, emitted=0[s])"   # (340-20)/500=0.64
  wl2: "wavelength(r, t=20[s])"       # 360/500=0.72
  d: "distance(car, bike, t=2[s])"    # 110
  per: "period(r)"
  kk: "k(r)"
  om: "omega(r)"
  L: "length(r)"
""",
"a2_same": f"""
media: {{air: {{type: gas, v: 340 m/s}}}}
sources: {{car: {{on: air, at: [0 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}}}
points: {{bike: {{at: [100 m, 0 m], velocity: [10 m/s, 0 m/s]}}, chase: {{at: [-100 m, 0 m], velocity: [30 m/s, 0 m/s]}}}}
rays: {{r: {{from: car, to: bike}}, c: {{from: car, to: chase}}}}
observe:
  ahead: "frequency(r, emitted=0[s])"      # 515.625
  ahead_late: "frequency(r, t=30[s])"      # source passed listener at t=10: f(340+10)/(340+20)=486.11
  chase: "frequency(c, t=1[s])"            # f (340+30)/(340+20) = 513.889
""",
"a3_wind": f"""
media: {{air: {{type: gas, v: 340 m/s, wind: [10 m/s, 0 m/s]}}}}
sources: {{car: {{on: air, at: [0 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}, st: {{on: air, at: [0 m, 0 m], {S}}}}}
points: {{O: [1000 m, 0 m], B: [-1000 m, 0 m], bike: {{at: [1000 m, 0 m], velocity: [-15 m/s, 0 m/s]}}}}
rays: {{r: {{from: car, to: O}}, b: {{from: car, to: B}}, s: {{from: st, to: bike}}, so: {{from: st, to: O}}}}
observe:
  along: "frequency(r, emitted=0[s])"      # 500*350/330=530.303
  against: "frequency(b, emitted=0[s])"    # 500*330/350=471.4286
  lis: "frequency(s, emitted=0[s])"        # 500*365/350=521.4286
  still: "frequency(so, t=10[s])"          # 500
  wl_still: "wavelength(so, t=10[s])"      # air frame: 340/ f_air; f_air = 500*340/350 -> lambda=0.70
  wl_along: "wavelength(r, emitted=0[s])"  # (350-20)/500 = 0.66
  wl_against: "wavelength(b, emitted=0[s])"  # (330+20)/500=0.70
  arr: "arrives_at(so, emitted=0[s])"      # 1000/350
  f0: "frequency(so)"
  L: "length(so)"
  pd: "path_difference(so, r)"
  ri: "relative_intensity(so)"
""",
}
for k,v in scenes.items():
    open(k+".yaml","w").write(v)
