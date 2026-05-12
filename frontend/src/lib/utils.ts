import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

/** Format a date string as "2 minutes ago", "3 hours ago", etc.
 *
 * Backend stores timestamps as naive UTC (no 'Z' suffix). Browsers
 * interpret naive ISO strings as local time, which would offset by the
 * timezone (e.g. WIB = UTC+7 -> 7 hour gap). Force UTC parse for
 * string inputs that don't already specify timezone.
 */
export function timeAgo(date: string | Date): string {
  if (typeof date === "string" && !date.endsWith("Z") && !/[+-]\d\d:?\d\d$/.test(date)) {
    return dayjs.utc(date).fromNow();
  }
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
