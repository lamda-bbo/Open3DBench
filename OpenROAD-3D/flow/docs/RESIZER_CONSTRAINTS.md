# 3D resizer constraints

The nangate45_3D platform defaults to `MAX_FANOUT=32`. `load_design`
applies it to the current design after reading each checkpoint's SDC,
including when a later stage restores the original synthesis SDC.
Other platforms are unchanged unless they define `MAX_FANOUT`.
An explicit make command-line value overrides the default; it must be a
positive integer. This is a repair constraint, not a guarantee that all
post-route nets meet it (clock/special nets and physical limitations remain).

`HBT_BOTIN` and `HBT_TOPIN` are excluded via `DONT_USE_CELLS`.
Their identity functions and zero-delay tables incorrectly make them appear
to be ideal buffering candidates. In the reproduced OpenROAD build this
caused the automatic maximum wire length to become zero. The Liberty models
remain loaded for inter-tier connectivity and timing; no existing HBT is
deleted and no timing arc is changed.

This change does not add setup/hold repair, modify placement inputs, or
change detailed-route iterations. The bp_fe verification runs explicitly
use `DETAILED_ROUTE_ARGS='-droute_end_iter 0'`.

Run the dependency-free checks from `OpenROAD-3D/flow`:

```
python3 -m unittest discover -s test -p test_resizer_constraints.py -v
```

For an integration check, load a representative placed ODB through
`load_design`, estimate placement parasitics, apply `DONT_USE_CELLS`, and
verify `rsz::find_max_wire_length` is positive. Run `repair_design -verbose`
and inspect fanout repairs, then verify the final routed design separately.
