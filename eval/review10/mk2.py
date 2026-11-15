S="f: 500 Hz, A: 1, phase: 0, spreading: none"
scenes={
"b1_car_wall": f"""
media: {{air: {{type: gas, v: 340 m/s}}}}
sources: {{car: {{on: air, at: [0 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}, st: {{on: air, at: [0 m, 0 m], {S}}}}}
points: {{drv: {{at: [0 m, 0 m], velocity: [20 m/s, 0 m/s]}}, P: [-10 m, 0 m], Q: [10 m, 0 m], beyond: [900 m, 0 m]}}
reflectors:
  wall: {{point: [500 m, 0 m], normal: [-1, 0], boundary: rigid}}
  rec: {{point: [500 m, 0 m], normal: [-1, 0], boundary: rigid, velocity: [10 m/s, 0 m/s]}}
  app: {{point: [500 m, 0 m], normal: [-1, 0], boundary: rigid, velocity: [-5 m/s, 0 m/s]}}
  appflip: {{point: [500 m, 0 m], normal: [1, 0], boundary: rigid, velocity: [-5 m/s, 0 m/s]}}
rays:
  e: {{from: car, to: drv, via: wall}}
  own: {{from: car, to: drv}}
  r: {{from: st, to: P, via: rec}}
  rq: {{from: st, to: Q, via: rec}}
  a: {{from: car, to: drv, via: app}}
  af: {{from: car, to: drv, via: appflip}}
  ap: {{from: st, to: P, via: app}}
  eP: {{from: car, to: P, via: wall}}
  dP: {{from: car, to: P}}
observe:
  echo: "frequency(e, t=5[s])"     # 562.5
  own: "frequency(own, t=5[s])"    # 500
  beat: "beat_frequency(e, own, t=5[s])"  # 62.5
  rec: "frequency(r, t=5[s])"      # 500*330/350 = 471.4286
  recq: "frequency(rq, t=5[s])"    # same
  app: "frequency(a, t=5[s])"      # 500*345/320*360/335 = 579.29
  appflip: "frequency(af, t=5[s])"
  app_still: "frequency(ap, t=5[s])"  # 500*345/335=514.925
  eP: "frequency(eP, t=5[s])"      # 500*340/320=531.25
  dP: "frequency(dP, t=5[s])"      # 500*340/360=472.22
  beatP: "beat_frequency(eP, dP, t=5[s])" # 59.03
  late: "frequency(a, t=30[s])"    # car hits wall at t=20: must refuse
  rec_arr: "arrives_at(r, emitted=0[s])"  # wall hit: 500+10T=340T -> T=500/330; wall at 515.15; back to -10: 525.15/340 -> 3.0597
  wl_echo: "wavelength(a, t=5[s])"   # in air after reflection: f_refl(air)=500*345/320*340/335 ; lam = 340/that
  early: "frequency(e, t=0.5[s])"   # echo not yet arrived? source emitting for ever -> fine
""",
"b2_echo_wind": f"""
media: {{air: {{type: gas, v: 340 m/s, wind: [10 m/s, 0 m/s]}}}}
sources: {{car: {{on: air, at: [0 m, 0 m], velocity: [20 m/s, 0 m/s], {S}}}, st: {{on: air, at: [0 m, 0 m], {S}}}}}
points: {{P: [-50 m, 0 m], drv: {{at: [0 m, 0 m], velocity: [20 m/s, 0 m/s]}}}}
reflectors:
  wall: {{point: [500 m, 0 m], normal: [-1, 0], boundary: rigid}}
  app: {{point: [500 m, 0 m], normal: [-1, 0], boundary: rigid, velocity: [-5 m/s, 0 m/s]}}
rays:
  s: {{from: st, to: P, via: wall}}
  e: {{from: car, to: P, via: wall}}
  d: {{from: car, to: P}}
  ed: {{from: car, to: drv, via: wall}}
  am: {{from: st, to: P, via: app}}
observe:
  still: "frequency(s, t=5[s])"   # 500
  arr: "arrives_at(s, emitted=0[s])"  # 500/350 + 550/330 = 3.0952
  echo: "frequency(e, t=5[s])"    # 500*350/330 = 530.303
  direct: "frequency(d, t=5[s])"  # 500*330/350 = 471.4286
  beat: "beat_frequency(e, d, t=5[s])"
  drv: "frequency(ed, t=5[s])"    # 500*350/330 * (330+20)/330 = 562.44
  am: "frequency(am, t=5[s])"     # wall hears 500*(350+5)/350; re-emits toward -x: sound speed 330; f*(330)/(330-5) => 500*355/350*330/325 = 514.945
""",
}
for k,v in scenes.items():
    open(k+".yaml","w").write(v)
