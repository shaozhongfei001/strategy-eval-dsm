'''DSM - Defensible Scoring Model for marketing strategy evaluation.

Layering (design doc 1.6), dependencies are strictly one-directional:

    L0a  weights_ahp / weights_combine / fixtures_gen   (no internal deps)
    L0b  weights_calibrate / whatif                     (may import L1-L5)
    L1   numeric / reason_codes / models / config / io_loaders
    L2   preflight
    L3   attainment / normalize / aggregate / grading
    L4   evidence / redline / pooling
    L5   sensitivity / triangulation / diagnostics
    L6   audit
    L7   reports

Invariants (design doc 1.6.3):
    INV-1  L1-L5 must never import L0a or L0b
    INV-2  L0b must never write into the production reports tree
    INV-3  a scoring run must never recompute entropy weights
'''

__version__ = '0.1.0'

DESIGN_DOC_VERSION = 'v1.1-FINAL'
