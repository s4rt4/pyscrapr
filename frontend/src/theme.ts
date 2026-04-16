import { createTheme, MantineColorsTuple } from "@mantine/core";

const cyan: MantineColorsTuple = [
  "#e0fbff",
  "#cbf2ff",
  "#9ae4ff",
  "#66d6ff",
  "#3ccaff",
  "#21c3ff",
  "#00bfff",
  "#00a8e0",
  "#0095c9",
  "#0081b2",
];

export const theme = createTheme({
  primaryColor: "cyan",
  colors: { cyan },
  defaultRadius: "md",
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  headings: {
    fontFamily: '"Syne", -apple-system, sans-serif',
    fontWeight: "800",
  },
});
