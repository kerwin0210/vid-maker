# Marketplace Plugins 安装说明

以下 3 个 Cursor Marketplace Plugin 需在 Cursor IDE 中手动安装（一次性操作）。

## 安装方式

在 Cursor 聊天框输入对应命令，或访问 cursor.com/marketplace 搜索安装：

---

## 1. shadcn/ui（官方）

```
/add-plugin shadcn
```

- **作者**：shadcn 官方
- **用途**：管理 shadcn/ui 组件——添加、搜索、修复、调试、样式、组合
- **触发条件**：工作涉及 shadcn/ui 组件、components.json、component registry 时自动激活
- **文档**：[https://cursor.com/marketplace/skills/shadcn](https://cursor.com/marketplace/skills/shadcn)

---

## 2. frontend-design（Cursor 认证）

```
/add-plugin frontend-design
```

- **作者**：Every（Cursor 官方认证）
- **用途**：构建高质量 Web UI——排版、色彩、动效、文案，截图验证完成效果
- **触发条件**：构建 landing page、web app、dashboard、admin panel、组件时激活
- **文档**：[https://cursor.com/marketplace/skills/frontend-design](https://cursor.com/marketplace/skills/frontend-design)

---

## 3. web-design-guidelines（Vercel Labs）

```
/add-plugin web-design-guidelines
```

- **作者**：Vercel Labs
- **安装量**：64,200+
- **用途**：审查 UI 代码是否符合 Web 界面规范——交互、动效、布局、表单、性能、可访问性、移动端适配
- **文档**：[https://cursor.com/marketplace/skills/web-design-guidelines](https://cursor.com/marketplace/skills/web-design-guidelines)

---

## 安装后验证

在 Cursor 中输入：

```
@shadcn 帮我添加一个 Button 组件
```

如果 shadcn plugin 正确安装，Agent 会自动读取 components.json 并执行安装。