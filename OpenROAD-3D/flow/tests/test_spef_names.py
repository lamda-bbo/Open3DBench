"""CPU-only tests: python3 -m unittest discover -s tests -p 'test_spef*.py'."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "normalize_spef_names.py"
spec = importlib.util.spec_from_file_location("normalize_spef_names", str(SCRIPT))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SPEF = r'''*SPEF "ieee 1481-1999"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER []
*C_UNIT 1 PF
*R_UNIT 1 OHM
*NAME_MAP
*1 u/n\.data\[0\]
*2 u/driver
*3 u/ram
*PORTS
clk I
*D_NET *1 0.123
*CONN
*I *2:Z O
*I *3:D[0] I
*CAP
1 *2:Z 0.0123
2 *1:1 0.1107
*RES
1 *2:Z *1:1 12.34
2 *1:1 *3:D[0] 0.001
*END
'''


class SpefNameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original.spef"
        self.inventory = self.root / "inventory.jsonl"
        self.output = self.root / "normalized.spef"
        self.audit = self.root / "audit.json"
        self.source.write_text(SPEF)
        self.rows = [
            {"kind": "net", "name": r"u/n.data\[0\]", "alias": "OPEN3D_STA_N_1"},
            {"kind": "instance", "name": "u/driver", "alias": "OPEN3D_STA_I_2"},
            {"kind": "instance", "name": "u/ram", "alias": "OPEN3D_STA_I_3"},
        ]

    def run_normalize(self):
        self.inventory.write_text("".join(json.dumps(row) + "\n" for row in self.rows))
        return module.normalize(self.source, self.inventory, self.output, self.audit)

    def test_only_name_map_changes(self):
        before = self.source.read_bytes()
        audit = self.run_normalize()
        self.assertEqual(before, self.source.read_bytes())
        self.assertEqual(audit["dnet_count"], 1)
        self.assertTrue(audit["rc_content_unchanged"])
        self.assertIn("*1 OPEN3D_STA_N_1", self.output.read_text())
        self.assertEqual(self.source.read_text().split("*PORTS", 1)[1],
                         self.output.read_text().split("*PORTS", 1)[1])

    def test_missing_name_fails(self):
        self.rows.pop()
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            self.run_normalize()

    def test_ambiguous_escaping_fails(self):
        self.rows.append({"kind": "net", "name": "u/n.data[0]", "alias": "OPEN3D_STA_N_4"})
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            self.run_normalize()

    def test_net_and_instance_same_name_use_reference_type(self):
        self.rows.append({"kind": "net", "name": "u/driver", "alias": "OPEN3D_STA_N_4"})
        self.run_normalize()
        self.assertIn("*2 OPEN3D_STA_I_2", self.output.read_text())

    def test_duplicate_map_fails(self):
        self.source.write_text(SPEF.replace("*PORTS", "*1 duplicate\n*PORTS"))
        with self.assertRaisesRegex(ValueError, "duplicate NAME_MAP"):
            self.run_normalize()

    def test_duplicate_alias_fails(self):
        self.rows[2]["alias"] = self.rows[1]["alias"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.run_normalize()

    def test_missing_map_reference_fails(self):
        self.source.write_text(SPEF.replace("*I *3:D[0]", "*I *9:D[0]"))
        with self.assertRaisesRegex(ValueError, "Missing or conflicting"):
            self.run_normalize()

    def test_empty_spef_fails(self):
        self.source.write_text("")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.run_normalize()

    def test_cannot_overwrite_source(self):
        self.output = self.source
        with self.assertRaisesRegex(ValueError, "must differ"):
            self.run_normalize()

    def test_rc_units_and_values_preserved(self):
        text = SPEF.replace("*C_UNIT 1 PF", "*C_UNIT 1000 FF").replace("12.34", "1.234e-2")
        self.source.write_text(text)
        self.run_normalize()
        self.assertIn("*C_UNIT 1000 FF", self.output.read_text())
        self.assertIn("1.234e-2", self.output.read_text())


if __name__ == "__main__":
    unittest.main()
