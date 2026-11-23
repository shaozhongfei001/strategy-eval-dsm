# strategy-eval-dsm

策略评价「可辩护评分」模型（DSM = Defensible Scoring Model）的离线批量实现。

## 这是什么

读入本期各策略的指标事实与评价设计卡，输出每条策略的综合得分、四级等级、应执行动作，
以及「这个结论有多稳、能不能用于淘汰」的检验报告。

- 形态：单机命令行批处理，**不需要数据库、不需要联网、不接生产库**
- 频率：评分每期一次（月/季），权重构造每年一次
- 输入：8 张表（CSV）；输出：5 张表 + report.md + audit.json

## 设计基线

开发设计文档（唯一权威）：

    D:\ws\codex_rd\ss_campaignlab\工行参考文件\开发设计文档-策略评价可辩护评分模型DSM-v1.1.md

核心口径：**入分的只有三件事 —— 目标达成率、加权聚合、红线否决。**
AHP 造权重（CR 检验）、熵权与 AHP 按 α 组合后冻结入配置、TOPSIS/GRA 做三角验证并拥有否决权。
四种教科书方法一个都没浪费，但没有一个被允许直接决定一条策略的生死。

## 环境

    python3 -m venv ~/venvs/dsm
    ~/venvs/dsm/bin/pip install -r requirements.txt
    ~/venvs/dsm/bin/python -m pytest

依赖版本见 requirements.txt（已实测锁定）。境内网络请配置 pip 镜像（见 pip.conf 示例）。

## 目录

    dsm/          模型代码（分层 L0a/L0b/L1-L7，见设计文档 §1.6）
    config/       治理配置（全部 PLACEHOLDER，须行方签认后才能出正式结论）
    fixtures/     合成数据与 golden 期望值（不含任何真实客户信息）
    tests/        单元测试 / golden G-01~G-15 / 属性 P-1~P-15 / 方法学 T-*
    tools/        开发辅助脚本（normalize 等）
    reports/      运行产物（gitignore，按 period/run_id 分层）

## 纪律

- 金额与整数**精确相等**；比率与均值 **1e-12** 容差（唯一实现点 dsm/numeric.py）
- 任何业务数值未签认 → 配置加载直接失败，**不出分**（PLACEHOLDER 拦截）
- 任何降级都必须留 reason_code 与披露位置，**禁止静默处理**
- 不使用任何真实客户数据
