| id | attempts | engine_fit | answer |
|----|----------|-----------|--------|
| R1 | 1 | full | A, B, C |
| R2 | 1 | full | A |
| R3 | 2 | full | 500 ms |

Friction points:
1. Beat/same-instant comparisons (R1 D) need a reception time t; picking t so that both direct and echo sound exist for every sampled arbitrary speed is fiddly, and the wall/listener distances had to be fixed assumed numbers rather than arbitrary (scalings x89 would break the instant).
2. Two-sided bounds on an unstated length (R2) work only via a ranged arbitrary (above+below); symbols allow one bound and the doc shows only one-sided ranged examples.
3. Wording ambiguity "ms after the source passes N" (R3): emission vs reception time must be resolved by an assumption; an unknown emission time (tau) plus arrives_at is needed, there is no direct "time at which heard frequency equals f" observable.
