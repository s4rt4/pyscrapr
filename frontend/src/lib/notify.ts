import { notifications } from "@mantine/notifications";
import { playDoneBeep, playErrorBeep } from "./sound";

export function notifyDone(message: string) {
  playDoneBeep();
  notifications.show({ title: "Done", message, color: "green" });
}

export function notifyError(message: string) {
  playErrorBeep();
  notifications.show({ title: "Error", message, color: "red" });
}
