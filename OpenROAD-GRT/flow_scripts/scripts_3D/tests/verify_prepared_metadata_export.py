#!/usr/bin/env python3
"""Compare the actual native exporter with the actual DEF writer/old parsers.

Run in the official image with a freshly built candidate OpenROAD. All output
is separate from the input ODB; optional fixtures use separate processes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from die_net_common import (classify_net_connections, iter_net_connections,
                            parse_inst_die_map, parse_pin_die_map)
from diagnose_guide_connectivity import build_net_pins


def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]') + '"'


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


FIXTURE = r'''
set db [ord::get_db]
set block [ord::get_db_block]
set tech [ord::get_db_tech]
set lib [odb::dbLib_create $db __metadata_fixture_lib $tech]
$lib setBusDelimiters {<} {>}
$block setBusDelimiters {[} {]}
$block setDefUnits [expr {[$block getDbUnitsPerMicron] / 2}]
foreach master_name {__metadata_bottom __metadata_upper __metadata_plain} {
  set master [odb::dbMaster_create $lib $master_name]
  $master setWidth 200
  $master setHeight 400
  $master setType CORE
  foreach pin {A Z BOT TOP BUS<0>} {odb::dbMTerm_create $master $pin INPUT}
  $master setFrozen
}
proc fixture_inst {name master_name status x y orient} {
  set inst [odb::dbInst_create $::block [$::db findMaster $master_name] $name]
  $inst setOrient $orient
  $inst setOrigin $x $y
  $inst setPlacementStatus $status
  return $inst
}
proc fixture_connect {net inst pin {special 0}} {
  set iterm [$inst findITerm $pin]
  $iterm connect $net
  if {$special} {$iterm setSpecial}
}
set placed [fixture_inst __fixture_placed_bottom __metadata_bottom PLACED 50 70 R0]
set fixed [fixture_inst __fixture_fixed_upper __metadata_upper FIRM 450 600 MY]
set covered [fixture_inst __fixture_cover_bottom __metadata_bottom COVER 50 70 R0]
set negative [fixture_inst __fixture_negative_bottom __metadata_bottom PLACED -100 70 R0]
set unplaced [fixture_inst __fixture_unplaced_bottom __metadata_bottom UNPLACED 50 70 R0]
set rotated [fixture_inst __fixture_rotated_bottom __metadata_bottom PLACED 1000 2000 R90]
set literal [fixture_inst PIN __metadata_bottom PLACED 20 30 R0]
set split [odb::dbNet_create $block __fixture_locations_BOT]
foreach inst [list $placed $fixed $covered $negative $unplaced $rotated] {
  fixture_connect $split $inst A
}
set package [odb::dbBTerm_create $split A]
set bpin [odb::dbBPin_create $package]
odb::dbBox_create $bpin [$tech findLayer metal11] 0 0 100 100
set collision [odb::dbNet_create $block __fixture_literal_pin]
fixture_connect $collision $literal A
set bus [odb::dbBTerm_create $split {BUS[0]}]
set bpin [odb::dbBPin_create $bus]
odb::dbBox_create $bpin [$tech findLayer metal2] 0 0 100 100
set collision_bus [odb::dbNet_create $block __fixture_literal_bus]
fixture_connect $collision_bus $literal BUS<0>
odb::dbNet_create $block __fixture_zero_BOT
set single [odb::dbNet_create $block __fixture_single]
fixture_connect $single $placed Z
set legacy_top [fixture_inst HBT_TOPIN_metadata_fixture __metadata_bottom PLACED 400 500 R0]
set legacy_bot [fixture_inst HBT_BOTIN_metadata_fixture_upper __metadata_upper PLACED 600 700 R0]
set n [odb::dbNet_create $block __fixture_legacy_top]
fixture_connect $n $legacy_top A
set n [odb::dbNet_create $block __fixture_legacy_bot]
fixture_connect $n $legacy_bot A
set hbt [fixture_inst LS_HBT_metadata_fixture __metadata_plain PLACED 800 900 R0]
foreach pin {BOT TOP} {
  set n [odb::dbNet_create $block __fixture_hbt_$pin]
  fixture_connect $n $hbt $pin
}
set unknown [fixture_inst __fixture_unknown __metadata_plain PLACED 1200 1300 R0]
set n [odb::dbNet_create $block __fixture_known_and_unknown]
fixture_connect $n $placed BOT
fixture_connect $n $unknown A
set pure [odb::dbNet_create $block __fixture_pure_special]
$pure setSpecial
fixture_connect $pure $unknown BOT 1
set partial [odb::dbNet_create $block __fixture_partial_special]
$partial setSpecial
fixture_connect $partial $unknown TOP 1
fixture_connect $partial $placed TOP
odb::dbBTerm_create $partial __fixture_without_geometry
if {[$tech findLayer METAL02] eq "NULL"} {odb::dbTechLayer_create $tech METAL02 ROUTING}
set alias [odb::dbNet_create $block __fixture_layer_alias]
set term [odb::dbBTerm_create $alias __fixture_alias_pin]
set pin [odb::dbBPin_create $term]
odb::dbBox_create $pin [$tech findLayer METAL02] 0 0 100 100
'''

VARIANTS = {
    'fixture': ('', None),
    'mixed_package': (r'''
set pin [odb::dbBPin_create $package]
odb::dbBox_create $pin [$tech findLayer metal2] 0 0 100 100
''', 'package_pin_spans_both_dies'),
    'regular_wire': ('odb::dbWire_create $single\n', 'regular_net_wire'),
    'unicode_token': ('fixture_inst 中文_bottom __metadata_bottom PLACED 100 100 R0\n', 'unsupported_component_token'),
    'placement_token': ('fixture_inst FIXED_name __metadata_bottom COVER 100 100 R0\n', 'unsupported_component_token'),
    'property_definitions': ('odb::dbStringProperty_create $block __ADS_DEF_PROPERTY_DEFINITIONS__ {}\n', 'def_property_definitions'),
    'safe_ndr': (r'''
set ndr [odb::dbTechNonDefaultRule_create $block __fixture_safe_ndr]
$single setNonDefaultRule $ndr
''', None),
    'unsupported_ndr': (r'''
set ndr [odb::dbTechNonDefaultRule_create $block {( __fixture_fixed_upper A )}]
$single setNonDefaultRule $ndr
''', 'unsupported_regular_ndr_token'),
    'safe_sensitivity': (r'''
set sensitivity [odb::dbBTerm_create $single __fixture_safe_sensitivity]
$sensitivity disconnect
$package setSupplyPin $sensitivity
$package setGroundPin $sensitivity
''', None),
    'unsupported_supply_sensitivity': (r'''
set sensitivity [odb::dbBTerm_create $single {+ LAYER metal2}]
$sensitivity disconnect
$package setSupplyPin $sensitivity
''', 'unsupported_package_sensitivity_token'),
    'unsupported_ground_sensitivity': (r'''
set sensitivity [odb::dbBTerm_create $single {+ LAYER metal2}]
$sensitivity disconnect
$package setGroundPin $sensitivity
''', 'unsupported_package_sensitivity_token'),
}


def expected(def_path):
    instances, pins = parse_inst_die_map(def_path), parse_pin_die_map(def_path)
    nets = [[name, classify_net_connections(name, refs, instances, pins), len(refs)]
            for name, refs in iter_net_connections(def_path)]
    split = {name: [list(point) for point in points]
             for name, points in build_net_pins(def_path, True).items()}
    return nets, split


def run_variant(args, name, extra, fallback_reason):
    folder = args.output / name
    folder.mkdir(parents=True, exist_ok=False)
    metadata, reference, before, after = (folder / item for item in
                                         ('metadata.json', 'reference.def', 'before.odb', 'after.odb'))
    script = 'set_thread_count 1\nread_db ' + quote(args.odb) + '\n'
    if name != 'original':
        script += FIXTURE + extra
    script += ('write_db ' + quote(before) + '\nset started [clock microseconds]\n'
               + 'source ' + quote(Path(__file__).resolve().parents[1] / 'prepared_metadata.tcl') + '\n'
               + 'prepared_metadata::export ' + quote(metadata) + '\n'
               + 'puts "METADATA_EXPORT_SECONDS [expr {([clock microseconds]-$started)/1e6}]"\n'
               + 'write_db ' + quote(after) + '\nwrite_def ' + quote(reference) + '\n')
    (folder / 'verify.tcl').write_text(script)
    result = subprocess.run([str(args.openroad), '-exit', '-no_init', str(folder / 'verify.tcl')],
                            text=True, capture_output=True)
    (folder / 'openroad.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'{name}: {result.stdout[-5000:]}\n{result.stderr}')
    record = {'metadata_sha256': digest(metadata), 'reference_def_sha256': digest(reference),
              'before_odb_sha256': digest(before), 'after_odb_sha256': digest(after),
              'odb_unchanged': digest(before) == digest(after)}
    if not record['odb_unchanged']:
        raise AssertionError(f'{name}: exporter changed OpenDB')
    document = json.loads(metadata.read_text())
    timing = re.search(r'^METADATA_EXPORT_SECONDS (\S+)$', result.stdout, re.M)
    record['export_seconds'] = float(timing.group(1)) if timing else None
    record['compatible'] = document['compatible']
    if fallback_reason is None:
        if document.get('schema_version') != 1 or document['compatible'] is not True:
            raise AssertionError(f'{name}: unexpectedly unsupported metadata: {document}')
        nets, split = expected(reference)
        if document['nets'] != nets or document['split_net_pins'] != split:
            raise AssertionError(f'{name}: native data differs from DEF writer/parsers')
        record.update(nets=len(nets), strict_pin_nets=len(split),
                      strict_pin_points=sum(map(len, split.values())), exact=True)
        if name == 'fixture':
            labels = {name: (label, count) for name, label, count in nets}
            for net, label, count in [('__fixture_zero_BOT', '2d_bottom', 0),
                                      ('__fixture_literal_pin', '2d_upper', 1),
                                      ('__fixture_literal_bus', '2d_bottom', 1),
                                      ('__fixture_layer_alias', '2d_bottom', 1),
                                      ('__fixture_legacy_top', '2d_upper', 1),
                                      ('__fixture_legacy_bot', '2d_bottom', 1)]:
                if labels[net] != (label, count):
                    raise AssertionError(f'Bad fixture reference for {net}: {labels[net]}')
            if '__fixture_pure_special' in labels:
                raise AssertionError('Pure special net incorrectly entered regular NETS')
            origins = split['__fixture_locations_BOT']
            if origins[:2] != [['PIN', 10, 15], ['PIN', 10, 15]]:
                raise AssertionError(f'Package/instance name collision not preserved: {origins}')
            if any(point[0] in ('__fixture_cover_bottom', '__fixture_negative_bottom',
                               '__fixture_unplaced_bottom') for point in origins):
                raise AssertionError('Legacy excluded component entered strict pins')
    else:
        if document.get('compatible') is not False or document.get('reason') != fallback_reason:
            raise AssertionError(f'{name}: fallback differs: {document}')
        if name in ('mixed_package', 'unsupported_supply_sensitivity',
                    'unsupported_ground_sensitivity'):
            try:
                expected(reference)
            except ValueError as error:
                record['legacy_expected_failure'] = str(error)
            else:
                raise AssertionError('Legacy mixed-pin rejection did not occur')
        if name == 'unsupported_ndr':
            nets, _ = expected(reference)
            labels = {net: (label, count) for net, label, count in nets}
            if labels['__fixture_single'] != ('3d', 2):
                raise AssertionError('Legacy NDR connection injection did not occur')
            record['legacy_injected_net'] = ['__fixture_single', '3d', 2]
        record.update(exact=True, reason=fallback_reason)
    if args.remove_snapshots:
        before.unlink()
        after.unlink()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--openroad', required=True, type=Path)
    parser.add_argument('--odb', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fixtures', action='store_true')
    parser.add_argument('--remove-snapshots', action='store_true')
    args = parser.parse_args()
    args.openroad, args.odb, args.output = args.openroad.resolve(), args.odb.resolve(), args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'scope': 'Actual guarded candidate native export vs actual DEF writer and unchanged parser oracle',
              'compatibility_wrapper_sha256': digest(Path(__file__).resolve().parents[1] / 'prepared_metadata.tcl'),
              'openroad_sha256': digest(args.openroad), 'input_odb_sha256': digest(args.odb), 'variants': {}}
    variants = {'original': ('', None)}
    if args.fixtures:
        variants.update(VARIANTS)
    for name, (extra, fallback) in variants.items():
        report['variants'][name] = run_variant(args, name, extra, fallback)
        (args.output / 'REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
        print(name, 'PASS', report['variants'][name].get('export_seconds'), flush=True)
    report['status'] = 'PASS'
    (args.output / 'REPORT.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
