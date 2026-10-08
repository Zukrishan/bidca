import { Thread } from "@/components/messages/Thread";

export const metadata = {
  title: "Message",
  robots: { index: false, follow: false },
};

export default async function ThreadPage({ params }) {
  const { transactionId } = await params;
  return <Thread transactionId={transactionId} />;
}
