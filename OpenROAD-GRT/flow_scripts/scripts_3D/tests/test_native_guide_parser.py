#!/usr/bin/env python3
"""Compile the actual guide fast parser and compare accepted rows to the old reader."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from test_fastroute_tech_layer_cache import REPOSITORY, production_function

SOURCE = Path(os.environ.get('GLOBAL_ROUTER_CPP',
    REPOSITORY / 'OpenROAD-GRT/openroad_src/src/grt/src/GlobalRouter.cpp'))

HEADERS = r'''
#include <array>
#include <charconv>
#include <cstdint>
#include <iostream>
#include <limits>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <vector>
'''

HARNESS = r'''
struct Parsed {
  std::array<int, 4> coordinates;
  std::string layer;
};
void require(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}
Parsed oldParse(const std::string& line) {
  std::stringstream stream(line);
  std::string word;
  std::vector<std::string> tokens;
  // Preserve the original reader's EOF handling, including trailing-space
  // duplicate tokens. This is intentionally not an idiomatic stream loop.
  while (!stream.eof()) {
    stream >> word;
    tokens.push_back(word);
  }
  if (tokens.size() != 5) throw std::runtime_error("old token count");
  return {{std::stoi(tokens[0]), std::stoi(tokens[1]),
           std::stoi(tokens[2]), std::stoi(tokens[3])}, tokens[4]};
}
size_t accepted = 0;
size_t fallback = 0;
void compare(const std::string& line, int expected = -1) {
  int coords[4] = {173, 173, 173, 173};
  size_t offset = 999999;
  bool fast = parseWrittenGuideRect(line, coords, offset);
  if (expected != -1) require(fast == (expected != 0), "unexpected fast/fallback classification");
  if (!fast) {
    ++fallback;
    return; // Production delegates these bytes to the unchanged old tokenizer.
  }
  ++accepted;
  require(offset < line.size(), "invalid layer offset");
  auto old = oldParse(line);
  require(old.layer == line.substr(offset), "layer differs from old tokenizer");
  for (int i = 0; i < 4; ++i) {
    require(old.coordinates[i] == coords[i], "coordinate differs from stoi");
  }
}
int main() {
  try {
    for (const std::string& line : {
        "0 0 0 0 metal1", "-0 00 000 -000 metal20",
        "-2147483648 2147483647 -1 1 metal11",
        "1 2 3 4 unknown_layer", "1 2 3 4 +layer", "1 2 3 4 metal02",
        "1 2 3 4 metal\\escaped", "1 2 3 4 \xE5\xB1\x82"}) compare(line, 1);
    for (const std::string& line : {
        "", "(", ")", "net", "1 2 3 4", "1 2 3 4 ",
        " 1 2 3 4 metal1", "1  2 3 4 metal1", "1 2 3 4  metal1",
        "1\t2 3 4 metal1", "1 2 3 4\tmetal1", "1 2 3 4 metal1 ",
        "1 2 3 4 metal1\t", "1 2 3 4 metal1\r", "1 2 3 4 metal1\n",
        "1 2 3 4 metal1\v", "1 2 3 4 metal1\f", "1 2 3 4 metal 1",
        "+1 2 3 4 metal1", "1 +2 3 4 metal1", "1 2 +3 4 metal1",
        "1 2 3 +4 metal1", "--1 2 3 4 metal1", "- 2 3 4 metal1",
        "2147483648 2 3 4 metal1", "-2147483649 2 3 4 metal1",
        "1 2 3 9999999999999999999999999999999 metal1",
        "1x 2 3 4 metal1", "1 2.0 3 4 metal1", "1 2 3e2 4 metal1",
        "1 2 3 0x20 metal1", "x 2 3 4 metal1"}) compare(line, 0);
    std::string embedded_nul("1 2 3 4 metal\0suffix", 20);
    compare(embedded_nul, 1);
    std::mt19937 rng(20261007);
    std::uniform_int_distribution<int> coordinate(
        std::numeric_limits<int>::min(), std::numeric_limits<int>::max());
    for (int trial = 0; trial < 100000; ++trial) {
      std::string line;
      for (int i = 0; i < 4; ++i) line += std::to_string(coordinate(rng)) + ' ';
      line += "metal" + std::to_string(1 + rng() % 20);
      compare(line, 1);
      if (trial % 5 == 0) {
        compare(" " + line, 0);
        compare(line + " ", 0);
        auto first = line.find(' ');
        std::string tabbed = line;
        tabbed[first] = '\t';
        compare(tabbed, 0);
        compare(line.substr(0, first) + "x" + line.substr(first), 0);
        compare(line.substr(0, first) + " " + line.substr(first), 0);
      }
    }
    std::cout << "accepted=" << accepted << " fallback=" << fallback << " PASS\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
'''


@unittest.skipUnless(shutil.which('g++') or shutil.which('clang++'), 'C++ compiler unavailable')
class NativeGuideParserTest(unittest.TestCase):
    def run_variant(self, flags):
        source = SOURCE.read_text()
        helper = production_function(source, 'bool parseWrittenGuideRect(')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            program = path / 'parser.cpp'
            program.write_text(HEADERS + helper + '\n' + HARNESS)
            compiler = shutil.which('g++') or shutil.which('clang++')
            compiled = subprocess.run([compiler, '-std=c++17', *flags, str(program),
                                       '-o', str(path / 'parser')], text=True, capture_output=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            env = dict(os.environ)
            # The workspace command sandbox uses ptrace, which LeakSanitizer
            # cannot inspect. AddressSanitizer and UBSan remain enabled.
            env['ASAN_OPTIONS'] = env.get('ASAN_OPTIONS', '') + ':detect_leaks=0'
            ran = subprocess.run([str(path / 'parser')], text=True,
                                 capture_output=True, env=env)
            self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
            self.assertIn('accepted=100009 fallback=100032 PASS', ran.stdout)
            print('guide_parser_sha256=' + hashlib.sha256(helper.encode()).hexdigest(),
                  ran.stdout.strip())

    def test_production_helper_matches_original_decimal_reader(self):
        self.run_variant(['-O2'])

    def test_production_helper_is_clean_under_address_and_undefined_sanitizers(self):
        self.run_variant(['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'])


if __name__ == '__main__':
    unittest.main()
