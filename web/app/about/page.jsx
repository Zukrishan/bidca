import { InfoPage } from "@/components/info/InfoPage";

export const metadata = {
  title: "About Us",
  description: "Who is behind BidCa, the local auction site for British Columbia.",
  alternates: { canonical: "/about" },
};

// Placeholder copy (Q014) — the BidCa team writes the real About text before launch.
const SECTIONS = [
  {
    heading: "Local auctions for British Columbia",
    body: "BidCa is a place for people in BC to buy and sell with their neighbours — by auction or at a fixed price — and meet in person to finish the deal.",
  },
  {
    heading: "Who we are",
    body: "Placeholder: the team behind BidCa, where we are based and why we built it.",
  },
  {
    heading: "How we keep it safe",
    body: "Every listing is reviewed, accounts are tied to a verified phone number, and public ratings show who completes their deals. BidCa never handles money; buyers and sellers pay each other in person.",
  },
  {
    heading: "Contact",
    body: "Placeholder: contact details to be added.",
  },
];

export default function AboutPage() {
  return <InfoPage title="About Us" sections={SECTIONS} />;
}
