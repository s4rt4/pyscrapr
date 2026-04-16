import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { setPageTitle, scrollToTop } from "../lib/utils";

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/harvester": "Image Harvester",
  "/mapper": "URL Mapper",
  "/ripper": "Site Ripper",
  "/media": "Media Downloader",
  "/ai": "AI Tools",
  "/playground": "Selector Playground",
  "/bypass": "Link Bypass",
  "/vault": "Auth Vault",
  "/scheduled": "Scheduled Jobs",
  "/diff": "Diff Detection",
  "/history": "History",
  "/settings": "Settings",
};

export function usePageMeta() {
  const { pathname } = useLocation();

  useEffect(() => {
    const title = PAGE_TITLES[pathname];
    setPageTitle(title);
    scrollToTop();
  }, [pathname]);
}
