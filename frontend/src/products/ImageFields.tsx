import { Alert } from "antd";
import { useRef, useState } from "react";

import { ApiError, uploadImage } from "../api/client";
import type { ProductImageInput } from "../api/types";

const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const maxBytes = 2 * 1024 * 1024;

export default function ImageFields({ value = [], onChange, onUploadingChange }: { value?: ProductImageInput[]; onChange?: (value: ProductImageInput[]) => void; onUploadingChange?: (uploading: boolean) => void }) {
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const uploads = useRef(0);

  const handleFiles = async (kind: "main" | "gallery", files: File[]) => {
    setError("");
    if (kind === "main" && files.length !== 1) return setError("请选择一张主图");
    if (kind === "gallery" && files.length > 5) return setError("副图最多 5 张");
    const invalidType = files.find((file) => !allowedTypes.has(file.type));
    if (invalidType) return setError("仅支持 JPEG、PNG 或 WebP 图片");
    const oversized = files.find((file) => file.size > maxBytes);
    if (oversized) return setError("单张图片不能超过 2 MiB");
    try {
      uploads.current += 1;
      setUploading(true);
      onUploadingChange?.(true);
      const uploaded = await Promise.all(files.map(uploadImage));
      const next = kind === "main" ? value.filter((item) => item.kind !== "main") : value.filter((item) => item.kind !== "gallery");
      onChange?.([...next, ...uploaded.map((item) => ({ ...item, kind }))]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.response.message : "图片上传失败，请重试");
    } finally {
      uploads.current -= 1;
      if (uploads.current === 0) {
        setUploading(false);
        onUploadingChange?.(false);
      }
    }
  };

  const mainImages = value.filter((item) => item.kind === "main");
  const galleryImages = value.filter((item) => item.kind === "gallery");

  return <div className="ss-upload-group">
    <div className="ss-upload-field">
      <label className="ss-upload-label">
        <span className="ss-field-required">*</span>商品主图
        <input
          className="ss-upload-input"
          aria-label="主图"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={uploading}
          onChange={(event) => void handleFiles("main", Array.from(event.target.files ?? []))}
        />
      </label>
      <span className="ss-upload-hint">主图展示在列表和详情页，建议 800x800px 正方形，单张不超过 2 MiB</span>
      {mainImages.length > 0 && (
        <div className="ss-upload-preview">
          {mainImages.map((image) => <img key={image.url} src={image.url} alt="主图预览" />)}
        </div>
      )}
    </div>

    <div className="ss-upload-field">
      <label className="ss-upload-label">
        商品副图
        <input
          className="ss-upload-input"
          aria-label="副图"
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp"
          disabled={uploading}
          onChange={(event) => void handleFiles("gallery", Array.from(event.target.files ?? []))}
        />
      </label>
      <span className="ss-upload-hint">最多上传 5 张副图，每张不超过 2 MiB，用于展示商品多角度细节</span>
      {galleryImages.length > 0 && (
        <div className="ss-upload-preview">
          {galleryImages.map((image, index) => <img key={image.url} src={image.url} alt={`副图预览 ${index + 1}`} />)}
        </div>
      )}
    </div>

    <span className="ss-upload-hint">已上传 {mainImages.length} 张主图、{galleryImages.length} 张副图</span>
    {error && <Alert type="error" showIcon message={error} />}
  </div>;
}
