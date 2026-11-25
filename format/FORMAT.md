# sim_waves scene format, v0.1

The engine in `../engine` implements exactly what is written here. Worked scenes are in
`examples/`; scenes that must be rejected are in `../engine/tests/`.

## The split

- **Engine:** physics only. Media, waves, sources, the resulting field, physical
  observables, and neutral maths services (solve, differentiate, maximise, check two
  expressions are equal).
- **LLM:** framing. Reads the problem and figure, picks the model, states assumptions,
  chooses which observables answer the question, and handles options, matrix matching
  and explanations.
- **Rule:** the LLM never writes a physics formula such as v = sqrt(T/mu) or
  P = (1/2) mu w^2 A^2 v. If it needs one, an observable is missing from the engine.

## File layout

```yaml
id: 22/01/cnt_004        # corpus id
assume: [...]            # the LLM's framing choices, in words, for a human to audit
symbols: {a: positive}   # free parameters: positive | real | integer | phase
unknowns: {k: positive}  # solved from `given`: positive | real | integer | phase | direction
functions: [F]           # arbitrary profiles, e.g. F(x - c*t)
media: {...}
waves: {...}
emitters: {...}
given: [...]             # equations (==) and inequalities the scene must satisfy
observe: {...}           # named expressions to evaluate
illustrate: {...}        # values for symbols, used ONLY for drawing (see Views)
view: [...]              # panels to draw (see Views)
explore: {...}           # one physical input to vary (see Views)
expect: {...}            # TEST HARNESS ONLY: the book answer; never read by the engine
```

Each `given` item is either a string or a tagged fact:

```yaml
given:
  - {fact: "y(w1, x=0, t=0) == 0", source: figure}      # stated | figure | convention | assumption
  - {fact: "wavelength(w) > 2[cm]", source: assumption, note: "points less than half a wavelength apart"}
```

Tag every fact. Untagged facts are allowed, but they are reported as `untagged`.

Unknown keys anywhere are rejected (so `lamda:` is an error, not ignored).
Write YAML booleans only as `true`/`false`; `on`, `yes`, `no` are plain words.

## Values and units

- **Scene fields:** a number with a unit, e.g. `0.2 m`, `50 g/m`, `30 degC`,
  `3*pi rad/s`, `1.7e-5 1/K`.
  - A bare number in a dimensional field is an error ("needs a unit").
  - A wrong dimension (e.g. `A: 5 Hz`) is an error.
  - Symbols need no unit.
  - A field may also be an expression with unit brackets, e.g.
    `tension: "9[kg]*9.8[m/s^2]"`; its dimension is checked.
  - **Quoting:** inside `{...}` or `[...]` (YAML flow style), quote any value that
    contains unit brackets: `{length: "(3/4)[m]"}`. Unquoted, YAML rejects it.
- **Inside `given` and `observe`:** units go in brackets, e.g. `10[cm]`, `tan(60[deg])`,
  `100[W]`.
  - Sums and comparisons must agree in dimension: `power(w) == 100[m]` is rejected.
  - `x` and `t` written freely in a formula count as SI numbers, so book formulas such as
    `0.2*sin(2*pi*(6*t - x/60))` are fine.
  - The `x=`, `t=`, `at=` and `r=` arguments must be lengths or times.
- **Every part as written must be defined (real and finite).** Each log, root, power,
  division, tan, asin/acos and wave value written in an `observe`, a `given` fact, a limit
  or a field with units, and each such part inside an observable's result (the log in
  `sound_level`), is checked, even if it cancels: `log(-1) - log(-2)` is refused although
  SymPy would give -log 2. In an observe, the condition must hold with the solved values
  (or it is refused); in a fact, the solution must satisfy it (it can rule out candidates:
  `d*(d-1) + 1/d - 1/d == 0` gives d = 1); a field must satisfy it when read, or after the
  solve if it involves an unknown. A power with an unknown exponent is decided once it is
  known: `0**q` is 0 for q = 2 and refused for q = -1.
  - `field(w)` carries the wave's written conditions: `at(field(w), x=..., t=...)` checks them
    at those values. `max_over`, `min_over`, `mean_over`, `max_in`, `min_in` and
    `frequency_of` need the expression defined for every value in their range. Their
    variable and expression are positional; only `lo=` and `hi=` may be keywords.
- **Units:** m, cm, mm, um (also μm), nm, km, s, ms, us, ns, h, kg, g, N, Pa, kPa, J, mJ, W, mW, kW, Hz, kHz, MHz, GHz, rad, deg, K, degC; km/h is `km/h` or `kmph`.
  - `h` (hour) works inside a compound unit (`36 km/h`, `36[km/h]`) or in brackets
    (`2[h]`). A lone `h` after a value (`3 h`) is not read as hours: it is too often a
    height.
  - A written zero takes its bracket's unit: `"0[m]"` is a length (and `"0[s]"` is not).
  - `degC` is not allowed inside brackets: `20[degC]` could be a temperature or a
    difference. Write temperatures in K (`293.15[K]`) and differences as `20[K]`. A
    field (`now: 30 degC`) and a result `in degC` are fine.
  - An absolute Celsius temperature must be written exactly as `degC` (`27 degC`): any other
    spelling of it, such as `27 (degC)`, `27 degC^1` or `27 degC*m/m`, is refused, because the
    273.15 K offset is tied to that spelling. Inside a compound unit, degC is a temperature
    difference and keeps working: `alpha: 1.7e-5 1/degC` is the same as `1/K`.
- **Internals:** the engine works in exact SI.

## Media

```yaml
type: string | gas | fluid | rod | open3d   # gas, fluid, rod: see Sound media
# string, mass per length: mu, or mass + length, or density + area|diameter
# (giving more than one is cross-checked)
tension: 60 N
tension: {hanging: {load: M, g: g}} # needs coordinate {origin: lower_end, direction: up, variable: s}
coordinate: {origin: left_end, direction: right, variable: s}   # s: a symbol declared in `symbols`
mu: "mu0 + alpha*s"                 # mu may vary with the coordinate variable (non-uniform string)
# hanging tension = load*g + g * (integral of mu below s); speed(m, at=...) and front(pulse, t=)
# integrate along the string. A symbol used in mu AND as a position must be the variable.
tension: {thermal: {slack_at: 30 degC, now: 10 degC}}   # needs Y, alpha, density
tension: {weight: {mass: 4 kg, g: 9.8 m/s^2}}              # T = M g (a hanging load); g as the problem states it
tension: {weight: {mass: 4 kg, g: 9.8 m/s^2,               # immersed load: T = M g - rho_f V g
                   buoyancy: {fluid_density: 1000 kg/m^3, volume: 5e-4 m^3}}}
#   or buoyancy: {fluid_density: ..., load_density: ..., fraction: 1/2}  (fraction immersed, default 1)
#   a load that would float is refused; mass, g, k, Y and lengths must be positive
#   (unknowns get these as conditions); a stated area within 1 % of the string's own is accepted
tension: {stretch: {Y: 2e11 Pa, extension: 1 mm, length: 2 m}}   # T = Y A dL/L0; area here or on the string
tension: {stretch: {k: 400 N/m, extension: 10 cm}}         # a spring: T = k dL
tension: free                       # the wave's speed fixes it
ends: {left: driven, right: absorbing}   # for fixed/free ends and joins, use `junctions`
```

## Waves

```yaml
# 1. harmonic: give any consistent subset; the engine completes it and cross-checks the rest
w: {harmonic: {on: rope, A: 1 cm, f | omega | period, lambda | k, v,
               dir: +x | -x | <direction unknown>   (or  from: left | right | <origin>),
               phase: 0}}
# 2. given: an explicit y(x,t); units for x, t AND y are required. Each log, root, division,
#    tan or asin/acos written in the profile is checked wherever the wave is evaluated, even
#    if it cancels: log(x - t) - log(x - t) is refused at x < t (and is 0 at x > t), a
#    profile with poles is refused at a pole, and sqrt(x - t) at x < t is refused. This
#    holds for y, vy, ay, slope, phase, energy densities, at(field(w), ...) and sums.
p: {given: "3/(2 + (x - 4*t)**2)", units: {x: m, t: s, y: m}, on: rope}
# 3. pulse on a string, launched from the coordinate origin (any origin, e.g. a horizontal rope:
#    coordinate: {origin: left_end, direction: right, variable: s} and from: left_end, toward: right)
p: {pulse: {on: rope, from: lower_end, toward: up}}
# 4. pulse with a shape: y(x, 0) as a formula in x; it moves at the string's speed
p: {pulse: {on: a, shape: "0.01*max(0, 1 - abs(x - 0.5)/0.1)", units: {x: m, y: m}, dir: +x}}
# a pulse without a shape has only a front position (front(p, t=...)) and cannot meet a junction
```

- **Phase convention:** `y = A sin(omega*t - d*k*x + phase)`, where `d = +1` for +x and
  `-1` for -x. `phase(w,x,t)` returns the argument of the sine, which always increases
  with time.
  - Converting textbook forms:
    - `A sin(kx - wt + phi)` = `A sin(wt - kx - phi + pi)`, so use `phase: pi - phi`;
    - `A sin(kx + wt + phi)` is dir -x with `phase: phi`;
    - `A cos(...)` adds pi/2.
  - If in doubt, give the wave as `given:` with the book's own formula and `on:` its
    string.
- **Direction:** if it is unknown, declare `unknowns: {d: direction}` and use `dir: d`.
  The solver tries both directions.
- **Cross-checks:** `omega = k*v`, the medium's speed, and a `given` formula's speed
  against its medium are all checked. If a check can't be decided yet, it becomes a fact
  for the solver.
- **No silent defaults:** if a result needs A, phase, etc. and the scene never fixed it,
  the scene is rejected as undetermined.

## Superposition

```yaml
waves:
  total: {sum: [y1, y2]}        # field = sum of fields of waves defined ABOVE
```

A sum is analysed like a `given` wave:
- **Same frequency and wavenumber:** the parts combine (phasors) into one wave with an
  amplitude and a phase.
- **Complete cancellation:** `amplitude` is 0; phase, frequency and wavelength are then
  undefined (an error).
- **All parts must live on one medium.** Waves on different strings cannot be summed.
- **Different frequencies, or opposite directions** (a standing wave): there is no single
  amplitude. Ask about a point instead, e.g.
  `max_over(t, abs(y(total, x=..., t=t)))` or `frequency_of(t, y(total, x=..., t=t))`.

## Junctions and string ends (reflection, transmission)

```yaml
media:
  s1: {type: string, mu: mu1, tension: T}
  s2: {type: string, mu: mu2, tension: T}
junctions:
  J:    {at: 0 m, left: s1, right: s2}       # two strings joined at x = 0
  wall: {at: 2 m, left: s2, right: fixed}    # or free
waves:
  w: {harmonic: {on: s1, A: 2 cm, f: f, dir: +x, phase: 0}}   # travelling toward J
```

- **Derived waves:** a harmonic wave travelling toward a junction creates
  `w_reflected` (and `w_transmitted` if the other side is a string). Only waves written
  as `harmonic:` are reflected; a `given:` wave on a string with a junction is an error. These are ordinary
  waves: use amplitude, phase, wavelength, velocity on them, or `sum` them with `w`
  (e.g. a standing wave = `sum: [w, w_reflected]`).
- **Coefficients come from the string impedances** sqrt(T*mu):
  - displacement is continuous at the junction;
  - a fixed end reflects with r = -1, a free end with r = +1;
  - energy conservation at each junction is checked as a fact.
- **Shaped pulses** also create `p_reflected` and `p_transmitted` at a junction or a
  fixed/free end, by the image method:
  - same coefficients as harmonic waves;
  - the transmitted pulse is v2/v1 as wide;
  - a fixed end inverts.

  Two conditions apply:
  - The pulse must start entirely on its own string. If more than 0.1% of its peak lies
    past the junction at t = 0, it is refused.
  - Shaped pulses need uniform strings (on a non-uniform string the pulse does not keep
    its shape).

  `sum: [p, p_reflected]` gives the string while incident and reflected pulses overlap.
  - Only one reflection is modelled. If a reflected or transmitted pulse would run into a
    further junction or end on its string, the scene is refused: model one junction per
    scene.
- **Extents:** a string is limited by its junctions. Evaluating a wave outside its string
  is an error. A junction's `at` must be a number with a unit, and a string has at most one
  junction on each side.
- **Views:** an engine-chosen display window is placed inside the wave's string, and any
  window is clipped to it.
- **Limit (v0):** only one reflection is modelled; derived waves are not reflected
  again. For the normal modes of a finite string, use a resonator.

## Sound media: gas, fluid (liquid), rod (solid)

```yaml
air:   {type: gas, v: 340 m/s, density: 1.29 kg/m^3}       # density: needed for pressure/intensity
air:   {type: gas, gamma: 7/5, pressure: 1e5 Pa, density: 1.29 kg/m^3}
air:   {type: gas, gamma: 7/5, temperature: 300 K, molar_mass: 29 g/mol}   # uses the exact gas constant R
air:   {type: gas, gamma: 7/5, pressure: 1e5 Pa, temperature: 300 K, molar_mass: 29 g/mol}  # density = P*M/(R*T)
water: {type: fluid, bulk_modulus: 2.2e9 Pa, density: 1000 kg/m^3}         # or v + density
sea:   {type: fluid, compressibility: 4.4e-10 1/Pa, density: 1025 kg/m^3}  # bulk modulus = 1/compressibility
water: {type: fluid, density: 1000 kg/m^3, bulk_modulus: "1e5[Pa] / (50[cm^3]/1[m^3])"}  # B = dP/(dV/V)
steel: {type: rod, Y: 2e11 Pa, density: 7800 kg/m^3}                       # longitudinal: v = sqrt(Y/density)
steel: {type: rod, Y: 2e11 Pa, mass: 0.1 kg, length: 1 m, area: 1e-6 m^2}  # density from mass/(length*area)
# a medium is a material: its length only fixes the density; resonators on it may have any length
```

- Every input must belong to a complete route; leftover inputs are an error.
- `density` is always allowed. It is needed for pressure amplitudes and intensities; it is
  never invented (missing gives "undetermined").
- A fluid works like a gas everywhere (pipes, sources, rays).
- **Sound waves:** a harmonic wave on a gas, fluid or rod states its amplitude as exactly
  one of `A` (displacement), `pressure_amplitude` or `intensity`. The engine links them:
  - p0 = density * v * omega * A;
  - I = p0^2 / (2 * density * v).

  For a rod, p0 is the stress amplitude.
- **Observables:** `pressure_amplitude(w)`, `displacement_amplitude(w)` and
  `intensity(w)`.
- **Sound level:** `sound_level(I)` = 10*log10(I/I0), and its inverse
  `intensity_of_level(L)`.
  - I0 = 1e-12 W/m^2 is the standard reference of the decibel scale, a definition.
  - A level fact may contain an unknown, e.g. `sound_level(intensity(r)) == 80` solves
    for a power.
- If the book uses a rounded gas constant, record it:
  `gas_constant: 8.3 J/(mol*K)`, tagged as a convention.

## Resonators (standing-wave modes)

```yaml
resonators:
  r: {type: string, on: wire, length: 1 m, ends: [fixed, fixed]}                      # fixed | free
  p: {type: pipe, on: air, length: L, ends: [closed, open], end_correction: 0.6 cm}    # closed | open
  b: {type: rod, on: steel, length: 1 m, ends: [clamped, free]}                        # clamped | free
```

- **Pipes must state `end_correction`** (`0 m` if the problem neglects it). It is added
  once per open end.
- **Allowed harmonics:**
  - equal ends: every harmonic n = 1, 2, 3, ...;
  - one closed (fixed) and one open (free) end: odd harmonics only. Asking for an even
    one is an error.
- **Unknown harmonic numbers:** `harmonic=n` with `n` a symbol of kind `integer` works.
  When n is solved, the mode rules (whole, >= 1, odd where required) are enforced; a
  solution breaking them is rejected. If n stays symbolic for a closed-open resonator,
  write it as `2*m - 1`.
- **Size:** length and effective length must be positive; `end_correction >= 0`. A pipe
  closed at both ends takes `end_correction: 0 m`.
- **Overtones:** `harmonic(r, overtone=k)` converts an overtone number to a harmonic
  number (the 1st overtone is the first mode above the fundamental).
- **Observables:**
  - `frequency(r, harmonic=n)`, `wavelength(r, harmonic=n)`,
    `node_spacing(r, harmonic=n)`;
  - `resonances(r, f=..., vary=L, lo=..., hi=...)` lists the values of a symbol in the
    scene (e.g. a length, a tension, a temperature, or the frequency itself) at which some
    allowed mode has frequency f. `count(...)` gives how many. The list cannot be used
    in arithmetic.
  - Other symbols involved must have values. Unknowns are fine once solved, so use
    `resonances()` in `observe`, not in `given`.
  - To count the modes below a limit (e.g. audible ones), vary the frequency:
    `count(resonances(p, f=fs, vary=fs, lo=20[Hz], hi=20000[Hz]))`, with `fs` a symbol.
  - `speed(r)` gives the wave speed in a resonator's medium.
- **Standing-wave patterns:**
  - Positions run from the first end in `ends` (x = 0) to the second (x = length).
  - `nodes(r, harmonic=n)` and `antinodes(r, harmonic=n)` give displacement nodes and
    antinodes on the resonator, ends included. For pipes, `pressure_nodes` and
    `pressure_antinodes` are also available.
    - With a non-zero end_correction, the displacement antinode at an open end lies
      beyond the pipe, so it is not listed. Counts are then one below the textbook count
      that places it at the mouth. Use `end_correction: 0 m` when the problem ignores
      it.
    - Solved unknowns (a length, a harmonic) may be used in `observe`.
    - An unknown point in `mode_shape` inside `given` is kept on the resonator
      (0 <= x <= length) automatically.
  - `mode_shape(r, harmonic=n, x=...)` is the displacement amplitude profile, with a
    maximum of 1.
    - Particles where it has the same sign move in phase; opposite signs move in
      antiphase.
    - A ratio of two values gives a ratio of amplitudes.
  - `harmonics(r, upto=N, node_at=x0)`: the allowed harmonics with a node at x0
    (touching a string there leaves these).
  - `harmonics(r, upto=N, no_node_at=x0)`: the harmonics that plucking or striking at x0
    can excite.
  - `harmonics(r, upto=N, antinode_at=x0)`: the harmonics with an antinode at x0.
  - Use `count(...)`, `min(...)` or `max(...)` on these lists.
- **Rods:** `type: rod` on a rod medium, ends `clamped` (displacement node) or `free` (antinode); same mode rules.
- **Not supported yet:** transverse (bending) modes of rods; resonators on non-uniform media.

## Point sources, reflectors and rays (sound interference by path)

```yaml
media:  {air: {type: gas, v: 340 m/s}}
sources:
  S1: {on: air, at: [0 m, 0 m], f: 170 Hz, A: 1, phase: 0, spreading: none}
  S2: {on: air, at: [3 m, 0 m], f: 170 Hz, A: 2, phase: pi/2, spreading: none}
  N:  {on: air, f: 170 Hz, A: 1, phase: random, spreading: none}     # incoherent
  D:  {on: air, at: [0 m, 0 m], power: 1e-3 W, phase: random, spreading: hemispherical}  # stated power
reflectors:
  wall: {point: [4 m, 0 m], normal: [-1, 0], boundary: rigid}         # or open
points:
  P: [0 m, 6 m]
rays:
  d1:   {from: S1, to: P}                    # straight path
  b1:   {from: S1, to: P, via: wall}         # one reflection (image source)
  tube: {from: S1, length: L1}               # a stated path length (tubes, interferometers)
```

- **What adds:** the engine adds rays as **pressure** waves,
  p = A sin(2*pi*f*t - k*s + phase + reflection phase), with s the path length.
  - Rays meeting from different directions add as a scalar, which pressure is and
    displacement (a vector) is not.
- **Reflection phase comes from the boundary.** A `rigid` wall gives pressure no phase
  change; an `open` (pressure-release) boundary gives pi.
  - Write `phase_change: pi` instead only when the problem itself states the phase
    change, and tag it as a convention.
  - Do not import the string rule ("a hard reflection adds lambda/2") into sound problems.
- **Spreading must be stated.**
  - `none` keeps A at every distance. `spherical` / `hemispherical` (A*A_at/s) and
    `cylindrical` need `A_at`, the distance where the amplitude is A. If a problem gives
    the amplitudes or intensities at the point, use `none` and say so in `assume`.
- **Power instead of an amplitude:** `power: 0.8 W` with `spreading: spherical`
  (I = P/(4 pi s^2)) or `hemispherical` (P/(2 pi s^2)).
  - Each ray then has a physical intensity, and with the medium's density a pressure and
    displacement amplitude.
  - `f` is optional when nothing needs a phase (e.g. incoherent sources and levels).
  - For such sources, `amplitude(ray)` is refused: ask for `pressure_amplitude` or
    `displacement_amplitude`.
  - A stated-length ray (a tube) from a powered source is refused, because spreading
    along a tube is not modelled.
- **Physical intensity of rays:** `intensity(r1, r2, ...)` in W/m^2, for sources with
  `power` or with A in Pa. Coherent rays of one frequency add as phasors; anything else
  adds as intensities. Also `pressure_amplitude(r1, r2, ...)`, the resultant for coherent
  rays, and `displacement_amplitude(ray)`.
- **`emitters` are older and need no change**; new scenes should use `sources`.
- **Coherence:** sources not marked `phase: random` are treated as coherent with each
  other.
  - Mark independent sources (two loudspeakers on separate amplifiers, two people)
    `phase: random`. A random source is incoherent with every other source, so their
    intensities add.
  - Rays of different frequencies also add as intensities (time average).
- **Units of A:** use one unit for every amplitude (e.g. all in Pa), or plain numbers
  throughout. Mixing is an error.
- **Positions:** 2 or 3 lengths. Never name a point `x`, `t` or `pi`.
- **Reflectors:** an infinite plane. A reflector acts only on rays that name it in
  `via`; a direct ray is not checked for crossing it. v0 allows one reflection per ray.
- **Positive inputs:** frequencies and stated lengths must be positive.
- **Observables:**
  - `length(ray)`, `distance(P, S)`, `path_difference(r1, r2)`,
    `phase_difference(r1, r2)` (phase of r1 minus phase of r2; use `wrap(...)` to reduce
    it);
  - `amplitude(ray)`, `phase(ray, t=...)`, and `frequency`, `wavelength`, `k`, `period`
    of a ray or a source;
  - `resultant_amplitude(r1, r2, ...)` for coherent rays of one frequency;
  - `relative_intensity(r1, r2, ...)`: time-averaged intensity in units of amplitude^2.
    Coherent rays of one frequency add as phasors; anything else adds as intensities.
    - It is proportional to intensity only for pressure amplitudes in one medium.
    - Use ratios, e.g. `60[W/m^2]*relative_intensity(r1, r2)/relative_intensity(r1)`.
    - Each ray may be listed once.
  - `maxima(r1, r2, vary=s, lo=..., hi=...)` and `minima(...)` list the values of a symbol
    (a wavelength, a frequency, a length) at which the two rays are in phase or opposite.
    - They test exactly two rays, by phase. With spreading and a varied position, or with
      a third ray, the true intensity extrema can lie elsewhere; check with
      `relative_intensity`.
    - [lo, hi] is closed; give units.
    - Values at which a ray would have a length of 0 or less are dropped.
    Use `max(...)`, `min(...)` or `count(...)` on the list. "Adjacent maxima" are
    neighbours in this list.

## Moving sources, listeners and walls (Doppler); wind

Sources and points can move, a plane wall can move along its normal, and the air can move
(wind).

```yaml
media: {air: {type: gas, v: 340 m/s, wind: [10 m/s, 0 m/s]}}     # wind: optional; fluids use flow:
sources:
  car:  {on: air, at: [-100 m, 0 m], velocity: [20 m/s, 0 m/s], f: 500 Hz, A: 1, phase: 0, spreading: none}
  horn: {on: air, at: [0 m, 0 m], velocity: [10 m/s, 0 m/s], starts: 5 s, emits_from: 0 s, ...}
  toy:  {on: air, at: [2 m, 0 m], circle: {center: [0 m, 0 m], speed: 5 m/s, sense: ccw}, ...}
points:
  O: [50 m, 0 m]                                         # a still listener
  bike: {at: [80 m, 0 m], velocity: [-15 m/s, 0 m/s]}    # a moving listener
reflectors:
  wall: {point: [200 m, 0 m], normal: [-1, 0], boundary: rigid, velocity: [-5 m/s, 0 m/s]}
rays:
  heard: {from: car, to: bike}
  echo:  {from: horn, to: O, via: wall}
```

- **Motion.**
  - `at` is the position at t = 0.
  - With `starts`, the object rests at `at` until that time, then moves with `velocity`.
  - `circle`: uniform circular motion in the plane. `at` is the position at t = 0, on the
    circle.
  - `emits_from`: the source is silent before this time.
- **How the engine hears** (first principles, not the textbook formula):
  - The sound heard at time t left the source at the emission time te, where
    |R(t) − E(te) − wind·(t − te)| = v (t − te).
  - The heard frequency is f · dte/dt: exact when te is (a line, a still side), and a
    30-digit decimal when an unknown time sits on a circle. Such a decimal is accepted only
    if it satisfies the propagation equation above; otherwise the time is refused as not
    established.
  - Wind at an angle is treated exactly, not by its component along the line, so the
    result can differ slightly from the book's formula; choose the nearest option.
- **Observables:**
  - `frequency(ray, t=...)`: heard at reception time t.
  - `frequency(ray, emitted=...)`: the sound emitted at that time ("when the source is at
    A").
  - `emitted_at(ray, t=...)`, `arrives_at(ray, emitted=...)`.
  - `wavelength(ray, t= or emitted=)`: in the air at the listener.
  - `beat_frequency(ray1, ray2, t=...)`: two rays heard at the same instant.
  - `distance(p, q, t=...)`.
  - Times in expressions need brackets: `t=2[s]`.
- **A time is required** when something on the ray moves, because the heard frequency
  can change with time. `frequency(ray)` alone is refused.
  - For "while approaching": place the source at a distance and use `emitted=0[s]`.
  - For "after they cross": use a time after the crossing.
  - Put unstated distances in `arbitrary:`: the answer must not depend on them.
- **Speeds and arbitrary values:** keep arbitrary speeds well below the speed of sound.
  The arbitrary check scales them up to x89, and every scaling must stay subsonic.
- **Light, radar, radio:** use `media: {space: {type: em}}`. The speed is c (exact SI);
  give `v` or a refractive index `n` for a material.
  - When the problem says to take c = 3e8 m/s, write `c: 3e8 m/s`. It is used everywhere,
    for travel and for time dilation; `v` may not exceed it.
  - `speed(space)` gives the medium's light speed.
  - A gas or fluid with v of 1e5 m/s or more is refused: it is not sound.
  - The Doppler effect for `em` is exact special relativity:
    f = f0 · (γ_receiver/γ_source) · dte/dt, in the frame where light has speed c.
    Echoes from moving reflectors work as for sound.
  - Book answers use 2u/c approximations; they agree to the digits shown. Pick the option
    with `nearest(...)`.
  - **Radar beats** (echo mixed with the transmitted signal):
    `beat_frequency(frequency(echo, t=100[us]), frequency(gun))`, with `echo` a ray from
    the gun to the gun's receiver via the moving car (a reflector).
  - In a material (`n` or `v`), light travels at c/n in the medium's frame (the scene
    frame), while time dilation uses the vacuum c.
  - `wavelength(ray, ...)` for `em` is the wavelength in the medium's frame:
    (c/n) / (the frequency an observer at rest there would measure).
  - There is no wind for `em`. Sound quantities (intensity, pressure, displacement, sound
    level) are refused.
  - Speeds solved from facts are checked: light faster than c, or a "sound" speed of
    1e5 m/s or more, is refused.
- **`wave_speed_seen(ray, t= | emitted=)`:** the speed of the arriving wave relative to
  the listener, along its direction of travel: v + (wind − listener velocity) · k̂ for
  sound. For light it is relativistic velocity addition, which gives exactly c in
  vacuum.
- **A listener carrying its own source** (same motion, same place) hears the source's own
  frequency.
- **Reflections:**
  - A moving wall must move along its normal. Source, listener, their velocities and the
    wind must lie on the normal line (v0).
  - A still wall works off the line too (image source), but not with wind.
- **Plotting** the heard frequency against time: `view: [{plot: "frequency(r, t=t)", vs: t,
  range: [0 s, 20 s]}]`. Each instant is solved on its own. In `observe`, a time is
  required.
- **On a moving ray** (anything moves, or wind), path lengths, phases, intensities, and
  `period`, `omega` and `k` are refused in v0.
- **Unknown speeds** (of a source, listener, wall or sound) can be solved from `given`
  facts. Ask with `emitted=` at a time whose positions are known (e.g. `emitted=0[s]`).
  If the solved speed is at or above the speed of sound, the scene is inconsistent.
- **No echo:** an echo exists only while the source (when it emits) and the listener
  (when it hears) are in front of the wall. Otherwise it is refused.
- **Refused:**
  - motion at or above the speed of sound (relative to the air);
  - an instant exactly when a motion starts, where the frequency jumps;
  - sound asked for before it was emitted ("no sound yet"). For a source with `emits_from`,
    this covers `phase(ray, t=...)` too (on a stated-length path the delay is length/v), and a
    phase at a symbolic time is then refused, because whether the sound exists cannot be
    decided. A ray in moving air (`wind`), whether geometric or of stated length, has no phase
    at all in v0.

## Energy on strings

For any wave on a string (harmonic, given with `on:`, sum, shaped pulse and its reflected
or transmitted parts):

- **Per unit length at (x, t):**
  - `kinetic_density(w, x=, t=)` = (1/2) mu (dy/dt)^2;
  - `potential_density(w, x=, t=)` = (1/2) T (dy/dx)^2;
  - `energy_density(w, x=, t=)` = their sum.

  For energy per unit volume, divide by the cross-section.
- **In a stretch at an instant:** `kinetic_energy(w, start=, end=, t=)`,
  `potential_energy(...)` and `energy(...)`.
  - Without `start`/`end`, the whole string is used.
  - For a shaped pulse, `t` may be omitted. Then the integral covers the whole pulse, and
    for a reflected or transmitted pulse that is the energy it carries.
- **Largest or smallest value over a range:** `max_in(var, expr, lo, hi)` and
  `min_in(...)`, e.g. `max_in(x, kinetic_density(p, x=x, t=0.05[s]), 1[m], 2[m])`. They work
  for any expression in one variable, including piecewise ones. Other symbols must have
  values before the search, so put `at(...)` inside: `max_in(x, at(expr, A=1[m]), lo, hi)`.
- **Averages over a period:** `mean_over(t, kinetic_energy(w, start=0[m], end=wavelength(w)/2, t=t), 0[s], period(w))`.
- **Pulse width:** `width(p)` is the length over which a shaped pulse is non-zero; for a
  transmitted pulse it is v2/v1 times the incident width. A shape that never reaches zero
  (e.g. a Gaussian) has no width. A shape written with an unspecified function
  (`functions: [F]`) has no determined width either, and `width()` is refused for it.
- **Refusals:**
  - A shape with a jump (e.g. a rectangle) is refused: it has infinite stretching energy.
    Continuity can only be checked where corners and edges are at numeric positions, so
    give numbers, including the instant.
  - A density exactly at a corner is refused (the slope is undefined there); ask just
    beside it.
  - A stretch (`start`/`end`) of a pulse needs `t`. Without `t`, the whole pulse is meant.
  - A wave with no string has no mu or T: undetermined.
- **Exact or decimal:** integrals are exact where possible. Otherwise a numerical value
  is computed piece by piece and shown as a decimal.
- `width` of a pulse with several separate non-zero parts is ambiguous, and is refused.
- A standing wave may be given directly (`given:` with `on:`); it has no single speed, so
  its speed is not compared with the string's.

## Emitters (open3d)

```yaml
pt:   {on: air, geometry: point, power: P}
line: {on: air, geometry: line,  power_per_length: P}
pl:   {on: air, geometry: plane, intensity: I}
```

## Ratio and comparison questions (values the problem does not give)

- **Arbitrary values:** if the answer cannot depend on a value the problem never states
  (the wire's mass per length in "the tension is doubled", a pipe's length in "how does the
  frequency change"), do not invent it as a fact. Declare it arbitrary:

  ```yaml
  arbitrary: {mu: 10 g/m, L: 1 m}      # any convenient positive values, with units
  media: {w1: {type: string, mu: mu, tension: 50 N}, w2: {type: string, mu: mu, tension: 200 N}}
  ```

  - The engine runs the scene at these values and at four other scalings (two near them,
    and x1/97 and x89). An observable is reported only if all five runs agree; its basis
    then says "same at 5 scalings ... (sampled)".
  - This is a sampled check, not a proof: a threshold far outside x0.01 to x89 would go
    unseen. Pick arbitrary values of a sensible size for the problem.
  - If an observable does depend on them, it is NOT AVAILABLE ("depends on the arbitrary
    values"): the problem really does not fix it.
  - **A ranged arbitrary value** has a physical ceiling or floor:
    `u: {value: 20 m/s, below: 340 m/s}` (an unstated speed, below the speed of sound),
    or `L: {value: 2 m, above: 1 m}`, or both: `L: {value: 20 cm, above: 15 cm, below: 30 cm}`.
    - Its other runs use values across the open range (3%, 37%, 61% and 97% of the way),
      not the x0.01–x89 scalings.
    - With `above` only, the distance above the bound is scaled.
    - Use a range whenever the scalings would leave the physically allowed values.
  - A name under `arbitrary` is not also declared in `symbols`. Any field may use it
    (lengths, Y, density, tension, power).
  - Use arbitrary values wherever a number is needed only to run the scene (resonance
    lists, `max_in`, sources). Never tag them as stated facts.
  - If the scene fails at another scaling, every observable is NOT AVAILABLE.
  - In the export:
    - unknowns solved from arbitrary values are marked "for drawing only";
    - panels carry a note that only scale-free features mean anything;
    - `explore: {vary: {arbitrary.L: [...]}}` is labelled an arbitrary value, never a
      physical input.
- **Comparisons in `observe`:** `a > b`, `a <= b`, chains such as `a > b > c`, and
  `a == b`.
  - The result is True or False, decided for all symbol values (with the stated bounds).
  - With arbitrary values:
    - The engine first tries a proof over every allowed value (basis "proved for every
      allowed arbitrary value").
    - Otherwise it checks 14 values, including values near both ends of every range
      (basis "sampled, not proved"). An unranged arbitrary value is scaled from x0.001 to
      x1000 here. A scaling that leaves the physics (a sound speed of 340000 m/s is not
      sound) is skipped, and the basis names it; with fewer than 5 extra values left, the
      comparison is refused. Give a range (below:/above:) to avoid that.
    - If the truth changes, the comparison is NOT AVAILABLE ("true for some allowed
      values and false for others"): the option is not necessarily true.
  - `==` between exact numbers needs exact equality; engine decimals use a relative
    tolerance.
  - An undecidable comparison is refused. Both sides need the same dimension.
- **Comparisons through `abs`, `max` and `min`** (e.g. a beat frequency) are split into
  sign cases. They are decided when every possible case agrees. A case with one symbol is
  checked on its own range. Cases with several symbols, or compound conditions, may be
  refused ("cannot decide"); they are never guessed.
- **Options given as rounded numbers:** `nearest(x, a, b, c, d)` gives the position (1 for
  a) of the option nearest to x by relative distance. It is refused when the two nearest
  options are about equally close.
  - x (or an option) may depend on solved unknowns; the option is picked after the solve.
    If it still depends on something unfixed, it is refused. With arbitrary values, the
    value and options it compares must be **proved** free of them (the engine reruns the
    scene with them as symbols); sampled agreement is not enough for a choice of option,
    so a value that cannot be proved independent is refused. An expression around a
    `nearest()` (e.g. `L*nearest(...)`) is still checked as a whole, like any value.
  - A `nearest()` inside another is picked first.
  - **Options printed in a unit:** `nearest(x in km/h, 36, 54, 72)` converts x to that
    unit (its dimension is checked, as for `in` in `observe`). A printed number is read
    in that unit; an option with a unit (`15[m/s]`) or an unknown is converted to it by
    its own dimension, and refused if that cannot be checked.
  - `nearest()` is for `observe` only, on its own: not in `given`, not inside a
    comparison, and not plotted.
- **Lists:** `item(list, n)` (1 for the first), `spacing(list)` (the common difference of
  an equally spaced list; otherwise refused), and `count(list)`.
- **A band of frequencies** (a source of variable frequency):
  `frequencies_in(resonator, lo=400[Hz], hi=1000[Hz])` lists the allowed mode frequencies
  in the band. Use it with `count`, `item` and `spacing`.
- **Units of a result:** `"expr in cm"` (or kHz, ms, degC, ...) reports the value in
  that unit. Without `in`, results are SI.
  - The dimension is checked. Lists and solved unknowns convert entry by entry. An
    unknown that no field fixes takes its dimension from the facts that use it.
  - `period(resonator, harmonic=n)` gives the period of a mode.
  - Angle units (rad, deg, rad/s) are refused: radians have no dimension, so a frequency
    could not be told from an angular frequency. `omega(...) in Hz` is refused too.
  - In an `expect` block, a value written with a unit is converted to the observable's
    unit; a bare number is read in that unit.
- **Bounds on a symbol:** a `given` fact comparing one symbol with a constant, e.g.
  `{fact: "n > 1", source: stated}`, `L >= 2[m]` or `2 < m`, is a stated bound.
  - It works for positive, real and integer symbols.
  - The engine uses it in every sign decision (e.g. n - 1 > 0).
  - Results are shown in the original symbol.
  - The symbol takes the bound's dimension: write the unit on the bound.
  - An `illustrate` value must satisfy the bound.
  - `at(..., n=value)`, `diff(..., n)` and `resonances(..., vary=n)` work on a bounded
    symbol: values outside the bound are refused or skipped.
  - Messages may show Δ(n), the distance of n from its bound.
  - One bound per symbol in v0. A bound on an unknown is an ordinary fact.
- **Several unknowns tied through sound levels** (two dB readings, two unknown powers or
  distances) are solved together. Every root is re-checked against the facts, and a root
  where a log's argument is not positive is dropped.
  - Declare such unknowns `positive` (distances, powers).
  - A real unknown inside a log of a product or power (log(d^2), log(a*b)) is refused, so
    that no sign case is lost.
  - Facts that fix only a combination of the unknowns are reported as undetermined.

## given: how facts are solved

- **Exactly one situation, or an error:**
  - **inconsistent:** names the first contradicting fact and, where possible, the range
    its left side can actually reach;
  - **ambiguous:** lists the fitting situations, including infinite periodic families;
  - **undetermined:** something is never fixed.
- **Fix an ambiguity explicitly:** add a constraint to `given` and record the reason in
  `assume`.
- **Free `t`:** an equation with a free `t` must hold for all t. Unknown frequencies
  inside such an identity are refused.
- **Unknowns inside sines/cosines:** these must have numeric coefficients. They are
  solved on the unit circle and every branch is enumerated:
  - phases mod 2*pi;
  - other unknowns over the range allowed by their sign and by the inequalities.
  - **Two points off the origin** (an unknown k, or omega, and an unknown phase, from two
    displacements): each fact fixes its angle up to two inverse-sine branches and 2*pi*n,
    so k = k0 + n*2*pi/(x2 - x1). A stated bound (e.g. "less than half a wavelength
    apart": `kk*15[cm] < pi`) picks the branches; one left is the answer, two or more
    (or no bound: infinitely many) are reported as ambiguous.
- **Refused trig cases:** any other unknown inside a trig function is refused rather than
  risk a lost root.
- **Unknowns inside log, exp, inverse trig or an exponent** (e.g. a power from a level):
  - Solved for one unknown at a time, with the full real root set; every root is
    re-checked.
  - Several such unknowns are solved together when each fact is linear in logs (e.g. sound
    levels); other forms are refused.
- **Absolute values** (`abs(...)`, and `beat_frequency`, which is |f1 - f2|) around
  unknowns are solved by sign cases. Each case is checked, so a beat with two possible
  sides gives one answer or an "ambiguous" error, never a guess.

## Observables (engine physics)

| Group | Functions |
|---|---|
| Wave | velocity (signed), speed, amplitude, offset, frequency, omega, period, wavelength, k, field |
| Point (`x=`, `t=` required) | y, vy, ay, slope, phase |
| Energy | power (string), intensity(emitter, r=), flux(point_emitter, sphere(r)) |
| Medium | speed(m, at=), tension(m, at=), mu(m), impedance(m) |
| Non-uniform string | speed(m, at=s), wavelength(w, at=s), frequency(w), front(pulse, t=) |

On a `given:` wave, wave-level observables are found by analysis:
- the travelling form, via `y_t + c*y_x = 0`;
- offset + one sinusoid, after product-to-sum reduction.

If the analysis fails, the scene is rejected.

Two more checks:
- `is_travelling(w)` returns true or false and never aborts the scene.
- `wrap(angle)` reduces an angle to (-pi, pi], e.g. a phase difference.

For "are two points in the same phase?", use
`equivalent(y(w, x=x1, t=t), y(w, x=x2, t=t))` (see example 18).

Beats: `beat_frequency(a, b)` takes two waves or two frequencies in Hz. Pass `frequency(w)`,
never `omega(w)`: both are 1/s, so the dimension check cannot catch it.

## Maths services

- `frequency_of(var, expr)` gives the oscillation frequency of a sinusoidal expression
  in var.
- **Pulse tools:**
  - `peak(w, t=...)` is the largest |y| over x at an instant, for any wave with a field.
    For a shaped pulse alone, `amplitude(p)` and `peak(p)` give its height.
    `peak_position(w, t=...)` is where it occurs; a tie is reported as ambiguous.
  - These look only where the written profile is defined at that instant, and only at a
    largest |y| that is reached: one only approached (beside a jump, toward where the profile
    stops being defined, or at infinity) is refused. Values are compared exactly, not to a
    tolerance. A constant field's peak is its value; its `peak_position` is ambiguous.
    `max_in` and `min_in` likewise need their extreme value taken somewhere. A shape with
    infinitely many breakpoints (`step(sin(x))`) is handled only over a finite range. An energy needs the profile defined over the whole
    stretch, and `width` needs the shape defined everywhere.
  - At a corner of a shape, `vy` and `slope` are undefined and refused; ask just beside it.
    (Known gaps at corners, jumps and branch points, for example `ay` at a corner or a derivative
    placed on a corner with `at(...)`, are open defect D3-1, to be fenced in milestone M4.)
  - Observables can be nested, e.g.
    `front(p, t=travel_time(rope, start=0[m], end=3[m])/2)`.
  - `step(u)` is 1 for u >= 0, else 0. Shapes can be built from `max`, `abs` and `step`.
    - Write a window from a to b as `(step(x - a) - step(x - b))`. It is half-open, so
      adjacent windows do not double up at the joint. Example, a half-sine:
      `0.02*sin(pi*(x - 1)/0.4)*(step(x - 1) - step(x - 1.4))`.
    - `peak` is exact where it can be. For shapes whose extremes have no closed form (e.g.
      overlapping Gaussians) it is a numerical value, shown as a decimal.
    - Positions and instants must be numbers. A symbolic peak position is an error,
      except that a lone pulse has the same height at every instant.
- `travel_time(m, start=..., end=...)` is the time to run along a string (or a sound medium)
  from start to end: the integral of ds/v, which also works with a coordinate variable.
  - It is never negative.
  - Both ends must lie on that string. Across a junction, add the times on each string.
  - It is for a still medium. In moving air (`wind`) or a moving fluid (`flow`) it is refused,
    since the time then depends on the direction; use a ray and `arrives_at(ray, emitted=...)`.
- `envelope(var, expr)` gives the beat envelope of a sum of two sinusoids with different
  frequencies: sqrt(A1^2 + A2^2 + 2*A1*A2*cos(dw*var + dc)).
  - Its maximum and minimum are `max_over(t, envelope(t, ...))` (A1 + A2) and
    `min_over(t, envelope(t, ...))` (|A1 - A2|).
    - The signal only reaches these values when the two frequencies are close (beats).
      For far-apart frequencies the envelope is not the signal's maximum.
  - Use `beat_frequency(...)` for the rate of the loudness maxima. The envelope's own
    oscillation is at the difference frequency.
- `limit(expr, var, value)` is for approximations; e.g. a small `dl` gives
  `limit(f/dl, dl, 0)` (see `examples/23_05_asc_004.yaml`).
  - Write it as `limit(expr, var, value)`: three arguments in that order, no keywords.
  - **Everything other than the variable must be a number:** no other symbol or unknown,
    and no arbitrary function (`functions:`), in the expression, the point, or anything
    written in them. Use numbers or `arbitrary:` values (numbers when the engine
    evaluates). Units in brackets are units (`q/2[m]` is fine). A wave whose profile is
    an arbitrary function cannot be used inside a limit.
  - **Every part as written must be defined near the point**, even one that cancels, and
    including what a call returns (a wave given as `sqrt(x - t)`): a log needs a positive
    argument there, a root a nonnegative one (`sqrt(0)` is fine), asin/acos an argument in
    [−1, 1] (it may tend to ±1 from inside: asin(1 - q²) → π/2; asin(1) is fine), and a
    division a denominator that is nonzero near the
    point (it may be 0 at the point itself, as in sin(q)/q). So
    `limit(log(q) - log(q), q, 0)` with q real is refused (no log below 0), while with q
    positive it is approached from above. A symbolic limit is refused:
    it is only generic, and can be wrong at some value of the other symbols (|q|/q at
    q → c has no limit at c = 0). So a formula such as v/(2l²) cannot be read off a limit;
    check it with numbers.
  - At an interior point both one-sided limits are taken and must agree; otherwise it is
    refused ("from above ..., from below ..."). At the edge of the variable's domain (0
    for a positive symbol, or a stated bound) it is approached from inside only.
  - The point must be one the variable can approach: within the values it can take, i.e.
    its kind (0 or more for a positive symbol) together with any stated bound (`q < 1`
    with q positive allows (0, 1)), or on an edge. Outside, it is refused. A whole-number
    variable is refused.
- Lists cannot be indexed (`[1]` is read as a unit and refused); use `min`, `max` or
  `count`.
- `min(a, b)` and `max(a, b)` take two values of the same dimension, or one list
  (e.g. `max(maxima(...))`).
- A limit that does not exist (oscillates or diverges) is an error.
- **Unit brackets bind tighter than `/`:** `3/2[m]` means 3/(2 m), so write `(3/2)[m]`.
- **Also available:** `diff(e, var, n<=10)`, `max_over(var, expr)` and `min_over(var, expr)` (combine sinusoids
  of one frequency), `equivalent(a, b)` (evaluated after
solving; relative tolerance), `abs`, `sqrt`, `sin`, `cos`, `tan`, `exp`, `log`, `atan`,
`asin`, `acos`, `simplify`.

## How results are reported

- **Each observable stands on its own.**
  - If one cannot be computed (an even harmonic in a closed pipe, a limit that does not
    exist, an empty list given to `max`), it is reported as NOT AVAILABLE with the
    reason. The other observables are still computed and shown, and the run exits with a
    non-zero status.
  - Errors in the facts (inconsistent, ambiguous, undetermined) stop the whole run, because
    no result would then be meaningful.
- **Value at a point:** `at(expr, d=120[m])` evaluates an observable with chosen values for
  scene symbols, or for `x` and `t`, e.g. `at(relative_intensity(up, direct), d=120[m])`.
  Unknowns cannot be set this way; their values come from the facts.
- **Every result has a basis:**
  - `exact` (symbolic engine result);
  - `proved` (an `equivalent()` that holds symbolically);
  - `sampled` (agreement at random points only; NOT a proof);
  - `counterexample` (shown to differ at a point).
- **Every solution is re-checked.** After solving, each original fact (and each implicit
  cross-check) is substituted back by a separate code path. The declared kind of every
  solved unknown is checked as well. Each fact is reported as `proved`, `sampled` or
  `undecided` (an inequality whose sign depends on free symbols). A failure here is an
  engine bug and stops the run.
- **What the re-check does not cover:** it confirms the facts hold. It does not re-prove
  uniqueness, which comes from the solver's branch enumeration. It also shares the
  expression parser with the solver.
- **Redundant facts:** a fact that contains no unknowns and is identically true (e.g.
  `sin(a)**2 + cos(a)**2 == 1`) is accepted. If it is false, the scene is inconsistent.
  If it can't be decided for all symbol values, the scene is over-specified.
- **Time and memory limits:** every request runs in its own fresh process: one `run`, each
  scene of a `test` run, each scene of a `view`.
  - The default limits are **120 s and 2048 MB per request**; change them with `--time S`
    and `--memory MB`. The time counts from the moment the request is accepted, so the
    process's start-up (about a second) is included. A time limit is a finite positive
    number of seconds, at most 1,000,000 (about 11.6 days), and a memory limit a whole number of
    MB from 256 to 1,048,576 (1 TB); anything else is refused with a clear error before
    anything runs.
  - `view` writes its page only if every scene finished within the limits.
  - What the limits guard against is the engine's own runaway computation. A request's
    processes are cleaned up with it (its process group on Linux, its Job on Windows); a
    process deliberately detached into a new session is outside that guarantee. A request
    carries plain data only (the built-in dicts, lists, strings and numbers, no subclasses),
    at most 16 MB of it as sent.
  - A request that passes a limit is stopped and reported as
    `RESOURCE LIMIT (time 120 s)` or `RESOURCE LIMIT (memory 2048 MB)` (exit status 3).
    This says nothing about the physics: it is not an inconsistency, a refusal or an
    unsupported feature. Simplify the scene or raise the limit.
  - The limits apply to the whole run. A scene cannot set its own (an `expect.limits` block
    is refused). In a test, `error: limit` expects the scene to be stopped.
  - A scene file larger than 64 KB is refused before it is read.
  - Some slow symbolic steps have their own shorter budgets and then switch to a stated
    numerical method or a specific refusal. These work the same on every platform.

## Views (`python -m simwaves view out.html scene.yaml ...`)

The viewer only draws arrays sampled by the engine; it does no physics.

```yaml
view:
  - {snapshot: w1, t: 0 s}                          # a wave at one instant
  - {animate: w}                                    # a wave over time
  - {plot: "speed(rope, at=s)", vs: s, range: [0 m, L]}   # any observable vs x, t or a symbol
illustrate: {M: 1 kg, g: 9.8 m/s^2}                 # numbers for symbols the source leaves open
explore:
  vary: {media.rope.tension: [30 N, 60 N, 120 N]}   # a symbol or a scene path; one entry
```

- **Choose the smallest panel the source supports.** If a figure only shows the shape at
  one instant, use `snapshot`. `animate` needs a time scale (speed, frequency), which
  the source must actually provide.
- **`illustrate`:**
  - Every value needs a unit (`1 cm`; use `1 rad` for a dimensionless one).
  - Each value is checked against the dimension the symbol takes in the scene and
    against its declared kind, so a negative value for a `positive` symbol is rejected.
  - Illustrative values are labelled in three places: the banner, each panel drawn with
    them, and each result computed with them.
  - Exact symbolic results stay symbolic; illustrative values only add a numeric reading
    beside them.
- **Display windows:**
  - Without `x:`/`t:` in a panel, the engine shows 2 wavelengths or periods of the
    longest wave in the scene. This is labelled as a display choice, not source geometry.
  - A pulse alone has no natural scale and needs `x:`/`t:`. If other waves set the
    default window, check that it fits the pulse.
  - Each panel's window, plot range and y-range stay fixed across all varied values, so
    a varied value cannot hide its effect by rescaling.
- **`explore`:**
  - Each value re-solves the whole scene.
  - The source's own value is marked.
  - Each value carries its own results, solved unknowns, facts, re-checks and
    illustrative values.
  - A value the engine rejects shows only the rejection, never another value's results.

## Writing scenes from statements and figures

- **Tag every fact:**
  - `stated`: in the problem text;
  - `figure`: read off the figure;
  - `convention`: e.g. the JEE value tan 53 deg = 4/3;
  - `assumption`: your own choice.

  Put the reason for every assumption in `assume` or in the fact's `note`.
- **Write what a figure shows as facts, not as parameters.** For example, write
  `y(w, x=0, t=0) == 0` and `slope(w, x=0, t=0) > 0` with `phase` as an unknown,
  instead of guessing `phase: 0`. The engine then works out the phase and can catch a
  misreading; a parameter you type in is never checked.
- **Symbols cannot carry a range yet** (e.g. 0 < phi < pi/2). If a range matters,
  make the quantity an unknown and state the range as inequalities in `given`.
- **Never turn a missing value into a stated one.** If the figure has no scale and the
  question does not depend on scale (e.g. "which points are in the same phase"), you may
  fix a convenient scale. Tag it `assumption` and say why it cannot change the answer.
  If the answer does depend on the missing value, keep it as a symbol.
- **If the engine reports `ambiguous`,** the facts allow several situations. Add the
  constraint the problem implies, tagged `assumption`; don't pick one of the listed
  values yourself.
- **If the engine reports `inconsistent`,** re-read the source before changing
  anything. A real contradiction in the source is a valid result: report it, don't
  hide it.

## Not in the format (LLM side)

Options, matrix codes, "which can be", comparisons between cases, explanations.
For a comparison, put both setups in one scene (e.g. `s1`, `s2`) and take ratios in
`observe`.

## Limits (v0)

- Expressions are capped at 2000 characters and exponents at 100.
- Every request has a time and a memory limit, 120 s and 2048 MB by default, on every
  platform (see "How results are reported").
- `x=`, `at=` positions that are numbers are checked against the string's extent
  (set by junctions). A symbolic `x` (e.g. `y(w, x=x, t=0)`) is not checked: keep it
  inside the string yourself.
