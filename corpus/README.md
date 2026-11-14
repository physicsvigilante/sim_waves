# Problem corpus

One YAML record per problem, transcribed from the Problems/ and Solutions/ images.
This is the reference set the engine and the LLM framing are tested against.

## Record fields
- `id`, `number`, `source` (problem + solution image paths)
- `format`: single_correct | multiple_correct | numerical | matrix_match
- `statement`: problem text (equations in plain ASCII/Unicode)
- `figure`: text description of any figure, with every number read off it; null if none
- `options`: option text; for matrix_match, Column I keys plus `column_ii`
- `answer`: book key (option letters, or mapping for matrix)
- `answer_value`: the key as a value/expression where meaningful
- `units`: units of answer_value
- `verified`: result of recomputing the answer independently, when done
- `kinds`: what the problem gives / asks (vocabulary below)
- `physics`: physical quantities involved
- `notes`: ambiguities, book errors, modelling remarks

## `kinds` vocabulary
- given_wavefunction: y(x,t) is supplied explicitly
- build_wavefunction: construct y(x,t) from stated parameters
- equation_form: options are candidate wavefunctions to compare
- inverse_condition: a condition must be solved for an unknown
- symbolic: answer is an expression, not a number
- graph_read: numbers must be read off a snapshot/graph
- graph_match: match a computed curve to drawn curves
- derived_medium: wave speed etc. must be derived from material properties
- nonuniform_medium: properties vary along the medium
- comparison / ratio: two setups compared
- point_timeseries_given: displacement of specific particles given vs t
- classification: decide which functions are travelling waves
- conceptual: statement-truth question with no numbers

## Status
- 22_Travelling_Waves: 33 records (complete). Questions missing from the source folders
  (e.g. 02 #10-11, 03 #1-2, #6-8) are simply absent in the images.
