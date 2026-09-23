# Workbench Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** 收敛重复行情版本，统一全站视觉并保持所有研究操作可用。
**Architecture:** 数据呈现选择器负责去重及推荐，原始版本高级展开；后端仅复用相同输入的不可变研究快照；CSS重整为统一规范，不引入前端框架。
**Tech Stack:** 原生HTML/CSS/JS、Python现有数据服务。

- [x] 后端tests：重复研究准备返回同一输入版本，不同价格/区间返回新版本，原始文件不变；实现快照复用。
- [x] 前端tests：证券默认一行，历史折叠、重复去重、不同复权版本不拼接，操作仍引用准确来源；重整data-management/timeline。
- [x] 重整HTML结构与CSS；教程默认折叠，字体层级、网格、表格、表单、图表、响应式及focus样式一致。
- [x] 检查主/子导航隔离及键盘行为，必要处先补失败测试再修复。
- [x] 浏览器逐页桌面/移动截图；回测、历史、实验、数据、时间轴关键交互验收；适当测试、文档与提交。
