import type { ThemeConfig } from "antd";

export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: "#1677ff",
    colorText: "#1f2329",
    colorTextSecondary: "#5f6b7a",
    colorBorder: "#d9dfe8",
    colorBgLayout: "#f5f7fa",
    borderRadius: 6,
    borderRadiusLG: 8,
    controlHeight: 44,
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  components: {
    Button: { fontWeight: 600 },
    Card: { paddingLG: 32 },
    Form: { itemMarginBottom: 16 },
    Layout: { bodyBg: "#f5f7fa", headerBg: "#ffffff" },
  },
};
