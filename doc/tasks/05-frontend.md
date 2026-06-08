# 05-frontend — 前端交互层

## 概述

实现前端画板、API 客户端、全局状态管理与 UI 渲染。可通过 Vite 代理或 Mock API 独立开发预览。

## 涉及文件

| 文件 | 说明 | 归属模块 |
|------|------|---------|
| `frontend/src/types.ts` | 类型定义 | 已在 01-core-contracts 完成 |
| `frontend/src/canvas.ts` | DrawingCanvas 类 | 本模块 |
| `frontend/src/api.ts` | API 调用封装 | 本模块 |
| `frontend/src/main.ts` | 入口 + 状态管理 + UI 事件 | 本模块 |

---

## 任务清单

### T5.1 canvas.ts — 画板模块

- [ ] `export class DrawingCanvas`
- [ ] `constructor(canvasElement: HTMLCanvasElement)`：
  - [ ] 设置 Canvas 尺寸 500×400（含 devicePixelRatio 适配）
  - [ ] 绑定 mousedown/mousemove/mouseup 事件
  - [ ] 初始化渲染上下文，填充白色背景
- [ ] `setTool(tool: Tool): void` → 切换 `pen`/`eraser`
- [ ] `clear(): void` → 清空画板并重新填充白色
- [ ] `exportBase64(): string` → `canvas.toDataURL("image/png")`
- [ ] 画笔模式：`strokeStyle="#000000"`, `lineWidth=3`, `lineCap="round"`
- [ ] 橡皮擦模式：`globalCompositeOperation="destination-out"`, `lineWidth=15`
- [ ] 鼠标事件：mousedown 开始路径，mousemove 绘制，mouseup 结束

### T5.2 api.ts — API 客户端

- [ ] `const BASE = "/api"`
- [ ] `async fetchTopic(): Promise<TopicResponse>`
- [ ] `async submitGuess(imageB64: string): Promise<GuessResponse>`
- [ ] `async sendFeedback(userSaysCorrect: boolean): Promise<FeedbackResponse>`
- [ ] `async getScore(): Promise<ScoreResponse>`
- [ ] 统一错误处理：非 2xx → `throw Error(await res.text())`
- [ ] POST 请求：`Content-Type: application/json`

### T5.3 main.ts — 应用入口

**状态管理**
- [ ] `let appState: AppState = AppState.DRAWING`
- [ ] `let currentScore: number = 0`
- [ ] `let canvas: DrawingCanvas`
- [ ] `let currentTool: Tool = "pen"`
- [ ] `setState(newState: AppState): void` → 按状态启用/禁用按钮

**初始化**
- [ ] `DOMContentLoaded` → 获取所有 DOM 引用
- [ ] 创建 `new DrawingCanvas(canvasEl)`
- [ ] 调用 `loadTopic()` 显示题目
- [ ] 绑定按钮事件

**关键函数**
- [ ] `loadTopic()`：调用 `fetchTopic()` → 显示 `"请画：{topic}"`
- [ ] `handleSubmit()`：状态 → GUESSING，导出 base64，`submitGuess()`，显示结果
- [ ] `handleFeedback(userSaysCorrect)`：`sendFeedback()`，更新分数，启用 [下一轮]
- [ ] `handleNextRound()`：`canvas.clear()`，`loadTopic()`，状态 → DRAWING

**UI 布局**（按 proposal §9）
- [ ] 题目区（顶部）：显示 topic + 分数
- [ ] Canvas 绘制区（中部）：500×400 固定画布
- [ ] 工具栏（中下部）：[清空] [橡皮擦] [提交猜画] [下一轮]
- [ ] 结果区（底部）：加载动画 / AI 结果 / ✅ ❌ 按钮

**异常处理**
- [ ] 网络错误 → 显示提示信息
- [ ] AI 超时（guess="timeout"）→ 显示"AI 推断超时"
- [ ] AI 异常（guess="error"）→ 显示"AI 服务异常"
- [ ] 空画板不阻止提交

---

## 验收标准

| 检查项 | 命令 | 阈值 |
|--------|------|------|
| TypeScript | `cd frontend && npx tsc --noEmit` | 0 errors |
| 构建 | `cd frontend && npx vite build` | 0 warnings |
| 预览验收 | `cd frontend && npx vite preview` | 人工确认 |

### 人工预览清单

- [ ] 页面加载后题目立即显示
- [ ] Canvas 可用鼠标拖拽绘制
- [ ] 画笔/橡皮擦切换正常
- [ ] 清空按钮重置画板
- [ ] 提交猜画后显示加载动画
- [ ] AI 结果正确展示
- [ ] ✅/❌ 按钮可点击，反馈后禁用
- [ ] 分数实时更新
- [ ] [下一轮] 清空画板 + 更换题目
- [ ] 响应式布局，居中显示

---

## 依赖

- `frontend/src/types.ts`（已由 01-core-contracts 完成）
- 后端 API（开发阶段可通过 Vite proxy 或 Mock 数据独立开发）
