---
name: sse-progress-ui
version: "1.0"
description: vid-maker 专用：SSE 驱动的骨架屏→渐入动效模式，用于分镜生成进度展示。Marketplace 无此模式。
allowed-tools:
  - Read
  - Write
  - Glob
---

# sse-progress-ui

为 vid-maker 分镜生成页面（Step 3）实现 SSE 驱动的渐进式进度 UI。

## 触发条件

- 实现分镜生成进度展示
- 需要 SSE 驱动的实时更新 UI
- 需要骨架屏 → 实图的渐入动效

## 核心模式

### 骨架屏 → 实图渐入

```tsx
// apps/web/src/components/StoryboardGrid/SceneSlot.tsx
'use client'
import { cn } from '@/lib/utils'

interface SceneSlotProps {
  sceneId: number
  imageUrl?: string       // undefined = 骨架屏状态
  narration: string
  onRegenerate: (id: number) => void
  onUpload: (id: number, file: File) => void
}

export function SceneSlot({ sceneId, imageUrl, narration, onRegenerate, onUpload }: SceneSlotProps) {
  return (
    <div className="group relative aspect-video rounded-lg overflow-hidden border">
      {imageUrl ? (
        // ✅ 实图：渐入动效
        <img
          src={imageUrl}
          alt={`场景 ${sceneId}`}
          className="w-full h-full object-cover animate-in fade-in duration-500"
        />
      ) : (
        // ✅ 骨架屏：脉冲动画
        <div className="w-full h-full bg-muted animate-pulse flex items-center justify-center">
          <span className="text-muted-foreground text-sm">生成中...</span>
        </div>
      )}

      {/* 悬浮操作按钮（只在有图时显示）*/}
      {imageUrl && (
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100
                        transition-opacity flex items-center justify-center gap-2">
          <Button size="sm" variant="secondary" onClick={() => onRegenerate(sceneId)}>
            重新生成
          </Button>
          <label className="cursor-pointer">
            <Button size="sm" variant="secondary" asChild>
              <span>上传替换</span>
            </Button>
            <input type="file" accept="image/*" className="hidden"
              onChange={(e) => e.target.files?.[0] && onUpload(sceneId, e.target.files[0])} />
          </label>
        </div>
      )}

      <div className="absolute bottom-0 left-0 right-0 bg-black/60 p-2">
        <p className="text-white text-xs line-clamp-2">{narration}</p>
      </div>
    </div>
  )
}
```

### SSE Hook

```tsx
// apps/web/src/hooks/useStoryboardProgress.ts
'use client'
export function useStoryboardProgress(projectId: string, totalScenes: number) {
  const [completedScenes, setCompletedScenes] = useState<Map<number, string>>(new Map())
  const [isComplete, setIsComplete] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const es = new EventSource(`/api/projects/${projectId}/storyboard-progress`,
      { withCredentials: true })

    es.addEventListener('scene-done', (e) => {
      const { sceneId, imageUrl } = JSON.parse(e.data)
      setCompletedScenes(prev => new Map(prev).set(sceneId, imageUrl))
    })

    es.addEventListener('complete', () => {
      setIsComplete(true)
      es.close()
    })

    es.addEventListener('error', (e) => {
      setError('生成失败，请重试')
      es.close()
    })

    return () => es.close()
  }, [projectId])

  const progress = completedScenes.size / totalScenes
  return { completedScenes, isComplete, progress, error }
}
```

### 进度展示页面结构

```tsx
// apps/web/src/app/projects/[id]/step3/page.tsx
'use client'
export default function Step3Page({ params }: { params: { id: string } }) {
  const { completedScenes, isComplete, progress } = useStoryboardProgress(params.id, totalScenes)

  return (
    <div className="space-y-6">
      {/* 进度条 */}
      <div className="flex items-center gap-4">
        <Progress value={progress * 100} className="flex-1" />
        <span className="text-sm text-muted-foreground">
          {completedScenes.size}/{totalScenes} 已完成
        </span>
      </div>

      {/* 网格（提前渲染所有骨架屏）*/}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {scenes.map(scene => (
          <SceneSlot
            key={scene.id}
            sceneId={scene.id}
            imageUrl={completedScenes.get(scene.id)}
            narration={scene.narration}
            onRegenerate={handleRegenerate}
            onUpload={handleUpload}
          />
        ))}
      </div>

      {/* 底部操作（可提前确认）*/}
      <div className="flex justify-between">
        <Button variant="outline" onClick={() => router.push(`step2`)}>← 返回修改脚本</Button>
        <Button onClick={handleApprove} disabled={completedScenes.size === 0}>
          确认画面 → 开始生产视频
          <span className="ml-2 text-xs opacity-70">（可在生成完成前提前确认）</span>
        </Button>
      </div>
    </div>
  )
}
```

## 关键约束

- ✅ 骨架屏数量在页面加载时即确定（不等 SSE 才渲染网格）
- ✅ 用户可以在所有图生成完成前提前点"确认画面"
- ✅ SSE 连接在组件卸载时必须关闭（useEffect cleanup）
- ✅ 渐入动效使用 Tailwind `animate-in fade-in duration-500`，不引入额外动画库
