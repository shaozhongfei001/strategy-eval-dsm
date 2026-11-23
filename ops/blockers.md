# ops/blockers.md — 待签认 / 待补登记簿（ORCH §10.2）

> 规则：无人值守下遇到「需要人签认」或「文档/环境不一致」一律在此登记，写 PLACEHOLDER 后
> 用合成数据继续，**不停机、不拟定业务数值**。每条须写：缺什么 / 谁签认 / 完成条件 / 是否阻塞。

| 编号 | 类型 | 缺什么 | 谁签认 | 完成条件 | 阻塞? | 登记时间 |
|---|---|---|---|---|---|---|
| B-001 | 环境漂移 | 只读邻仓 /home/szf/dev/CampaignLab 的 tag R19-S14add 实测不存在（git tag -l 为 0 个、git show-ref 无该 ref），与 ops/dag-state.json 原描述不符 | 邻仓无人值守 DAG 的负责人 | 确认该 tag 是被 DAG 移动/删除还是从未创建；确认后回填 dag-state 的 
eadonly_neighbors 描述 | 否（§10.1-2 只比对 status --porcelain 与 HEAD，二者已快照：branch=m0-framework / HEAD=0cccb76 / porcelain 空 / rev-list=154） | 2026-11-23 |
| B-002 | 文档缺口 | docs/ORCHESTRATION-v1.0.md 正文无 §8.2「三级自续跑」（§8.1 之后直接进 §9），但 dag-state.json session_log seq=1 与启动提示词均引用「按 §8.2 选 T1/T2/T3」 | Orchestrator 规程维护者 | 补写 §8.2 的 T1/T2/T3 定义；在此之前，交接动作按提示词给出的语义执行：T1=直接进下一阶段；T2=运行时支持则自动开新会话续跑（本运行时**无** create_thread 工具，不可用）；T3=打印续跑提示词全文并把「现在从第 0 步开始」替换为「从 next_task = <task_id> 继续」 | 否（有明确 fallback 语义） | 2026-11-23 |

## K-01 ~ K-20 业务数值待行方签认

（尚未进入需要具体业务数值的任务。按 H-5，S1-T05/T06 起所有权重、门槛、红线阈值、目标值、
单价、周期、样本量与 K-01~K-20 一律写 PLACEHOLDER，并在此逐条登记。）

| 编号 | 含义（待 SDD 行号确认） | 当前处置 | 签认人 | 完成条件 |
|---|---|---|---|---|
| — | — | — | — | — |
