# Summary

The Nangate Open Cell Library is a generic open-source, standard-cell
library provided for the purposes of research, testing, and exploring EDA
flows. This library is purposely non-manufacturable.

Version: PDKv1.3_v2010_12.Apache.CCL

# Source

Downloaded from https://projects.si2.org/openeda.si2.org/project/showfiles.php?group_id=63#503

# Modifications

- Performed abstract generation from the gds files to avoid polygon pin shapes in the LEF.
- Added additional files and info required for the OpenROAD flow.
- Fix contact enclosure by poly on cell `AOI21_X1` (rule CONTACT.5).
- Added LICENSE.

# Hybrid-Bonding Rule

`hb_layer` uses a 0.5 um cut with 5.9 um edge-to-edge spacing. Both the
generated-via rule and the resulting minimum center-to-center HBT pitch are
6.4 um. The same spacing applies to different-net and same-net HBT cuts.

Each HBT is modeled as a 3.0 ohm series via with 0.6 fF total ground
capacitance. Before fixed-via conversion, the HBT Liberty input pin carries
0.6 fF. After extraction, the same 0.6 fF is split equally between the two
ends of the extracted HBT via resistor.

Validate every LEF in this platform with:

```bash
python3 validate_hbt_lefs.py
```
