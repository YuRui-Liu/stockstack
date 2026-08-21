import type { ProductStatus } from "../api/types";

export interface StatusAction {
  target: ProductStatus;
  label: string;
  requiresConfirmation?: boolean;
  /** 行内操作按钮的视觉分组，用于套用设计稿配色 */
  tone?: "on" | "off" | "danger";
}

export const statusLabels: Record<ProductStatus, string> = {
  on_shelf: "已上架",
  off_shelf: "已下架",
  penalized: "处罚中",
};

/** 状态标签的样式类，取自设计稿的三种 Tag 配色 */
export const statusTagClassNames: Record<ProductStatus, string> = {
  on_shelf: "ss-tag ss-tag-on-shelf",
  off_shelf: "ss-tag ss-tag-off-shelf",
  penalized: "ss-tag ss-tag-penalized",
};

const transitionActions: Record<ProductStatus, readonly StatusAction[]> = {
  off_shelf: [
    { target: "on_shelf", label: "上架", tone: "on" },
    { target: "penalized", label: "设为处罚", requiresConfirmation: true, tone: "danger" },
  ],
  on_shelf: [
    { target: "off_shelf", label: "下架", tone: "off" },
    { target: "penalized", label: "设为处罚", requiresConfirmation: true, tone: "danger" },
  ],
  penalized: [],
};

export const batchStatusActions = [
  { target: "on_shelf" as const, label: "批量上架" },
  { target: "off_shelf" as const, label: "批量下架" },
];

export function canTransition(source: ProductStatus, target: ProductStatus): boolean {
  return transitionActions[source].some((action) => action.target === target);
}

export function actionsForStatus(status: ProductStatus): readonly StatusAction[] {
  return transitionActions[status];
}
