import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { setPageTitle, scrollToTop } from "../lib/utils";

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/harvester": "Image Harvester",
  "/mapper": "URL Mapper",
  "/ripper": "Site Ripper",
  "/media": "Media Downloader",
  "/ai": "AI Tagger",
  "/ai-extract": "AI Extract",
  "/pipeline": "Custom Pipeline",
  "/playground": "Selector Playground",
  "/bypass": "Link Bypass",
  "/tech": "Tech Fingerprinter",
  "/screenshot": "Screenshotter",
  "/seo": "SEO Auditor",
  "/broken-links": "Broken Link Checker",
  "/security": "Security Headers",
  "/ssl": "SSL Inspector",
  "/intel": "Domain Intel",
  "/wayback": "Wayback Explorer",
  "/sitemap": "Sitemap Analyzer",
  "/vault": "Auth Vault",
  "/scheduled": "Scheduled Jobs",
  "/diff": "Diff Detection",
  "/history": "History",
  "/settings": "Settings",
  "/docs": "Documentation",
};

export function usePageMeta() {
  const { pathname } = useLocation();

  useEffect(() => {
    const title = PAGE_TITLES[pathname];
    setPageTitle(title);
    scrollToTop();
  }, [pathname]);
}
