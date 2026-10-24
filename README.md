# HackSHSID 2026 · Track 2 — AI 数据中心算电协同调度

单年 8,760 小时（1 h 分辨率）的算电协同调度模型 + Q2/Q3 实验台。
本项目把原先四个单文件程序（`schedule.py` / `sim.py` / `dispatch.py` / `figs.py`）拆成
"**模型层 / 实验层 / 资产层**" 三层，**数值结果与拆分前逐字节一致**（见 §6 验收）。

```bash
python main.py all          # 一条命令跑完全部四步（约 40 秒）
```

---

## 1. 目录结构

```
hackathon/
├── main.py                     单一入口：bench / program / ladder / figures / all / variables / bound
├── requirements.txt            numpy · pandas · matplotlib（只有画图用得到 matplotlib）
├── run.sh                      等价的 shell 包装（给不想记子命令的人）
│
├── track2/                     ── 模型层：只做计算，不读写文件、不打印表格 ──
│   ├── paths.py                所有目录的唯一声明处（其它文件一律不许出现路径字面量）
│   ├── inputs.py               输入：合成序列 / 读外部 CSV / 情景缩放
│   ├── scheduler.py            时段打分 priority_index + Case A 离线排布 + Case B 滚动排布
│   ├── balance.py              逐时能量平衡（run_battery 含储能，run_baseline = S0）
│   ├── metrics.py              年度指标、松弛下界、vs S0 / vs LB
│   ├── strategies.py           Q2 阶梯：S0 / S1 / S2 / S3(λ 扫描 + 非支配 + maximin 折中)
│   ├── validation.py           DoD 自检与 AB 输入一致性
│   ├── config/
│   │   ├── params.py           全部数值参数（唯一参数区）
│   │   ├── scenarios.py        三情景与 λ 取值
│   │   ├── schema.py           论文变量名→程序名→单位；8760 表列序；数据字典
│   │   └── fallback.py         Excel 零代码降级路径文本
│   └── reporting/
│       ├── console.py          控制台单行指标与论文表
│       ├── bounds.py           Q3 下界报告（两档口径 + 差距分解 + 不可达理由）
│       └── ladder.py           Q2 两张表 + 四句结论（由数字生成，不手写）
│
├── experiments/                ── 实验层：只做循环、落盘、打印 ──
│   ├── run_bench.py            8,760 h × 三情景 → var/bench/
│   ├── run_program.py          程序正本：S0 / Case A(λ 扫描) / Case B → stdout
│   ├── run_ladder.py           S0 / S1 / S2 / S3 × 三情景 → var/ladder/
│   ├── run_figures.py          四张图，只读 CSV → assets/figures/
│   └── run_all.py              串起上面四步，任一步失败即停
│
├── tests/
│   └── test_contract.py        8 条契约测试（无 pytest 也能跑）
│
├── var/                        ── 动态内容：程序生成的，随时可删可重建 ──
│   ├── bench/                  sim_<情景>.csv（8760×21）· scenario_summary.csv · data_dictionary.csv
│   ├── ladder/                 strategy_matrix.csv · pareto_<情景>.csv · Q2_strategy_matrix.md
│   └── archive/old_contract/   已作废的旧口径产物（MW 级系统），仅留可追溯，勿引用
│
└── assets/                     ── 资产：给人看、给报告用的成品 ──
    ├── figures/                fig_Q2-1_pareto · fig_Q2-2_bars · fig_D11-1_heatmap · fig_D11-2_typical_day
    ├── docs/                   Q2 对比实验定稿 · Q3 松弛下界论证 · 口径核对清单 · 提交材料互查表
    ├── submission/             平台提交包：封面图 · 自检/契约测试证据图 · 填写文案.md
    └── reference/              上游资源（只读）：作战 Workflow · Part1/Part2 · 对话记录 · 赛道对比 · schedule.py / sim.py 原型
```

**动态 vs 资产的分界**：`var/` 里全部是程序写出来的中间数据（表、生成式 md），删掉后一条命令即可复原；
`assets/` 里是成品与证据，图表由 `run_figures.py` 重建，`docs/` 由人维护，`reference/` 是从项目盘同步进来的
上游正本（赛题纪律、论文、对话沿革、重构前原型），**只读、不参与计算**，删掉不影响复现，只影响审计。
目录索引见 `assets/reference/README.md`：每个上游文件对应到引用它的那份文档。

---

## 2. 数据流

```
   config/params.py ─┐
                     ├─► inputs ──► scheduler ──► balance ──► metrics ──► experiments ──► var/
   config/scenarios ─┘   (合成/读入)  (何时干活)   (逐时平衡)   (年化指标)      (落盘/打印)
                                                                              │
                                                         var/ladder/*.csv ────┴──► run_figures ──► assets/figures
```

关键约束（重构时逐条保住）：

- **一套生成器**：`run_bench` 与 `run_program` 都调 `track2.inputs.build_inputs`，所以 bench 的 S0 行与 program 的 S0 行同源；`tests/test_contract.py::test_bench_and_program_agree_on_s0` 守着这条。
- **一套物理**：能量平衡只在 `track2/balance.py`；S0/S1/S2 都是"换规则"，不是"换模型"。
- **一套单位制**：price 元/kWh、carbon gCO₂e/kWh、功率 kW、电量 kWh、dt = 1 h。列名带单位后缀（`_kw` / `_kwh` / `_mwh` / `_pct` / `_h`），单位换算只允许出现在 `metrics.evaluate`。
- **一套路径**：任何文件系统访问都从 `track2.paths` 取，模型层不出现路径字面量。

---

## 3. 命名规范

| 对象 | 规则 | 例 |
|---|---|---|
| 包/模块 | 小写、单数、按**职责**命名（不按类型、不按作者） | `scheduler.py` 而非 `utils.py` |
| 配置 | `config/<是什么>.py` | `params` / `scenarios` / `schema` / `fallback` |
| 计算函数 | 动词短语，`run_` = 跑一次返回结果字典 | `run_battery` / `run_shifted` / `run_flat` |
| 自检函数 | `check_*` 返回 `(标签, 是否通过, 细节)` 三元组 | `check_invariants` |
| 指标键 | 严格等于论文变量名，百分比加 `_pct`、张量加单位 | `grid_energy` / `annual_cost` / `gap_to_LB` |
| 情景 | `base` / `high_price` / `green_scarce`（与论文 §1.1 #10 一致） | `sim_green_scarce.csv` |
| 图表文件 | `fig_<编号>_<slug>.png` | `fig_Q2-1_pareto.png` |
| 结果表 | `<用途>_<情景>.csv` | `pareto_base.csv` |
| 上游资源 | **保留原名**，不加前缀/日期，仅去掉项目盘目录层级 | `Track2-WorkingNotes-Part1.docx` |
| 文档 | 中文、下划线连接，编号在前 | `Q2_对比实验_定稿.md` |

**禁止事项**（重构后已无例外）：模型层 import 实验层；模型层写文件；任何模块自建目录而不是走 `paths`；
写入 `assets/reference/`（该目录只从上流同步，就地编辑会让核对清单的行号失效）；同一物理量出现两个名字
（例如 `carbon` 与 `grid_carbon` 并存）。

---

## 4. 运行方式

```bash
# 从干净状态重建一切
python main.py all

# 分步
python main.py bench                  # 三情景 8760 行表 + 13×3 项自检
python main.py program                # 论文 §4 的表：S0 / Case A / Case B（64 项自检）
python main.py ladder                 # Q2 四策略 × 三情景 + Pareto（90 项自检）
python main.py figures                # 四张图

# 口径与论证
python main.py variables              # 论文变量名 ↔ 程序名 ↔ 单位
python main.py bound                  # Q3 下界报告（两档口径 + 差距分解 + 不可达理由）

# 换参数（子命令后面的开关原样透传）
python main.py ladder --lam 0.4 --scenario base
python main.py program --inputs var/bench/sim_base.csv   # 用 bench 的表代替内置序列
python main.py bench --seed 7 --outdir /tmp/s7

# 契约测试
python tests/test_contract.py         # 8/8
```

也可从任意目录直接跑单个脚本（自带 `sys.path` 引导）：

```bash
python experiments/run_ladder.py --quiet
```

---

## 5. 规模

纯语句（去空行 / 注释 / docstring）：

| 层 | 行数 | 说明 |
|---|---:|---|
| `track2/`（模型层） | 557 | 含 config 72、reporting 137 |
| `experiments/`（实验层） | 541 | run_bench 148 · run_figures 156 · run_program 106 · run_ladder 100 · run_all 30 |
| `main.py` | 30 | 子命令派发 |
| `tests/` | 78 | 8 条契约测试 |
| **合计** | **1206** | 拆分前四文件合计 969 |

增量 237 行的构成（全部是结构性样板，不含新逻辑）：契约测试 +78、入口与编排 +61、路径模块 +16、
各模块 import 引导约 +40、`paths`/`config` 拆分带来的声明拆行约 +42。
任务卡上的单文件上限仍然满足：bench 148 ≤ 300、ladder 100（+ strategies 41）≤ 200。

---

## 6. 重构验收：数值逐字节一致

拆分前后对比同一份 `seed = 42` 的输出（md5）：

| 产物 | 结果 |
|---|---|
| `sim_base / sim_high_price / sim_green_scarce.csv` | 3/3 逐字节一致 |
| `scenario_summary.csv`、`data_dictionary.csv` | 2/2 逐字节一致 |
| `strategy_matrix.csv`、`pareto_<三情景>.csv` | 4/4 逐字节一致 |
| 四张 PNG | 4/4 逐字节一致 |
| **数据表合计** | **9/9** |
| `Q2_strategy_matrix.md` | 仅第 3 行的"生成命令"一行不同（`dispatch.py` → `main.py ladder`），数字全同 |

自检通过数不变：bench 13×3 = 39、program 64、ladder 90。契约测试 8/8。

---

## 7. 已知边界

- 参数仍是占位值：`solar_peak_kw`、`wind_mean_kw`、TOU 档位与电网因子都需要 D2 的外部锚定（省份电价目录、电网因子、PVWatts/ERA5、海辰产品参数）。
- 松弛下界**按构造不可达**：它要求把 2,786,526 kWh 塞进同一个小时，等于刚性峰值的 3,685 倍；储能只有需求量的 0.07%。所以报告的是"关闭率"，不是"接近最优"。
- `var/archive/old_contract/` 是 MW 级系统的旧口径产物，与论文口径（2 MWh / 6,565 MWh 年负载）不是同一个数据中心，已作废，勿在报告或答辩中引用。
