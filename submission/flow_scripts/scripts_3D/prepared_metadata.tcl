# Read-only compatibility checks around the submitted native metadata backend.
# DefOut emits NDR and supply/ground reference names verbatim. Reject all unsafe
# names in these small object sets, including unused rules/unconnected BTerms,
# before a native export can bypass the original DEF parser.
namespace eval prepared_metadata {}
proc prepared_metadata::token_supported {name} {
  return [expr {$name ne "" && [regexp {^[\x21-\x7e]+$} $name] &&
    [string first "(" $name] < 0 && [string first ")" $name] < 0 &&
    [string first ";" $name] < 0}]
}
proc prepared_metadata::export {path} {
  set reason ""
  if {[catch {
    set block [ord::get_db_block]
    set tech [ord::get_db_tech]
    foreach owner [list $tech $block] {
      foreach rule [$owner getNonDefaultRules] {
        if {![prepared_metadata::token_supported [$rule getName]]} {
          set reason unsupported_regular_ndr_token
          break
        }
      }
      if {$reason ne ""} { break }
    }
    if {$reason eq ""} {
      foreach bterm [$block getBTerms] {
        if {![prepared_metadata::token_supported [$bterm getName]]} {
          set reason unsupported_package_sensitivity_token
          break
        }
      }
    }
  } query_error]} {
    # A missing query must use the original parser, rather than omit a guard.
    set reason compatibility_query_unavailable
  }
  if {$reason ne ""} {
    set fp [open $path w]
    puts $fp "\{\"schema_version\":1,\"compatible\":false,\"reason\":\"$reason\"\}"
    close $fp
    return
  }
  ::grt::export_prepared_routing_metadata $path
}
