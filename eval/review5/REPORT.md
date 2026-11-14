# Review 5: standing-wave patterns, envelope, max_over/min_over

Scratch scenes: eval/review5/{a1,b*,c*,d*,e*,f*,g1}.yaml. All findings CONFIRMED (ran) unless marked.

## Findings, by severity

1. **MEDIUM, silent wrong: max_over/min_over of sqrt return imaginary numbers.** (c13, c14)
   `min_over(t, sqrt(sin(t)))` -> `I`; `max_over(t, sqrt(-5 + 3*sin(t)))` -> `sqrt(2)*I`.
   Expected: an error (radicand goes negative; no real extremum). Cause: the sqrt branch
   recurses on the base without checking min(base) >= 0. Symbolic case
   `max_over(t, sqrt(B + C*sin(t)))` likewise returns sqrt(B + |C|) unguarded.

2. **MEDIUM, silent wrong / false error: mode_shape with unknown x has no range limit.** (g1, f1, f2)
   The 0..L check runs only for numeric x. `mode_shape(s, harmonic=1, x=x0) == 1/2` with
   `x0 > 2[m], x0 < 2.5[m]` on a 1 m string -> "solved x0 = 13/6" (a point off the string;
   expected inconsistent). Conversely `mode_shape(s,1,x=x0) == 1` has the single physical
   answer x0 = 1/2 but gives "infinitely many situations ... x0=1/2; 5/2; 9/2".

3. **MEDIUM, misleading error: solved unknowns are not usable in nodes/antinodes/harmonics.** (b5, b6, e4)
   With L solved (17/20), e solved (1/32) or n solved (4), `nodes(...)` still fails with
   "need a numeric length and end correction" / "need a numeric harmonic", and
   `harmonics(..., node_at=2*L/3)` with "the point must be a number inside the
   resonator", while `mode_shape` in the same scene works with the solved value (b = 1).
   FORMAT.md says of resonances "Unknowns are fine once solved"; the pattern functions
   apparently evaluate before substitution. Not silent, but blocks the natural
   "find L, then locate nodes" problem and the message points at the wrong cause.

4. **LOW, silent: subscript on a list is dropped.** (b20) `nodes(s, harmonic=3)[1]` returns
   the whole tuple (0, 1/3, 2/3, 1); `[1]` is read as a unit bracket. Expected an error.

5. **LOW, doc/semantics: envelope of far-apart frequencies.** (c11)
   `max_over(t, envelope(t, sin(t) + sin(3*t)))` = 2, but the true signal maximum is 1.5396
   (`max_over` on the raw sum correctly errors). The envelope bounds the signal; A1 + A2
   is attained only for near/incommensurate frequencies. Doc should say so.

6. **LOW, doc gap:** "Its period is 1/beat frequency" but `frequency_of(t, envelope(...))`
   errors "not a sinusoid" (c3); only `frequency_of(t, envelope(...)**2)` works (= 4).

7. **LOW:** end_correction on a [closed, closed] pipe is silently ignored (a1 cc; harmless).
   With end correction, `antinodes()` omits open-end antinodes (documented) so
   `count(antinodes(...))` is one or two short of the textbook count; `harmonics(open pipe,
   antinode_at=0)` gives `()` (a1 h4).

8. **LOW, confusing errors:** `-2*sqrt(...)`, `-2*abs(...)`, `K*abs(...)` (K real),
   `2*sqrt(...) + 1`, `1/sqrt(...)` all give bare "not a sinusoid in t" (c12, c15-c19);
   the doc does not state which wrappers are supported. `(2+sin(t))**2` errors with
   "2 different frequencies" (safe). Unknown integer n in mode_shape: "infinitely many,
   e.g. n=2" although n < 5 was given (negative n counted) (f6). `harmonics(upto=1000)` takes 13 s (f5).

## Verified correct (hand-computed)

- All eight end combinations, both orders: [open,closed] vs [closed,open] mirror
  correctly (L=0.85, n=3: nodes (17/60, 17/20) vs (0, 17/30)); open-open, closed-closed,
  free-free, fixed-free, free-fixed strings.
- End corrections: [open,closed] L=0.8, e=0.05, n=3 nodes (7/30, 4/5), antinode 31/60;
  [closed,open] 30 cm, e=0.6 cm, n=3 nodes (0, 51/250), antinode 51/500; [open,closed]
  n=5 nodes (69/1250, 111/625, 3/10); open-open L=0.9, e=0.05, n=2 nodes (1/5, 7/10).
  Pressure nodes/antinodes are the exact swap.
- Even harmonic in a mixed resonator: clear error; `harmonics()` lists odd only;
  symbolic n on mixed pipe demands 2*m - 1.
- harmonics: touch 1/3 -> (3,6,9); pluck centre -> (1,3,5); fixed-free L=0.7 node at 0.28
  -> (5); free-free; points at exact ends (node_at=0 -> all, no_node_at=L -> ());
  10[cm] = 0.1[m]; 0.3333 -> () while 16-digit 1/3 matches; count/min/max work;
  min of empty list errors.
- mode_shape: values, sign (antiphase negative), amplitude ratio -2*sqrt(2); numeric x
  outside -> error; missing unit / wrong unit / missing harmonic / harmonic 0 -> errors.
- Symbolic length: nodes -> clear error; mode_shape(x=L/3) = 1 correct.
- envelope: phases, cosines, negative coefficients, negative frequency, three terms with
  two frequencies (phasor merge: max 9, min 1), product form 2*sin*cos, symbolic and
  real-signed amplitudes (|A|+|B|, ||A|-|B||), waves via y(...); 1, 3 frequencies, constant
  part, t*sin, exp decay -> errors.
- max_over/min_over: abs with offsets (8, 2, 0), negative constants (-8, -2), negative
  prefactor on plain sinusoid (4, -8), sin**2, sqrt(abs), positive constant times sqrt,
  two-frequency raw sum -> error. r53/r54 expectations are right.
