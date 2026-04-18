import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

/** Format a date string as "2 minutes ago", "3 hours ago", etc. */
export function timeAgo(date: string | Date): string {
  return dayjs(date).fromNow();
}

/** Set document title with prefix */
export function setPageTitle(subtitle?: string) {
  document.title = subtitle ? `${subtitle} - PyScrapr` : "PyScrapr";
}

/** Scroll to top of page */
export function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "instant" });
}
