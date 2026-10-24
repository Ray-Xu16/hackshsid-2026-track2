"""Console rendering: one-line metrics and the paper table."""


def report(name, m, tag=""):
    print("%-34s cost %9.0f yuan  carbon %7.1f t  green %5.1f%%  SLA %5.1f%%  "
          "vs S0: cost %+6.1f%% carbon %+6.1f%%  gap to LB: cost %+5.1f%% carbon %+6.1f%%%s"
          % (name, m["annual_cost"], m["annual_carbon"], m["green_utilization"],
             m["sla_on_time"],
             m["vs_baseline"]["cost_pct"], m["vs_baseline"]["carbon_pct"],
             m["gap_to_LB"]["cost_pct"], m["gap_to_LB"]["carbon_pct"], tag))


def print_table(rows):
    """Table of Part 2 Section 4."""
    head = ("Case", "Cost (yuan/yr)", "Carbon (tCO2e/yr)", "Green utilization",
            "vs. S0: cost", "vs. S0: carbon")
    print("\n%-34s %15s %18s %19s %13s %15s" % head)
    for r in rows:
        print("%-34s %15s %18s %19s %13s %15s" % r)
