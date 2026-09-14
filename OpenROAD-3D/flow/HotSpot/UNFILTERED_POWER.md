# Preserve all reported physical-cell power

The thermal power reporter no longer removes instances based on their name,
design name, or total power. In particular, the former `max_cap* > 0.01 W`
and `bp_fe_top > 0.002 W` exclusions are removed.

The intentional 10x thermal power multiplier is unchanged. Grid geometry,
layer assignment, activity assumptions, library loading, and SPEF handling
are unchanged. This change does not modify the separate HBT proxy-power
attribution policy or certify vectorless activity or SPEF coverage.

## Regression test

From the flow directory:

```
python3 -m unittest discover -s test -p test_thermal_power_no_filter.py
```

The test requires `tclsh`, but not OpenSTA. It executes the production Tcl
with a mocked power report, covering a high-power RAM, a high-power
`max_cap` instance, name invariance, an empty grid, the last grid, and the
unchanged 10x multiplier. All three tests fail on the former reporter and
pass after the change.

## Routed-artifact validation (2026-09-14)

The patched production Tcl was also executed with the historical OpenSTA
2.6.0 image on existing routed bp_fe artifacts. All 200 grid values agree
with an independent unfiltered reconstruction to within 1e-9 W.

| Artifact | Thermal trace power (after 10x) | Peak temperature |
| --- | ---: | ---: |
| bp_fe / MoL-Tiling | 2.9120369573 W | 88.08 C |
| bp_fe / LoL cadb0013 | 2.3905390819 W | 79.54 C |

Artifact identity was checked against placement inputs: all 11 RAM
positions match MoL-Tiling and cadb0013, respectively. These are not
interchangeable with TCAD'25 Default/Padded results or evidence that a
historical failed placement is now a valid paper comparison. Regenerate
or retrieve the matching artifact before updating any other paper row.
