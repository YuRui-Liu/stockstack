import type { ThemeConfig } from "antd";

// 设计令牌来自参考设计稿（主色 #326BFB、圆角 6/8/12、浅灰底 #F5F6F9）
export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: "#326bfb",
    colorInfo: "#326bfb",
    colorSuccess: "#01b15c",
    colorWarning: "#ffa800",
    colorError: "#fe3421",
    colorText: "#2c2e30",
    colorTextSecondary: "#90949e",
    colorTextPlaceholder: "#cdd2db",
    colorBorder: "#dfe4ec",
    colorBorderSecondary: "#eef1f6",
    colorBgLayout: "#f5f6f9",
    colorBgContainer: "#ffffff",
    borderRadius: 6,
    borderRadiusLG: 8,
    borderRadiusSM: 4,
    controlHeight: 32,
    fontSize: 14,
    fontFamily: "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Button: { fontWeight: 500, controlHeight: 32, controlHeightLG: 36, paddingInline: 16 },
    Card: { paddingLG: 24, borderRadiusLG: 12 },
    Form: { itemMarginBottom: 20, labelColor: "#2c2e30" },
    Input: { controlHeight: 32, paddingInline: 12 },
    InputNumber: { controlHeight: 32 },
    Select: { controlHeight: 32 },
    Table: { headerBg: "#f5f6f9", headerColor: "#2c2e30", borderColor: "#eef1f6", rowHoverBg: "#fafbfc", cellPaddingBlock: 12 },
    Layout: { bodyBg: "#f5f6f9", headerBg: "#ffffff", headerHeight: 56, headerPadding: "0 24px" },
    Modal: { borderRadiusLG: 12 },
    Descriptions: { labelBg: "#fafbfc" },
    Tooltip: { colorBgSpotlight: "#2c2e30" },
  },
};
