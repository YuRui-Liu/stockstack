import type { ThemeConfig } from "antd";

export const adminTheme: ThemeConfig = {
  token: {
    colorPrimary: "#ff5000",
    colorInfo: "#ff5000",
    colorText: "#1d2129",
    colorTextSecondary: "#4e5969",
    colorBorder: "#dfe3e8",
    colorBorderSecondary: "#eaedf1",
    colorBgLayout: "#f4f6f8",
    borderRadius: 7,
    borderRadiusLG: 12,
    controlHeight: 40,
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  components: {
    Button: { fontWeight: 500, primaryShadow: "0 4px 10px rgba(255, 80, 0, 0.18)" },
    Card: { paddingLG: 24 },
    Form: { itemMarginBottom: 16 },
    Input: { activeShadow: "0 0 0 3px rgba(255, 80, 0, 0.10)" },
    Layout: { bodyBg: "#f4f6f8", headerBg: "#ffffff" },
    Table: { headerBg: "#f7f8fa", headerColor: "#4e5969", rowHoverBg: "#fff8f5" },
  },
};
