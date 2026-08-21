import { PictureOutlined, UploadOutlined, CloseCircleFilled } from "@ant-design/icons";
import { Alert, Tooltip } from "antd";
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

  const removeImage = (url: string) => {
    onChange?.(value.filter((item) => item.url !== url));
  };

  const mainImages = value.filter((item) => item.kind === "main");
  const galleryImages = value.filter((item) => item.kind === "gallery");
  const galleryFull = galleryImages.length >= 5;

  return <div className="ss-upload-group">
    {/* ---------- 主图 ---------- */}
    <div className="ss-upload-field">
      <div className="ss-upload-field-label">
        <span className="ss-field-required">*</span>
        <span>商品主图</span>
        <Tooltip title="主图展示在列表和详情页，建议 800x800px 正方形，单张不超过 2 MiB">
          <span className="ss-upload-help">?</span>
        </Tooltip>
      </div>
      <div className="ss-upload-cards">
        {/* 已上传主图 */}
        {mainImages.map((image) => (
          <div key={image.url} className="ss-upload-card ss-upload-card--filled">
            <img src={image.url} alt="主图预览" className="ss-upload-card-img" />
            <button
              type="button"
              className="ss-upload-card-remove"
              onClick={() => removeImage(image.url)}
              aria-label="移除主图"
            >
              <CloseCircleFilled />
            </button>
          </div>
        ))}
        {/* 主图上传槽（没有主图时显示） */}
        {mainImages.length === 0 && (
          <label className={`ss-upload-card ss-upload-card--empty${uploading ? " ss-upload-card--disabled" : ""}`}>
            <input
              className="ss-upload-input"
              aria-label="主图"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={uploading}
              onChange={(event) => void handleFiles("main", Array.from(event.target.files ?? []))}
            />
            <PictureOutlined className="ss-upload-card-icon" />
            <span className="ss-upload-card-text">上传主图</span>
            <span className="ss-upload-card-hint">最大 2MB</span>
          </label>
        )}
      </div>
    </div>

    {/* ---------- 副图 ---------- */}
    <div className="ss-upload-field">
      <div className="ss-upload-field-label">
        <span>商品副图</span>
        <Tooltip title={`最多上传 5 张副图，每张不超过 2 MiB，用于展示商品多角度细节`}>
          <span className="ss-upload-help">?</span>
        </Tooltip>
      </div>
      <div className="ss-upload-cards">
        {/* 已上传副图 */}
        {galleryImages.map((image, index) => (
          <div key={image.url} className="ss-upload-card ss-upload-card--filled">
            <img src={image.url} alt={`副图预览 ${index + 1}`} className="ss-upload-card-img" />
            <button
              type="button"
              className="ss-upload-card-remove"
              onClick={() => removeImage(image.url)}
              aria-label={`移除副图 ${index + 1}`}
            >
              <CloseCircleFilled />
            </button>
          </div>
        ))}
        {/* 副图上传槽（最多 5 张） */}
        {!galleryFull && (
          <label className={`ss-upload-card ss-upload-card--empty${uploading ? " ss-upload-card--disabled" : ""}`}>
            <input
              className="ss-upload-input"
              aria-label="副图"
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              disabled={uploading}
              onChange={(event) => void handleFiles("gallery", Array.from(event.target.files ?? []))}
            />
            <UploadOutlined className="ss-upload-card-icon" />
            <span className="ss-upload-card-text">上传副图</span>
            <span className="ss-upload-card-hint">{galleryImages.length}/5</span>
          </label>
        )}
      </div>
    </div>

    {error && <Alert type="error" showIcon message={error} />}
  </div>;
}
