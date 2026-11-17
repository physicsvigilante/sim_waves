| id | attempts | engine_fit | answer |
|----|----------|-----------|--------|
| R1 | 3 (v1 scene error: speed() arg; v2 em v=3e8 refused; v3 solves but 'us' unit unknown) | none | B |
| R2 | 1 | full | A, B |
| R3 | 1 | full | A |
| R4 | 1 | full | A, C |

Three friction points:
1. em medium: cannot use the book's rounded c = 3e8 m/s (v refused as faster than c) and no convention-tagged way to set c; also the microsecond unit "us" is missing (only s, ms), which cost R1 its last attempt.
2. nearest() refuses ties between options sharing a value (R3 options A and D both 507 Hz), so multi-quantity options need manual pairing.
3. Moving-ray scenes need an explicit time or emitted= and an arbitrary separation, and a moving reflector/listener must be written as reflector + point with velocities; the doc gives no way to state "beat with the transmitted signal" except frequency(gun) (not verified, since R1 evaluation failed).
