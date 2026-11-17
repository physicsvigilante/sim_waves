# Review of m13 (tension from mechanics, frequency bands, output units)

Reviewer: Opus, standing in for Fable 5.2, which needed usage credits.
Scenes are in eval/review13/ (a*, b*, c*, d*, e*, h/). r162 to r167 pass (copied to rt/).

## Findings, most severe first

1. **CONFIRMED, high: `in degC` reports kelvin labelled as degC.** `"300[K] in degC"` gives `300 degC`.
   It should give 26.85 degC, or be refused. The cause: `degC: (1, TEMP)`; the offset is ignored (b1).
2. **CONFIRMED, high: frequency and angular frequency are mixed up silently.** rad has no
   dimension, so `frequency(w) in rad/s` gives `10 rad/s` (it should be 20*pi). `omega(w) in Hz`
   gives `62.83 Hz` (it should be 10). See d1. The same dimensionless gap lets
   `count(...) in deg` give 171.9 deg (b2.g).
3. **CONFIRMED, high: negative k or Y gives a negative tension and an imaginary speed.**
   `stretch: {k: -400 N/m, ...}` gives T = -40 and v = 63.2*I. `Y: -2e11 Pa` gives T = -100 and
   v = 100*I. Neither is refused (a2, a3). Only the extension's sign is checked.
4. **CONFIRMED, medium-high: a solved immersed fraction above 1 is accepted.** With
   `fraction: xf` (unknown) and the fact tension == 10 N, the result is `xf = 3/2` (c5). The
   0 < x <= 1 check runs only at load time.
5. **CONFIRMED, medium (harness): the unit in `expect` is not compared with the unit in
   `observe`.** With `"wavelength(...) in cm"` (the value is 200 cm), `expect: "200 m"` PASSES and
   `expect: "200 cm"` FAILS (h/). The harness converts the expected value to SI but compares it
   with the converted result, so a book answer 100x off can pass.
6. **CONFIRMED, low: a negative mass is reported as "the load floats"** (a4). (refused; wrong reason)
7. **CONFIRMED, low, gap (refused with a clear error): unit conversion fails for lists and for
   unknowns.** `frequencies_in`, `item`, `spacing` and `resonances` have dimension None, so
   `frequencies_in(...) in kHz` is refused (b2.f). So "lists convert entry by entry" (PLAN 4) does
   not hold for any list I could build. Solved unknowns also have no
   dimension: `dL in mm` is refused (c4), and so is `Tg in K` (a1).
8. **CONFIRMED, low (refused):** a stretch area of 3.14 mm^2 on a string with a 2 mm diameter is
   refused as "differs" (e1).
9. **SUSPECTED, low:** in `_frequencies_in` the 100000-mode cap counts modes below `lo` too. A narrow
   band far above the fundamental is refused (clearly).

## Verified correct (hand-computed)
- Weight and buoyancy: 40 N, 35 N by volume, 35 N by fraction in g/cm^3, and 17.64 N from
  2000 g. A floating load is refused (numeric and symbolic). M solved from a frequency ratio
  with cm^3 volume gives 16.5 kg (c3).
- Stretch: area from the diameter gives 25*pi and 100*pi, mm^2 with cm gives 400 N, N/cm gives
  4 N, and an extension solved from a frequency gives 0.8 mm. A conflicting area is refused,
  and so are two tension routes.
- frequencies_in:
  - pipes with end correction: closed-open (100, 300, 500) and open-open (400 ... 1000),
    edges included;
  - closed-closed (200, 400) and rod (1250, 3750) are right;
  - lo = hi, an empty band, lo in kHz and solved unknowns all work;
  - lo > hi, lo in metres, a huge band and arbitrary dependence are refused.
- `in`:
  - prefixes (km/s, cm/ms, ms, kHz, g/cm) are right;
  - an unknown unit, a wrong dimension, comparisons, `in cm in m` and `in 1/s` are refused;
  - arbitrary checks still run, and export carries `unit`.
- Regressions unchanged: hanging sqrt(110), thermal 40 N, free.
