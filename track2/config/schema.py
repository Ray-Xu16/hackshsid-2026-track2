"""The naming contract: paper variable -> program name -> unit.

Single source of truth for the mapping (Track2-WorkingNotes-Part1 Sections
1.1-1.2). If a column name changes anywhere in the project it must change here
first, and ``python main.py variables`` prints this table for the paper.
"""

VARIABLE_MAP = """
paper variable          program name          unit
price[t]                price                 yuan/kWh
grid_carbon[t]          grid_carbon           gCO2e/kWh
solar[t]                solar                 kW
wind[t]                 wind                  kW
green[t]                green                 kW          (solar + wind)
rigid_load[t]           rigid_load            kW
elastic_total[d]        elastic_total_kwh     kWh/day     (fixed per day)
battery                 battery               MWh, MW, -, -
task_attrs              task_attrs            kWh, h, kW
lambda                  lam                   -           (lambda is a Python keyword)
scenario                scenario              -
grid_energy[t]          grid_energy           kWh
green_used[t]           green_used            kWh         (direct + via battery)
green_curtailed[t]      green_curtailed       kWh
soc[t]                  soc                   kWh
charge[t]               charge                kW          (AC side)
discharge[t]            discharge             kW          (AC side)
task_schedule           task_schedule         h, kW, h
annual_cost             annual_cost           yuan/yr
annual_carbon           annual_carbon         tCO2e/yr
green_utilization       green_utilization     %
sla_on_time             sla_on_time           %
pue                     pue                   -
vs_baseline             vs_baseline           % vs S0
gap_to_LB               gap_to_LB             % vs LB
"""

# Column order of the 8,760-row hourly table. Order matters: the zero-code
# Excel fallback quotes these letters, so do not reorder without updating
# track2/config/fallback.py.
HOURLY_COLUMNS = ["hour", "timestamp", "day", "hour_of_day", "tou_segment",
                  "price", "grid_carbon", "solar", "wind", "green",
                  "rigid_load", "elastic_total_kwh", "elastic_load", "it_load",
                  "grid_energy", "green_used", "green_curtailed",
                  "soc", "charge", "discharge", "scenario"]

# Row per column of the hourly table, written to var/bench/data_dictionary.csv.
DATA_DICT = [
    ("hour", "Part 1 tab. 1.1", "-", "0-8759 running index"),
    ("timestamp", "Part 1 tab. 1.1", "-", "hourly stamps of the modelled year"),
    ("day", "Part 1 tab. 1.1", "-", "day of year, 1-365"),
    ("hour_of_day", "Part 1 tab. 1.1", "h", "clock hour, 0-23"),
    ("tou_segment", "Part 1 tab. 1.1 #1", "-", "valley / flat / peak / sharp (sharp = evening sub-peak of peak)"),
    ("price", "Part 1 tab. 1.1 #1  price[t]", "yuan/kWh", "TOU nominal level x (1 + N(0, 3%))"),
    ("grid_carbon", "Part 1 tab. 1.1 #2  grid_carbon[t]", "gCO2e/kWh", "640 at night to 430 at noon, + N(0, 20), clipped [300, 800]"),
    ("solar", "Part 1 tab. 1.1 #3  solar[t]", "kW", "sine day shape x cloud factor (<= nameplate 800 kW)"),
    ("wind", "Part 1 tab. 1.1 #4  wind[t]", "kW", "mean 200 kW + N(0, 120), clipped at 0"),
    ("green", "Part 1 tab. 1.1 #3-#4", "kW", "solar + wind, used on site first (self-consumption)"),
    ("rigid_load", "Part 1 tab. 1.1 #5  rigid_load[t]", "kW", "Class A: 500 + 150 sin(2pi(h-8)/24) + N(0, 30), never moved"),
    ("elastic_total_kwh", "Part 1 tab. 1.1 #6  elastic_total[d]", "kWh/day", "Class B: fixed 6,000 kWh per day"),
    ("elastic_load", "Part 1 tab. 1.1 #6", "kW", "Class B profile; S0 spreads it evenly over the 24 h window"),
    ("it_load", "Part 1 tab. 1.2", "kW", "rigid_load + elastic_load (facility side = x pue)"),
    ("grid_energy", "Part 1 tab. 1.2 #1  grid_energy[t]", "kWh", "grid purchase after green and battery"),
    ("green_used", "Part 1 tab. 1.2 #2  green_used[t]", "kWh", "direct green + green routed through the battery"),
    ("green_curtailed", "Part 1 tab. 1.2 #2  green_curtailed[t]", "kWh", "green output that could not be used on site"),
    ("soc", "Part 1 tab. 1.2 #3  soc[t]", "kWh", "state of charge after the hour; S0 has no battery so it is flat"),
    ("charge", "Part 1 tab. 1.2 #3  charge[t]", "kW", "battery AC charging power (0 in S0)"),
    ("discharge", "Part 1 tab. 1.2 #3  discharge[t]", "kW", "battery AC discharge power (0 in S0)"),
    ("scenario", "Part 1 tab. 1.1 #10  scenario", "-", "base / high_price / green_scarce, same code different inputs"),
]
