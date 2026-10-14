"""Compile the production name helpers against the independent DEF consumers."""
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from die_net_common import DEF_LAYER_RE, NET_HEADER_RE, PIN_CONN_RE, name_die, routing_layer_die
from test_fastroute_tech_layer_cache import REPOSITORY, production_function

SOURCE = Path(os.environ.get('GLOBAL_ROUTER_CPP',
    REPOSITORY / 'OpenROAD-GRT/openroad_src/src/grt/src/GlobalRouter.cpp'))


@unittest.skipUnless(shutil.which('g++') or shutil.which('clang++'), 'C++ compiler unavailable')
class PreparedMetadataNativeHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        folder = Path(cls.folder.name)
        source = SOURCE.read_text()
        bodies = '\n'.join(production_function(source, signature) for signature in
                           ('bool routingMetadataTokenSupported(', 'int routingMetadataNameDie(',
                            'int routingMetadataLayerDie('))
        program = folder / 'helpers.cpp'
        program.write_text('#include <algorithm>\n#include <iostream>\n#include <string>\n'
                           + bodies + r'''
int main() {
  std::string row;
  while (std::getline(std::cin, row)) {
    std::string value;
    for (size_t i = 2; i < row.size(); i += 2) {
      value.push_back(char(std::stoi(row.substr(i, 2), nullptr, 16)));
    }
    int result = row[0] == 'n' ? routingMetadataNameDie(value)
               : row[0] == 'l' ? routingMetadataLayerDie(value)
               : routingMetadataTokenSupported(value);
    std::cout << result << '\n';
  }
}
''')
        cls.binary = folder / 'helpers'
        compiler = shutil.which('g++') or shutil.which('clang++')
        result = subprocess.run([compiler, '-std=c++17', '-O2', '-Wall', '-Wextra',
                                 str(program), '-o', str(cls.binary)], text=True, capture_output=True)
        if result.returncode:
            raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def query(self, kind, values):
        rows = ''.join(kind + ' ' + value.encode().hex() + '\n' for value in values)
        result = subprocess.run([str(self.binary)], input=rows, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return [int(line) for line in result.stdout.splitlines()]

    def test_instance_mapping_matches_suffix_and_legacy_prefix_precedence(self):
        values = ['plain', 'cell_bottom', 'cell_upper', 'HBT_BOTIN_x', 'HBT_TOPIN_x',
                  'HBT_BOTIN', 'HBT_TOPIN', 'HBT_BOTIN_x_upper', 'HBT_TOPIN_x_bottom',
                  'LS_HBT_x', 'HBT_x', 'HBT_BOTIN_x_bottom']
        rng = random.Random(20261012)
        for _ in range(1000):
            values.append(rng.choice(['', 'HBT_BOTIN_', 'HBT_TOPIN_', 'LS_HBT_'])
                          + str(rng.randrange(10000))
                          + rng.choice(['', '_bottom', '_upper']))
        expected = [{'bottom': 1, 'upper': 2}.get(name_die(value), 0) for value in values]
        self.assertEqual(self.query('n', values), expected)

    def test_layer_mapping_matches_case_aliases_zero_and_large_numbers(self):
        values = ['metal0', 'metal0002', 'METAL02', 'MeTaL11', 'metal10', 'metal20',
                  'metal', 'metal-1', 'metal+2', 'metal2x', 'cut1', 'layer2']
        values += [case + str(number) for case in ('metal', 'METAL', 'mEtAl') for number in range(40)]
        values += ['metal' + '9' * 500, 'metal' + '0' * 500 + '2']
        expected = [{'bottom': 1, 'upper': 2}.get(routing_layer_die(value), 0) for value in values]
        self.assertEqual(self.query('l', values), expected)

    def test_accepted_tokens_roundtrip_legacy_header_and_unsupported_tokens_fall_back(self):
        accepted = ['simple', 'hier/name[12]_bottom', 'back\\slash', 'quoted"name',
                    '$literal', '+plus', 'punctuation{}<>.:,_-!?']
        unsupported = ['', 'with space', 'with\ttab', 'with\nnewline', 'with\rreturn',
                       'parenthesis(', 'parenthesis)', 'semicolon;', '\x00', '\x1c', '\x7f',
                       '中文', 'nonbreaking\u00a0space', 'unicode\u2003space']
        self.assertEqual(self.query('t', accepted), [1] * len(accepted))
        self.assertEqual(self.query('t', unsupported), [0] * len(unsupported))
        for token in accepted:
            self.assertEqual(NET_HEADER_RE.match('- ' + token + ' ;').group(1), token)

    def test_ndr_and_sensitivity_names_that_inject_legacy_tokens_are_unsupported(self):
        ndr = '( __fixture_fixed_upper A )'
        sensitivity = '+ LAYER metal2'
        self.assertEqual(PIN_CONN_RE.findall('+ NONDEFAULTRULE ' + ndr),
                         [('__fixture_fixed_upper', 'A')])
        self.assertEqual(DEF_LAYER_RE.findall('+ SUPPLYSENSITIVITY ' + sensitivity),
                         ['metal2'])
        self.assertEqual(self.query('t', [ndr, sensitivity]), [0, 0])
        self.assertEqual(self.query('t', ['__fixture_safe_ndr', '__fixture_supply']), [1, 1])


if __name__ == '__main__':
    unittest.main()
