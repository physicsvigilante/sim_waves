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
- **Units:** m, cm, mm, km, s, ms, kg, g, N, Pa, kPa, J, mJ, W, mW, kW, Hz, kHz, rad, deg, K, degC.
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
tension: free                       # the wave's speed fixes it
ends: {left: driven, right: absorbing}   # for fixed/free ends and joins, use `junctions`
```

## Waves

```yaml
# 1. harmonic: give any consistent subset; the engine completes it and cross-checks the rest
w: {harmonic: {on: rope, A: 1 cm, f | omega | period, lambda | k, v,
               dir: +x | -x | <direction unknown>   (or  from: left | right | <origin>),
               phase: 0}}
# 2. given: an explicit y(x,t); units for x, t AND y are required
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
    antinodes inside the resonator. For pipes, `pressure_nodes` and
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

## Emitters (open3d)

```yaml
pt:   {on: air, geometry: point, power: P}
line: {on: air, geometry: line,  power_per_length: P}
pl:   {on: air, geometry: plane, intensity: I}
```

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
- **Refused trig cases:** any other unknown inside a trig function is refused rather than
  risk a lost root.
- **Unknowns inside log, exp, inverse trig or an exponent** (e.g. a power from a level):
  - Solved for one unknown at a time, with the full real root set; every root is
    re-checked.
  - Several such unknowns together are refused: fix the others first.
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
- `envelope(var, expr)` gives the beat envelope of a sum of two sinusoids with different
  frequencies: sqrt(A1^2 + A2^2 + 2*A1*A2*cos(dw*var + dc)).
  - Its maximum and minimum are `max_over(t, envelope(t, ...))` (A1 + A2) and
    `min_over(t, envelope(t, ...))` (|A1 - A2|).
    - The signal only reaches these values when the two frequencies are close (beats).
      For far-apart frequencies the envelope is not the signal's maximum.
  - Use `beat_frequency(...)` for the rate of the loudness maxima. The envelope's own
    oscillation is at the difference frequency.
- `limit(expr, var, value)` is for approximations; e.g. a small `dl` gives
  `limit(f/dl, dl, 0)`.
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
- Evaluation has a 120 s time limit on Linux/macOS. Windows has no such limit yet.
- `x=`, `at=` positions that are numbers are checked against the string's extent
  (set by junctions). A symbolic `x` (e.g. `y(w, x=x, t=0)`) is not checked: keep it
  inside the string yourself.
