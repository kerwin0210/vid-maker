---
name: saas-billing-ui
version: "1.0"
description: vid-maker SaaS 专用：积分余额展示、成本警告弹窗、积分不足引导、升级套餐 UI 组件模式。
allowed-tools:
  - Read
  - Write
  - Glob
---

# saas-billing-ui

为 vid-maker SaaS 生成计费相关 UI 组件。

## 触发条件

- 实现积分余额展示
- 需要成本警告弹窗
- 需要积分不足提示和充值引导
- 实现套餐升级页面

## 核心组件模式

### 1. 积分余额展示（导航栏）

```tsx
// apps/web/src/components/CreditBalance/CreditBalance.tsx
'use client'
export function CreditBalance() {
  const { data: balance } = useSWR('/api/user/credits', fetcher, {
    refreshInterval: 30000  // 每 30s 刷新
  })

  const isLow = balance !== undefined && balance < 20  // 低于 20 积分预警

  return (
    <div className={cn(
      'flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium',
      isLow ? 'bg-orange-100 text-orange-700' : 'bg-muted text-muted-foreground'
    )}>
      <Coins className="h-3.5 w-3.5" />
      <span>{balance ?? '—'} 积分</span>
      {isLow && (
        <Link href="/billing" className="ml-1 underline text-orange-600 text-xs">充值</Link>
      )}
    </div>
  )
}
```

### 2. 生成前成本确认弹窗

```tsx
// apps/web/src/components/CostConfirmDialog/CostConfirmDialog.tsx
const COST_WARN_THRESHOLD = 50  // ¥50 以上必须弹窗确认

interface CostConfirmDialogProps {
  estimatedCostCny: number
  creditBalance: number
  onConfirm: () => void
  onCancel: () => void
}

export function CostConfirmDialog({ estimatedCostCny, creditBalance, onConfirm, onCancel }: CostConfirmDialogProps) {
  const hasEnoughCredits = creditBalance >= estimatedCostCny
  const isHighCost = estimatedCostCny > COST_WARN_THRESHOLD

  return (
    <Dialog open>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isHighCost ? '⚠️ 生成成本提醒' : '确认开始生成'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 py-4">
          <div className="flex justify-between text-sm">
            <span>预估成本</span>
            <span className={cn('font-medium', isHighCost && 'text-orange-600')}>
              {estimatedCostCny} 积分（约 ¥{estimatedCostCny}）
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span>当前余额</span>
            <span className={cn('font-medium', !hasEnoughCredits && 'text-red-600')}>
              {creditBalance} 积分
            </span>
          </div>

          {!hasEnoughCredits && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              积分不足，还需 {estimatedCostCny - creditBalance} 积分。
              <Link href="/billing" className="ml-1 font-medium underline">立即充值 →</Link>
            </div>
          )}

          {isHighCost && hasEnoughCredits && (
            <p className="text-sm text-muted-foreground">
              5 分钟视频生成成本较高，确认后将从余额中扣除。生成失败会全额退还。
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>取消</Button>
          <Button onClick={onConfirm} disabled={!hasEnoughCredits}>
            确认生成
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

### 3. 积分充值页面组件

```tsx
// apps/web/src/app/billing/page.tsx 核心组件
const CREDIT_PACKAGES = [
  { credits: 50,  price: 49,  label: '基础包', popular: false },
  { credits: 150, price: 129, label: '标准包', popular: true,  badge: '最划算' },
  { credits: 350, price: 279, label: '专业包', popular: false },
]

const SUBSCRIPTION_PLANS = [
  { name: '免费版', monthlyCredits: 10, price: 0,   features: ['每月 10 积分', '30s 视频', '16:9 比例'] },
  { name: '基础版', monthlyCredits: 60, price: 99,  features: ['每月 60 积分', '全规格视频', '优先队列'] },
  { name: '专业版', monthlyCredits: 200, price: 299, features: ['每月 200 积分', '全规格视频', '最高优先级', '专属客服'] },
]
```

## 关键约束

- ✅ 积分不足时禁用生成按钮，明确引导充值
- ✅ 超过 ¥50 估算成本时必须弹确认弹窗（不可跳过）
- ✅ 支付成功后实时刷新积分余额
- ✅ 生成失败的退积分要在 UI 上有明确提示
- ❌ 禁止在前端计算最终积分扣除（以后端返回为准）
