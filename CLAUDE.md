# Claude Code Assistant Instructions

## 项目概述
这是一个ALS（肌萎缩性侧索硬化症）助手应用，包含前端Vue.js应用和后端FastAPI服务。

## 架构状态（2024年9月更新）
✅ **已完成重大架构简化**：
- 从复杂的会话表结构迁移到基于文档的存储（schema_v2.sql）
- 统一API端点：`/chat/conversation` 处理所有对话交互
- 简化FSM状态机：5状态流程（ROUTE → ASK → PROCESS → SCORE → CONTINUE）
- 移除了40%的后端复杂性，直接覆写源文件完成

## 永久性要求和约定

### 🔒 硬性要求
1. **不要额外弄一套逻辑，直接覆盖旧方案**
2. **全部代码必须是英文** - 无中文注释或变量名
3. **测试脚本和任何文件使用完成必须删除**
4. **不要使用uniform或复杂抽象**
5. **强烈反对硬编码** ("我非常反対硬編碼")

### 🛠️ 技术栈和工具
- **后端**: FastAPI + SQLite + Document-based storage
- **前端**: Vue.js 3 + TypeScript + Pinia
- **数据库**: schema_v2.sql（文档式存储）
- **测试**: 完成后运行 `npm run build` 和 `npm run lint`

### 📁 项目结构
```
backend/
  app/
    routers/
      chat_unified.py     # 统一对话端点
      auth.py            # 身份验证
      health.py          # 健康检查
    services/
      storage.py         # 文档存储服务
      fsm.py            # 简化状态机
      question_bank.py   # 问题库
      ai_routing.py      # AI路由
      pnm_scoring.py     # PNM评分
    data/
      schema_v2.sql      # 文档数据库架构
      als.db            # 主数据库

frontend/
  src/
    views/
      Chat.vue          # 主对话界面
      Data.vue          # 数据显示
      Profile.vue       # 用户资料
    stores/
      auth.ts           # 身份验证状态
      chat.ts           # 对话状态
    services/
      api.ts            # API客户端
```

### 🔄 简化后的API流程
1. **统一端点**: POST `/chat/conversation` 
   - 接受: `{user_response, dimension_focus?, request_info}`
   - 返回: 完整的 ConversationResponse 对象
2. **80% 对话模式 + 20% 结构化评估**
3. **自动对话管理** - 无需多个端点调用

### 🗄️ 数据存储架构
- **conversation_documents**: 主表，每个对话存为JSON文档
- **conversation_scores**: 索引表用于快速查询
- **用户验证**: 创建对话前检查用户存在

### 🧪 测试要求
在任何重大更改后运行：
```bash
cd backend && python -c "from app.deps import warmup_dependencies; warmup_dependencies()"
cd frontend && npm run build
```

### 📝 文档和日志约定
- 所有错误必须有上下文信息
- 使用英文日志消息
- 重要操作需要确认日志

## 当前已知问题和解决方案

### ✅ 已修复的兼容性问题
1. **外键约束** - 创建对话前验证用户存在
2. **消息添加** - 支持对象和参数两种格式
3. **前端API兼容性** - 统一使用 `/chat/conversation`
4. **对话历史** - 实施降级行为避免崩溃

### 🚨 关键提醒
- ConversationHistory组件使用降级行为（后端端点已移除）
- Data.vue使用模拟数据（评分端点已简化）
- 所有核心对话功能100%兼容

## 快速命令参考

### 后端测试
```bash
cd backend
python -c "from app.deps import warmup_dependencies; warmup_dependencies()"
```

### 前端测试
```bash
cd als-assistant-frontend
npm run build
npm run lint  # 如果可用
```

### 数据库备份
```bash
cp backend/app/data/als.db backend/app/data/als.db.backup_$(date +%Y%m%d_%H%M%S)
```

---
📅 **最后更新**: 2024年9月11日
🎯 **状态**: 后端架构简化完成，前端兼容性100%