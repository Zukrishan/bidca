import { Inbox } from "@/components/messages/Inbox";

export const metadata = {
  title: "Messages",
  robots: { index: false, follow: false },
};

export default function MessagesPage() {
  return <Inbox />;
}
