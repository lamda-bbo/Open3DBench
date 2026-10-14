"""Compare streaming master discovery with the unchanged DEF section grammar."""
import hashlib
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'submission/src'))
spec = importlib.util.spec_from_file_location('streaming_run_router', ROOT / 'submission/src/run_router.py')
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


def legacy_masters(text):
    section = re.search(r'\bCOMPONENTS\s+\d+\s*;(.*?)\bEND COMPONENTS\b', text, re.S)
    if section is None:
        raise ValueError('DEF has no COMPONENTS section')
    return set(re.findall(r'^\s*-\s+\S+\s+(\S+)', section.group(1), re.M))


class CollateralStreamingTest(unittest.TestCase):
    def test_chunk_boundaries_match_legacy_section_and_master_grammar(self):
        cases = [
            'VERSION 5.8 ;\nCOMPONENTS 2 ;\n- a BUF_X1\n + PLACED ( 0 0 ) N ;\n- b INV_X1 ;\nEND COMPONENTS\nNETS 0 ;\nEND NETS\n',
            'END COMPONENTS\nCOMPONENTS\n 1\t;\n\t- inst α_X1 ;\nEND COMPONENTS',
            'xCOMPONENTS 0 ;\nEND COMPONENTS\nCOMPONENTS 1 ;\n- a A ;\nEND COMPONENTSx\n- b B ;\nEND COMPONENTS\n',
            'COMPONENTS 0 ;\nEND COMPONENTS\nCOMPONENTS 1 ;\n- later IGNORE ;\nEND COMPONENTS\n',
            'END COMPONENTS\nNO SECTION\n',
            'COMPONENTS 1 ;\n- a A ;\nEND COMPONENTS_suffix',
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.def'
            for text in cases:
                path.write_text(text)
                for size in range(1, 41):
                    with self.subTest(text=text, size=size):
                        try:
                            expected = legacy_masters(text)
                        except ValueError as error:
                            with self.assertRaisesRegex(ValueError, str(error)):
                                router.component_masters(path, size)
                        else:
                            self.assertEqual(router.component_masters(path, size), expected)

    def test_all_public_case_master_sets_match_full_text_oracle(self):
        root = ROOT / 'Open3DBench-offline-20260904/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724/cases'
        self.assertEqual(len(list(root.glob('*/grt_input/4_1_cts.def'))), 8)
        for path in sorted(root.glob('*/grt_input/4_1_cts.def')):
            with self.subTest(case=path.parents[1].name):
                self.assertEqual(router.component_masters(path), legacy_masters(path.read_text()))

    def test_streaming_hash_matches_binary_oracle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.def'
            for content in (b'', b'DEF\r\n', bytes(range(256)) * 8193):
                path.write_bytes(content)
                self.assertEqual(router.file_sha256(path), hashlib.sha256(content).hexdigest())


if __name__ == '__main__':
    unittest.main()
