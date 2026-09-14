# v1.1 checked SPEF annotation

## Scope and release policy

This is a focused maintenance change based on the original `v1.1.0` commit
`9562531df1ebcbf6b8a4a04360a6be74c1c3ce0a`. It does not import the V2.0
architecture, change placement/CTS/routing algorithms, edit libraries, or replace
the evaluator binary. The original tag is immutable. Use the maintenance commit
explicitly and keep corrected evaluations separate from historical results.

The existing Docker image is supported. The regression used:

- Registry digest: `shiyunqi/open3dbench@sha256:32ab6667ca2a0708a6462b44a07cf6092828c3263f8a606c0184f31490e02235`
- Image ID: `sha256:6bbf54387f15666f186302060b25df18903ae623295d1c19ed6facfc04b62e32`
- OpenROAD: `v2.0-17198-g8396d0866`

## Defect and repair boundary

The old SPEF reader does not reliably resolve flattened OpenDB names containing
hierarchy separators or escaped punctuation. It can report an existing instance
as missing and fail to annotate real wire parasitics. The old STA runtime also
has a separate lumped-cap delay-calculator defect: it reuses a modified slew
across successive loads with different library slew thresholds. In the bp_be
write-mask network, the 30%-70% standard-cell and 20%-80% RAM definitions can
produce repeated 1.5x scaling across 32 RAM loads. The resulting extreme input
slew makes the following buffer's table extrapolation nonsensical.

Relevant upstream source for that OpenROAD version:

- [SPEF relative-name lookup](https://github.com/The-OpenROAD-Project/OpenSTA/blob/aa598a2f14c5c142e90391a69988523505e7db3d/parasitics/SpefReader.cc#L152)
- [Shared slew in the load loop](https://github.com/The-OpenROAD-Project/OpenSTA/blob/aa598a2f14c5c142e90391a69988523505e7db3d/dcalc/LumpedCapDelayCalc.cc#L138)

The v1.1 repository ships flow scripts, not the OpenROAD/STA source. This change
repairs the annotation boundary and rejects loaded-net annotation failures. It
does **not** claim to patch the underlying binary's lumped-cap implementation.
A future image update should separately fix/test that implementation without
changing the library threshold definitions. The adapter is for final routed
OpenRCX evaluation; it is not a general replacement for pre-route wireload STA.

## How it works

`scripts/read_spef_checked.tcl` is sourced by `scripts/final_report.tcl`:

1. Inventory original OpenDB net/instance names and unique temporary aliases.
2. Resolve every OpenRCX NAME_MAP entry against that inventory. Missing,
   duplicate or ambiguous identities are fatal. Net/instance reference types
   distinguish objects that share a name.
3. Write a normalized SPEF sidecar, replacing NAME_MAP labels only. Hash all
   other bytes independently to prove units, capacitances, resistances,
   connections and node references were preserved.
4. Temporarily rename the in-memory objects, read the normalized SPEF, and
   require no reader warnings/errors and no partially annotated drivers.
5. Resolve each wholly unannotated driver against OpenDB. Exempt only a
   disconnected driver or a net with no input/inout ITerm or output/inout BTerm.
   Any remaining loaded-net omission is fatal.
6. Restore all canonical names before timing/power reporting, on success **and
   on caught failures**. Do not write a renamed ODB, DEF, Verilog or SDC.

No false paths, input-slew clamps, RC rescaling, library modifications or silent
placement-RC fallbacks are introduced. The adapter fails closed on unsupported
input (for example, mapped `*P` port references); it is qualified for the
OpenRCX format emitted by the v1.1 image, not arbitrary vendor SPEF dialects.

The adapter uses the flow's existing `SCRIPTS_DIR` and Python 3 standard library.
Canonical `6_final.spef` remains the extraction artifact. Reports retain:

- `6_spef.names.jsonl`: reversible OpenDB name inventory;
- `6_spef.normalized.spef`: private STA read view (requires matching aliases);
- `6_spef.names.audit.json`: input/output hashes, D_NET count, unchanged-RC proof;
- `6_spef.read.log`: SPEF reader output (empty on the qualified regressions);
- `6_spef.coverage.rpt` and `.coverage.json`: annotation checks;
- `6_spef.status.json`: success is set only after coverage and name restoration.

For independent STA replay, load the **canonical** ODB/SDC/libraries and call
the checked reader on the **canonical** SPEF. Do not read the normalized
sidecar directly against original names, and do not rerun raw `read_spef` in
the old image and assume it gives the corrected result.

```tcl
# After loading the original ODB, SDC and Liberty set:
source $::env(SCRIPTS_DIR)/read_spef_checked.tcl
read_spef_checked /run/results/6_final.spef /new/reports/6_spef
```

## Regression evidence (2026-09-14)

All checkpoint replays used the same final ODB, SDC and original extracted SPEF,
propagated clocks, original libraries, and no path masking. Every canonical
instance/net name was checked after reading, and original input SHA-256 hashes
were checked before/after.

| Saved case | Original WNS / TNS (ns) | Checked WNS / TNS (ns) |
| --- | ---: | ---: |
| bp_be / Analytical | -4678.127930 / -652715.062500 | **-1.883880 / -827.819702** |
| aes / cadb1051 | -0.177027 / -8.457870 | **-0.233667 / -9.158494** |
| aes / cadb1021 | -0.238442 / -14.355800 | **-0.335398 / -20.881037** |

The full modified `final_report.tcl` also passed on a copied bp_be
`6_1_fill.odb`/SDC, including **fresh OpenRCX extraction**, checked annotation,
final artifacts and timing/power reporting. Its WNS agrees with the checkpoint
replay. This was not a rerun of placement, CTS or routing.

For bp_be, partial annotations fall from 5,162 to zero. The remaining 8,418
unannotated drivers comprise 8,137 no-load cases and 281 disconnected outputs;
none has a driven input or output port. Removing only `net3066`'s D_NET from a
diagnostic SPEF copy gives exactly one invalid loaded-net omission: evaluation
fails as required, canonical names are restored, and no timing metrics are
published by the replay test. Ten CPU-only name-adapter unit tests also pass.

These are evaluator corrections, **not optimization gains or signoff claims**.
The previous diagnostic -0.539 ns result after masking RAM write masks still
used incomplete RC and is not a corrected reference. Power-derived thermal
results and the full benchmark matrix need reevaluation before updating paper
tables; this change does not modify historical archives or paper files.

## Running tests

CPU-only (no OpenROAD required), from `OpenROAD-3D/flow`:

```bash
python3 -m unittest discover -s tests -p 'test_spef_names.py' -v
```

Real checkpoint replay, inside the existing evaluation image; mount the original
run read-only and use a **new** output directory. The flow's saved final ODB,
SDC, SPEF, original platforms/configuration and normal Make environment are
required. Paths below are examples, not repository dependencies.

```bash
python3 tests/replay_spef.py \
  --flow /saved/bp_be/flow \
  --design-config designs/nangate45_3D/bp_be_top/config.mk \
  --make-var FLOW_VARIANT=mol --make-var DEF_VERSION=bp_be \
  --output /new/bp_be_checked

python3 tests/replay_spef.py \
  --flow /saved/bp_be/flow \
  --design-config designs/nangate45_3D/bp_be_top/config.mk \
  --make-var FLOW_VARIANT=mol --make-var DEF_VERSION=bp_be \
  --output /new/bp_be_missing_net --remove-net net3066
```

The second command is a negative test: it succeeds only when the deliberately
incomplete SPEF is rejected and canonical names are restored. Its modified
SPEF is written only to the new test output directory.
