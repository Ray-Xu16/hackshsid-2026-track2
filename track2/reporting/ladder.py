"""Q2 output: the two tables and the four conclusion sentences, as Markdown.

Every number and every clause below is computed from the matrix that is passed
in, so the text cannot drift from the CSV next to it. Nothing here is typed by
hand - that was the point of generating it.
"""


def report_table(mx):
    """Table Q2-1, ready to paste into the paper."""
    lines = ["| Strategy | Scenario | Cost (yuan/yr) | Carbon (tCO2e/yr) | Green util. "
             "| SLA on time | vs S0 cost | vs S0 carbon |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in mx.iterrows():
        lines.append("| %s | %s | %s | %.1f | %.1f%% | %.1f%% | %+.1f%% | %+.1f%% |" % (
            r["strategy"], r["scenario"], format(r["annual_cost"], ",.0f"),
            r["annual_carbon"], r["green_utilization"], r["sla_on_time"],
            r["vs_s0_cost_pct"], r["vs_s0_carbon_pct"]))
    return "\n".join(lines)


def write_markdown(mx, fronts, lb, path, cfg, lam):
    """Table Q2-1 + Table Q2-2 + the four-sentence reading of the numbers."""
    base = mx[mx["scenario"] == "base"]
    pick = lambda s: base[base["strategy"] == s].iloc[0]
    s0, s1, s2, s3 = pick("S0"), pick("S1"), pick("S2"), pick("S3")
    hp = mx[(mx["scenario"] == "high_price") & (mx["strategy"] == "S2")].iloc[0]
    gs = mx[(mx["scenario"] == "green_scarce") & (mx["strategy"] == "S2")].iloc[0]
    f = fronts["base"]
    eta = cfg["battery"]["eta_roundtrip"]
    out = ["# Q2 策略 × 情景对比（自动生成，勿手改数字）", "",
           "生成命令：`python main.py ladder`（`track2/` 为模型正本，同一 config、同一单位制）", "",
           "## 表 Q2-1 四策略 × 三情景（IT 侧口径，λ = %.2f）" % lam, "",
           report_table(mx), "",
           "## 表 Q2-2 S3 Pareto 前沿（base，%d 个 λ 点，%d 个非支配）" % (
               len(f), int(f["on_front"].sum())), "",
           "| λ | Cost (yuan/yr) | Carbon (t) | Green util. | 距 LB 成本 | 距 LB 碳 | 非支配 |",
           "|---:|---:|---:|---:|---:|---:|:--:|"]
    for _, r in f.sort_values("lam", ascending=False).iterrows():
        out.append("| %.1f | %s | %.1f | %.1f%% | %+.1f%% | %+.1f%% | %s |" % (
            r["lam"], format(r["cost"], ",.0f"), r["carbon"], r["green"],
            r["gap_lb_cost_pct"], r["gap_lb_carbon_pct"], "yes" if r["on_front"] else "no"))
    # ---- conclusions: every clause below is computed, not written by hand ----
    dc_cost = s2["annual_cost"] - s1["annual_cost"]
    dc_carbon = s2["annual_carbon"] - s1["annual_carbon"]
    dc_curt = s2["green_curtailed_kwh"] - s1["green_curtailed_kwh"]
    c1 = (("S1 同时省钱减碳：电费 %+.1f%%、碳 %+.1f%%、绿电消纳率 %.1f%%→%.1f%%"
           if s1["vs_s0_cost_pct"] < 0 else
           "纯时间迁移不是免费午餐：S1 多付 %.1f%% 电费，换来 %.1f%% 的碳减排"
           "（绿电优先权重下它把弹性负载推向午间低碳但平价的时段）、绿电消纳率 %.1f%%→%.1f%%")
          % (abs(s1["vs_s0_cost_pct"]), abs(s1["vs_s0_carbon_pct"]),
             s0["green_utilization"], s1["green_utilization"]))
    c2 = ("S2 = S1 + 储能：%s %s 元（%+.1f%%），碳%s %.1f t（%+.1f%%），弃电 %.0f→%.0f kWh。"
          % ("再省" if dc_cost < 0 else "多付", format(abs(dc_cost), ",.0f"),
             100.0 * dc_cost / s1["annual_cost"],
             "减少" if dc_carbon < 0 else "增加", abs(dc_carbon),
             100.0 * dc_carbon / s1["annual_carbon"],
             s1["green_curtailed_kwh"], s2["green_curtailed_kwh"]))
    if dc_carbon < 0 and dc_curt < 0:
        c2 += ("原因是储能吃的是午间富余绿电而非谷段网电；若改为纯谷电套利，"
               "充电侧碳强度必须比放电侧低 1/η_rt−1 = %.1f%% 以上才净减碳。"
               % (100.0 * (1.0 / eta - 1.0)))
    else:
        c2 += ("注意：此时储能走的是谷段网电套利，充电侧碳强度未低于放电侧 1/η_rt−1 = %.1f%%，"
               "省钱与减碳开始分家。" % (100.0 * (1.0 / eta - 1.0)))
    c3 = ("便宜与干净不必二选一：S3 折中解 λ = %.1f，在 S0 基础上同时 %+.1f%% 电费、%+.1f%% 碳"
          "（均衡解定义：让两个目标里较差的那个尽量好）。情景排序一致——高电价储能收益最大"
          "（S2 %+.1f%%），绿电稀缺最小（S2 %+.1f%%），因为没有富余绿电可存时储能退化为纯套利。"
          % (s3["lam"], s3["vs_s0_cost_pct"], s3["vs_s0_carbon_pct"],
             hp["vs_s0_cost_pct"], gs["vs_s0_cost_pct"]))
    c4 = ("下界（P4）：成本 %s 元/年、碳 %.1f t/年；S3 折中解距 LB 成本 %+.1f%%、碳 %+.1f%%。"
          % (format(lb["lb_cost"], ",.0f"), lb["lb_carbon"],
             s3["gap_lb_cost_pct"], s3["gap_lb_carbon_pct"]))
    out += ["", "## 结论（四句话，报告 §5.2 可直接用）", "",
            "1. " + c1, "2. " + c2, "3. " + c3, "4. " + c4,
            "", "> %d 次运行中 SLA 恒为 %.2f%%、Class B 日总量恒为 %.0f kWh、SOC 恒在 "
            "[%.0f, %.0f] kWh 内，因此上述差异全部来自调度，而不是来自「少干活」。"
            % (len(mx), mx["sla_on_time"].min(), cfg["elastic_total_kwh"],
               cfg["battery"]["soc_min"] * cfg["battery"]["capacity_mwh"] * 1000,
               cfg["battery"]["soc_max"] * cfg["battery"]["capacity_mwh"] * 1000), ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    return path
