# 04 · 语义 JSON 与数学化闸门（对接 econ-math-mapper）

**来源**：schema 与十项校验**复制精简自** `econ-math-mapper` `references/01_always/l2_schema.md` 与其 L4 校验层；底本见 `00-guide-full.md` §八。

**角色**：本技能是 `econ-math-mapper` 的**管道前件**——把指标解码成结构化语义，正是它 L2 层的输入；它的十项校验反向作为本技能的"数学化闸门"。

---

## 一、L2 语义 JSON（必标字段）

以下四组为**必标**，缺一即触发 **H2**：

| 组 | 字段 | 取值 |
|---|---|---|
| 领域结构 | `domain` | 微观 / 宏观 / 不确定 |
| | `macro_module` | 国民收入核算 / 增长 / 短期波动 / 通胀与失业 / 政策分析 / 政治经济学 / 发展经济学 / 金融证券 |
| 时间价格 | `time_frame` | 短期 / 长期 / 超长期 / 不确定 |
| | `stock_flow` | 存量 / 流量 / 两者 / 不确定 |
| | `nominal_real` | 名义 / 实际 / 两者 / 不确定 |
| 预期不确定 | `expectation` | 无 / 适应性 / 理性 / 不确定 |
| | `has_policy_shock` | true / false |
| 变量均衡 | `endogeneity_tendency` | 0.0–1.0（0 纯外生，1 纯内生） |
| | `mathable` | 可数学化 / 需降级 / 不可数学化 |

**可选扩展**（有则填）：`market_structure`、`agent_type`、`price_setting`、`has_equilibrium`、`has_elasticity`（须标方向）、`has_multiplier`（须分短长期）、`real_meaning`、`variables`、`math_tool_hint`。

**可追溯性**：每个字段附 `field_provenance.source`（`given` 用户给定 / `derived` 语义推导 / `clarified` 用户澄清 / `default` 缺省），缺省值必须显式标注，不得冒充给定。

## 二、十项校验（数学化闸门）

引入公式/模型前逐项过，任一不过 → 回溯修正或触发澄清，**不得带着量纲错误输出**：

1. 宏微观分类一致？
2. 外生 / 内生一致？
3. 时间框架一致（短 / 长 / 超长）？
4. 名义 / 实际一致？
5. 存量 / 流量一致？
6. **量纲一致**？（v1.0 政策影响函数即栽在此：时滞因子带时间量纲）
7. 比较静态符号合理？
8. 极端值下不荒谬？
9. 假设完整（含 ceteris paribus）？
10. 与语义字段矩阵一致？

**已修正的量纲范本**：政策影响

$$\Delta Y \;=\; S \times k \times \lambda(\tau)$$

其中 $S$ 为政策强度（无量纲打分或支出额）、$k$ 为传导系数、$\lambda(\tau)\in[0,1]$ 为**兑现率**（随兑现时滞 $\tau$ 递增）。不得写成"× 时滞（月）"，否则右侧带时间量纲而左侧不带。

## 三、四层降级

| `mathable` | 条件 | 处置 |
|---|---|---|
| 可数学化 | 四组必标齐全 + 十项校验通过 | 直接交 `econ-math-mapper` |
| 需降级 | 必标齐全但有 1–2 项校验存疑 | 标注存疑项，交 `econ-math-mapper` 时声明"需降级" |
| 不可数学化 | 必标缺失 ≥1 组，或涉及规范判断（公平、正义） | 停止数学化，退回语义层，只出解读卡 |
| 不确定 | 信号不足 | 走澄清模式补问 |

## 四、交接示例

```json
{
  "indicator": "社会融资规模存量同比",
  "value": {"actual": 9.6, "unit": "%", "period": "2026-08", "yoy_or_mom": "yoy"},
  "domain": "宏观",
  "macro_module": "短期波动",
  "time_frame": "短期",
  "stock_flow": "存量",
  "nominal_real": "名义",
  "expectation": "适应性",
  "has_policy_shock": true,
  "endogeneity_tendency": 0.7,
  "mathable": "可数学化",
  "field_provenance": {"stock_flow": "derived", "nominal_real": "given"},
  "handoff": {"to": "econ-math-mapper", "gate": "十项校验通过 10/10"}
}
```

## 五、与 econ-math-mapper 的分工红线

- 本技能**只产出语义与口径**，不判定用哪个模型、不做计量估计、不给比较静态结论。
- 对方**只做映射**，不重新解释指标口径（口径问题回流本技能）。
- 双方共用同一套字段词表，避免"存量/流量"等标签在两处含义漂移。
