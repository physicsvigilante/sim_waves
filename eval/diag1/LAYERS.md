# Run 4 capability gaps, attributed to charter layers (diagnostic 1)

**Source:** `eval/run4/GRADES.md`, section "Missing capabilities" (independent grader), plus
the authors' logs.

**Layers (charter section 4):** authoring = physical authoring; assembly = fresh assembly;
revision = structural revision; qualification = physical qualification; maths = mathematical
and numerical solution; observation = requested observations; teaching = teaching
exploration. "Response" is the preferred response from charter section 5.

| # | Gap (n problems) | Immediate blocker | Layer(s) | Response | Notes and uncertainty |
|---|---|---|---|---|---|
| 1 | Acoustic amplitude relations: p0 = B k s0, I = p0^2/(2 rho v) (9) | Gas media have no density/bulk-modulus link to wave amplitudes; there is no pressure observable | qualification (new relation) + observation | Reusable physical capability: an acoustic wave quantity set on fluid media | A real law; textbook-standard in one medium. Uncertain: whether sources (rays) should carry pressure amplitudes in Pa. |
| 2 | Liquid and solid media; rods (7) | `type: gas` only; no B or Y route; no rod resonator | qualification (media laws) + assembly (rod resonator) | Physical capability: fluid/solid media (v = sqrt(B/rho), sqrt(Y/rho)) | A rod resonator should reuse the Resonator mode logic (clamped = node, free = antinode). Authors disguised liquids as gas with gamma = 1, a correct value reached by an unfaithful route (A minor deviations). |
| 3 | Travel time over a length; non-uniform integrals (5) | No time-of-flight observable; `front()` wrong on non-uniform strings | observation + maths | Extend the observation service | The `front()` defect is fixed after the run (r58). A plain `travel_time(medium, from, to)` is still missing. |
| 4 | Closed forms from lists; loci (5) | Lists only support min/max/count; infinite families cannot be returned | observation + maths; authoring (attempt budget) | Extend the observation/maths service for families n*f1; loci out of scope | The ambiguity message hid a family (fixed, r61). Loci in x-y: a genuinely different output type, deferred. |
| 5 | Decibels; unknown inside log (4) | No dB service; the solver refuses log(unknown) with a misleading "inside a sine/cosine" message | maths (+ authoring: wrong message) | Extend the maths service; fix the message | Small and neutral: L = 10 log10(I/I0). Not new physics. |
| 6 | Springs, Hooke extension, load statics (4) | No mechanics outside waves | qualification (out of domain) | Retain the restriction for now; record hand steps as derivations | A different domain. Better served by a provenance tag "derivation" than by engine physics. |
| 7 | Gas extras: mixtures, rms speed, P with T (4) | Gas routes accept fixed key sets; no rms speed; no mixture rule | qualification (small extensions to the media law) | Physical capability, small | P with T needs density from the ideal gas law (rho = P M / (R T)). |
| 8 | Pulse tools: piecewise, peak, zeros (4) | A pulse has only `front`; no shape or field | assembly (pulse representation) + observation | Reusable assembly change (a pulse with a shape) | Linked to Track B (pulses at junctions). |
| 9 | Energy density, KE of a segment, power x area x time (3) | No energy observables; no integral service | observation + maths | Extend the observation service | Integral over x of an expression is a neutral maths service. |
| 10 | Partial standing waves; phasor extremes; hole in a pipe (3) | Antinode amplitude with partial reflection is computable (`max_over` on a sum) but authors did not find it; a side hole is not modelled | teaching/authoring (discoverability) + qualification (side hole) | Documentation example for the first; retain the restriction for the hole | Uncertain: whether this is an interface gap or only a documentation gap. |
| 11 | Source geometry: hemisphere, power-amplitude link, source by wavelength, symbolic distances (4) | `emitters` (power, intensity) and `sources` (amplitude, phase) are separate components with no link | assembly (component compatibility) | Improve the shared assembly: one source object carrying power and amplitude | This is the clearest composability defect: two components for one physical thing. |

## Summary by layer (a gap may count twice)
- **Qualification (new or extended physical law):** 1, 2, 6, 7, 10 (hole).
- **Assembly:** 2 (rod resonator), 8 (pulse shape), 11 (emitter/source split).
- **Observation and maths services:** 1, 3, 4, 5, 8, 9.
- **Authoring and teaching:** 4 (attempt budget), 5 (misleading message), 10
  (discoverability).

Gaps 1, 2 and 11 together are the "acoustics" milestone. Gap 11 shows that it should
unify the emitter and source objects, not only add laws.
