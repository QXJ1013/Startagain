# ALS Assistant Frontend
todo:修复route bug，之前是用session传递。
     conversation history 显示bug
     改进dimension 跳转和维度打分bug（现在总会遍历所有问题库而不是只遍历同一个维度）
     性能提升：打分效果不佳，知识库数据不足信息卡质量一般
     
现代化的Vue 3 + TypeScript前端应用，为ALS/MND患者提供自我意识评估和个性化对话体验。

## 🚀 技术栈

- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **路由**: Vue Router 4
- **状态管理**: Pinia
- **UI组件**: 自定义组件 + Chart.js
- **样式**: 原生CSS + 响应式设计

## 📁 项目结构

```
src/
├── components/          # 可复用组件
│   ├── InfoCard.vue    # 信息卡片
│   ├── PNMScoreChart.vue # PNM评分图表
│   ├── ScoreRadar.vue  # 雷达图
│   └── Sidebar.vue     # 侧边栏导航
├── views/              # 页面组件
│   ├── Assessment.vue  # 评估页面（默认首页）
│   ├── Chat.vue        # 对话页面
│   ├── Data.vue        # 数据展示页面
│   └── Profile.vue     # 用户档案页面
├── services/           # API服务层
│   └── api.ts          # 后端API接口
├── stores/             # 状态管理
│   └── session.ts      # 会话状态
├── router/             # 路由配置
│   └── index.ts        # 路由定义
└── App.vue             # 根组件
```

## 🎯 核心功能

### 1. 智能评估系统 (Assessment.vue)
- **结构化问答流程**: 支持主问题和跟进问题
- **多种响应方式**: 选项按钮 + 自由文本输入
- **实时进度跟踪**: 显示评估完成度和当前水平
- **个性化信息卡片**: 基于回答内容提供相关建议
- **过渡消息**: 平滑的话题转换提示

### 2. 交互式对话 (Chat.vue)  
- **自然对话流**: 支持连续多轮对话
- **选项与文本混合**: 用户可选择预设选项或自由输入
- **信息卡片展示**: 实时提供相关健康信息
- **会话状态管理**: 保持对话上下文和历史
- **跳过机制**: 允许跳过不适用的问题

### 3. 数据可视化 (Data.vue)
- **八维度评分**: 可视化展示PNM八个维度的得分
- **交互式图表**: 悬停显示详细信息和操作按钮
- **最近完成术语**: 显示评估历史和进度
- **个性化建议**: 基于当前评分提供下一步行动建议
- **维度聚焦**: 点击维度可直接开始该领域的对话

### 4. 用户档案管理 (Profile.vue)
- **评估档案**: 完整的PNM评分历史
- **详细评分**: 四个子维度（意识、理解、应对、行动）
- **建议系统**: 基于评分水平的改进建议
- **会话统计**: 对话轮次和评估覆盖度

## 🔌 API集成

### 后端接口对接
```typescript
// 主要API端点
api.getNextQuestion(sessionId, userResponse?)    // 获取下一个问题
api.getPNMProfile(sessionId)                     // 获取PNM评分档案
api.health()                                     // 健康检查
```

### 数据流架构
```
Frontend ↔ API Service ↔ Backend Routes ↔ Business Logic ↔ Database
   ↓           ↓              ↓                ↓             ↓
Vue组件   → api.ts    → FastAPI路由  → 对话管理器   → SQLite
状态管理  → HTTP请求   → JSON响应    → 评分引擎    → 会话持久化
```

## 🚀 开发和部署

### 开发环境
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

### 环境配置
```bash
# 开发环境
VITE_API_BASE=http://localhost:8000

# 生产环境  
VITE_API_BASE=https://your-api-domain.com
```

## 📊 功能验证

### 集成测试覆盖
✅ 后端健康检查  
✅ 对话启动和流程管理  
✅ 用户响应处理  
✅ PNM评分系统  
✅ 会话状态持久化  
✅ 信息卡片生成  
✅ 多维度评分可视化  

---

**系统状态**: ✅ 生产就绪  
**最后更新**: 2025年8月25日
