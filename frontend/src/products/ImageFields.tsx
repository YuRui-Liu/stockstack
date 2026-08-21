import { Alert, Space, Typography } from "antd";
import { useState } from "react";

import { ApiError, uploadImage } from "../api/client";
import type { ProductImageInput } from "../api/types";

const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const maxBytes = 2 * 1024 * 1024;

export default function ImageFields({ value = [], onChange }: { value?: ProductImageInput[]; onChange?: (value: ProductImageInput[]) => void }) {
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const handleFiles = async (kind: "main" | "gallery", files: File[]) => {
    setError("");
    if (kind === "main" && files.length !== 1) return setError("请选择一张主图");
    if (kind === "gallery" && files.length > 5) return setError("副图最多 5 张");
    const invalidType = files.find((file) => !allowedTypes.has(file.type));
    if (invalidType) return setError("仅支持 JPEG、PNG 或 WebP 图片");
    const oversized = files.find((file) => file.size > maxBytes);
    if (oversized) return setError("单张图片不能超过 2 MiB");
    try {
      setUploading(true);
      const uploaded = await Promise.all(files.map(uploadImage));
      const next = kind === "main" ? value.filter((item) => item.kind !== "main") : value.filter((item) => item.kind !== "gallery");
      onChange?.([...next, ...uploaded.map((item) => ({ ...item, kind }))]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.response.message : "图片上传失败，请重试");
    } finally {
      setUploading(false);
    }
  };

  return <Space direction="vertical" style={{ width: "100%" }}>
    <label>主图（必填）<input aria-label="主图" type="file" accept="image/jpeg,image/png,image/webp" disabled={uploading} onChange={(event) => void handleFiles("main", Array.from(event.target.files ?? []))} /></label>
    <label>副图（最多 5 张）<input aria-label="副图" type="file" multiple accept="image/jpeg,image/png,image/webp" disabled={uploading} onChange={(event) => void handleFiles("gallery", Array.from(event.target.files ?? []))} /></label>
    <Typography.Text type="secondary">已上传 {value.filter((item) => item.kind === "main").length} 张主图、{value.filter((item) => item.kind === "gallery").length} 张副图</Typography.Text>
    {error && <Alert type="error" showIcon message={error} />}
  </Space>;
}
