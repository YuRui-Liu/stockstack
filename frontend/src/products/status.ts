import type { ProductStatus } from "../api/types";

export interface StatusAction {
  target: ProductStatus;
  label: string;
  requiresConfirmation?: boolean;
}

export const statusLabels: Record<ProductStatus, string> = {
  on_shelf: "已上架",
  off_shelf: "已下架",
  penalized: "处罚中",
};

const transitionActions: Record<ProductStatus, readonly StatusAction[]> = {
  off_shelf: [
    { target: "on_shelf", label: "上架" },
    { target: "penalized", label: "设为处罚", requiresConfirmation: true },
  ],
  on_shelf: [
    { target: "off_shelf", label: "下架" },
    { target: "penalized", label: "设为处罚", requiresConfirmation: true },
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
