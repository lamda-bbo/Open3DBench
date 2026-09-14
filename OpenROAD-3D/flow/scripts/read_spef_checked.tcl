# Compatibility boundary for the v1.1 prebuilt OpenROAD/OpenSTA runtime.
# Only labels are temporary. Canonical names are restored even on failure.
namespace eval open3d_spef {
  variable helper [file join $::env(SCRIPTS_DIR) normalize_spef_names.py]
}

proc open3d_spef::json_string {value} {
  set value [string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $value]
  return \"$value\"
}

proc open3d_spef::coverage {block report_path audit_path} {
  report_parasitic_annotation -report_unannotated > $report_path
  set stream [open $report_path r]
  set lines [split [read $stream] \n]
  close $stream
  set expected -1
  set partial -1
  set seen 0
  set no_load 0
  set disconnected 0
  set invalid {}
  set in_unannotated 0
  foreach line $lines {
    if {[regexp {^Found ([0-9]+) unannotated drivers\.} $line -> count]} {
      set expected $count
      set in_unannotated 1
      continue
    }
    if {[regexp {^Found ([0-9]+) partially unannotated drivers\.} $line -> count]} {
      set partial $count
      set in_unannotated 0
      continue
    }
    set name [string trim $line]
    if {!$in_unannotated || $name eq ""} { continue }
    incr seen
    set split_at [string last / $name]
    set term NULL
    if {$split_at >= 0} {
      set instance [$block findInst [string range $name 0 [expr {$split_at - 1}]]]
      if {$instance ne "NULL"} {
        set term [$instance findITerm [string range $name [expr {$split_at + 1}] end]]
      }
    } else {
      set term [$block findBTerm $name]
    }
    if {$term eq "NULL"} { lappend invalid $name; continue }
    set net [$term getNet]
    if {$net eq "NULL"} { incr disconnected; continue }
    set loads 0
    foreach pin [$net getITerms] {
      if {[$pin getIoType] in {INPUT INOUT}} { incr loads }
    }
    foreach pin [$net getBTerms] {
      if {[$pin getIoType] in {OUTPUT INOUT}} { incr loads }
    }
    if {$loads == 0} { incr no_load } else { lappend invalid $name }
  }
  set valid [expr {$expected >= 0 && $seen == $expected && $partial == 0 && [llength $invalid] == 0}]
  set stream [open $audit_path w]
  puts $stream [format {{"schema_version":1,"coverage_pass":%s,"unannotated":%d,"partially_unannotated":%d,"no_load":%d,"disconnected":%d,"invalid":%d}} \
    [expr {$valid ? "true" : "false"}] $expected $partial $no_load $disconnected [llength $invalid]]
  close $stream
  if {!$valid} {
    error "SPEF coverage failed: unannotated=$expected parsed=$seen partial=$partial invalid=[llength $invalid]; see $report_path"
  }
}

proc read_spef_checked {spef prefix} {
  set spef [file normalize $spef]
  set prefix [file normalize $prefix]
  # Keep the canonical SPEF immutable and retain inspectable sidecars.
  foreach suffix {.names.jsonl .normalized.spef .names.audit.json .read.log .coverage.rpt .coverage.json .status.json} {
    if {"$prefix$suffix" eq $spef} { error "SPEF output would overwrite its input" }
  }
  set status [open "$prefix.status.json" w]
  puts $status {{"schema_version":1,"success":false,"phase":"started"}}
  close $status
  set block [ord::get_db_block]
  set inventory "$prefix.names.jsonl"
  set normalized "$prefix.normalized.spef"
  set records {}
  set counter 0
  foreach kind {net instance} {
    if {$kind eq "net"} { set objects [$block getNets]; set letter N } else { set objects [$block getInsts]; set letter I }
    foreach obj $objects {
      set old [$obj getName]
      set alias OPEN3D_STA_${letter}_[incr counter]
      if {[$block findNet $alias] ne "NULL" || [$block findInst $alias] ne "NULL"} {
        error "Reserved temporary SPEF alias already exists: $alias"
      }
      lappend records [list $kind $obj $old $alias]
    }
  }
  set stream [open $inventory w]
  fconfigure $stream -encoding utf-8 -translation lf
  foreach record $records {
    lassign $record kind obj old alias
    puts $stream [format {{"kind":%s,"name":%s,"alias":%s}} \
      [open3d_spef::json_string $kind] [open3d_spef::json_string $old] [open3d_spef::json_string $alias]]
  }
  close $stream
  # Resolve every SPEF name before touching the database.
  exec python3 $open3d_spef::helper $spef $inventory $normalized "$prefix.names.audit.json"
  set changed {}
  set code [catch {
    foreach record $records {
      lassign $record kind obj old alias
      if {![$obj rename $alias]} { error "Failed to apply temporary alias for $old" }
      lappend changed [list $obj $old]
    }
    read_spef $normalized > "$prefix.read.log"
    set stream [open "$prefix.read.log" r]
    set messages [read $stream]
    close $stream
    if {[regexp {\[(WARNING|ERROR)} $messages]} {
      error "SPEF reader emitted a warning/error; see $prefix.read.log"
    }
    open3d_spef::coverage $block "$prefix.coverage.rpt" "$prefix.coverage.json"
  } result options]
  set restore_failed {}
  foreach record [lreverse $changed] {
    lassign $record obj old
    if {[catch {$obj rename $old} restored] || !$restored} { lappend restore_failed $old }
  }
  if {[llength $restore_failed]} { error "Failed to restore canonical names: $restore_failed" }
  if {$code} { return -options $options $result }
  set status [open "$prefix.status.json" w]
  puts $status {{"schema_version":1,"success":true,"canonical_names_restored":true}}
  close $status
  puts "SPEF checked: RC preserved, coverage passed, canonical names restored ($prefix)"
}
