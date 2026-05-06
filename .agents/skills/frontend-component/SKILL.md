---
name: frontend-component
version: "1.0"
description: 生成 React 19 + TypeScript 组件，含完整 vitest + Testing Library 测试和 Storybook story。与 frontend-design plugin 分工：本 skill 管测试和文档，frontend-design 管视觉质量。
allowed-tools:
  - Read
  - Write
  - Glob
---

# frontend-component

为 vid-maker 前端生成符合项目规范的 React 19 组件，包含测试和 Storybook。

## 触发条件

- 用户说"生成 XX 组件"
- 用户描述了组件的功能需求
- 需要为现有组件补充测试

## 分工说明

- **本 skill**：组件骨架 + vitest 测试 + Storybook story
- **frontend-design plugin**：视觉设计质量（色彩/排版/动效）
- **shadcn plugin**：shadcn/ui 组件安装和管理
- **web-design-guidelines plugin**：UI 规范审查

## 生成步骤

### Step 1：判断 Server vs Client Component

```
有交互（onClick/onChange/useState）→ Client Component（'use client'）
仅展示数据、无事件监听            → Server Component（不加 'use client'）
有异步数据获取                    → async Server Component + Suspense
```

### Step 2：组件结构

```tsx
// apps/web/src/components/SceneCard/SceneCard.tsx
'use client'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface SceneCardProps {
  scene: Scene
  onRegenerate: (sceneId: number) => void
  onDelete: (sceneId: number) => void
  className?: string
}

export function SceneCard({ scene, onRegenerate, onDelete, className }: SceneCardProps) {
  return (
    <article className={cn('rounded-lg border bg-card p-4', className)}>
      {/* 内联编辑：点击直接编辑，失焦保存 */}
    </article>
  )
}
```

### Step 3：vitest 测试

```tsx
// SceneCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SceneCard } from './SceneCard'

describe('SceneCard', () => {
  it('渲染旁白文本', () => { ... })
  it('点击重新生成按钮触发回调', () => { ... })
  it('点击删除按钮触发回调', () => { ... })
})
```

### Step 4：Storybook Story

```tsx
// SceneCard.stories.tsx
import type { Meta, StoryObj } from '@storybook/react'
import { SceneCard } from './SceneCard'

const meta: Meta<typeof SceneCard> = {
  title: 'vid-maker/SceneCard',
  component: SceneCard,
  tags: ['autodocs'],
}
export default meta

export const Default: StoryObj<typeof meta> = {
  args: { scene: mockScene, onRegenerate: () => {}, onDelete: () => {} }
}
```

## 关键约束

- ❌ 禁止在 Server Component 中使用 useState / useEffect
- ✅ 使用 shadcn/ui 基础组件，不自己写 Button/Dialog 等
- ✅ 使用 cn() 合并 className，支持外部样式覆盖
- ✅ 每个组件必须有对应测试文件
