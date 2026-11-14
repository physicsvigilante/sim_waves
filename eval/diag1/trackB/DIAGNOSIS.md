# Track B: pulses meeting a junction (diagnostic 1)

## The combination
A `pulse` (supported component) on a string with a `junction` (supported component).
Harmonic waves on the same strings get `<w>_reflected` and `<w>_transmitted`; pulses do
not.

## What the software does (probes `b1`, `b2`, run before any change)
- **b1** (pulse on string a, junction at x = 0 to string b): the scene is accepted.
  - `front(p, t=1 s)` = 30 m. That is the uniform-string answer: the pulse is placed 30 m
    past the junction, on string b, still moving at string a's speed (30 m/s; b's is
    15 m/s).
  - `p_reflected` does not exist ("unknown name").
- **b2** (same pulse, no junction): front = 30 m, correct.

## Finding 1: a defect, not a restriction
The engine never refuses the pulse-at-junction combination. It silently ignores both the
junction and the medium's extent. This is a silent wrong answer: no physical justification,
and no rejection message.
- **Layer:** assembly (whole-system check missing; the pulse ignores the junction).
- **Fix to make after the diagnostic:** refuse, or handle (below).
- **Production changes:** none made during this diagnostic. It is recorded for the
  correction step.

## Finding 2: the missing reflection is a conservative software restriction, not physics
- **Physics:** for ideal strings (uniform each side, non-dispersive), the junction
  coefficients are frequency-independent:
  - r = (Z1 - Z2)/(Z1 + Z2) and t = 2 Z1/(Z1 + Z2);
  - every Fourier component of a pulse reflects and transmits alike;
  - so a pulse of any shape gives a reflected pulse r times as tall, and a transmitted
    pulse t times as tall and stretched by v2/v1 along x.
  - This is standard (the textbook case is a pulse on two joined strings) and the engine
    already has the coefficients.
- **Why the software cannot do it:**
  - A `pulse` has no shape or field. It is only a front position, so there is nothing to
    reflect.
  - This is the same representation gap as gap 8 in `LAYERS.md` (pulse tools: peak,
    piecewise profiles).
- **Where the restriction is justified:**
  - Non-uniform strings, such as hanging ropes or graded mu. They reflect continuously and
    shape is not preserved; that needs a different model.
  - Dispersive media, which the engine does not have.
  - On those strings the restriction should stay, with a message giving that reason.

## Responsible layers
- **assembly:** a pulse with a shape; junction handling for it.
- **observation:** pulse peak and pulse position for reflected and transmitted pulses.
- No new physical law is needed for the uniform case. The qualification boundary is
  "uniform, non-dispersive strings each side".

## Recommendation (not implemented here)
- Immediately: make the combination fail loudly (correction of finding 1).
- Then, as a bounded shared extension: pulses with a shape (a function of x - v t on the
  launch string), reflected and transmitted at junctions between uniform strings using the
  existing coefficients. They should be refused on non-uniform strings with the reason.
- **Implementation-cost hypothesis:** after this, pulse-at-junction, pulse-at-fixed/free-end
  and pulse-shape questions (peak, where two pulses cancel) need scene data only.
