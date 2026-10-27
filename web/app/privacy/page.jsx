import { InfoPage } from "@/components/info/InfoPage";

export const metadata = {
  title: "Privacy Policy",
  description: "What BidCa collects, what other members can see, and how to delete your account.",
  alternates: { canonical: "/privacy" },
};

// Placeholder copy (Q014) — the BidCa team supplies the real Privacy Policy before launch.
const SECTIONS = [
  {
    heading: "What we collect",
    body: "Your email, full name, phone number, BC city and postal code, your confirmation that you are 19 or older, an optional profile picture, and your listings, bids, messages and ratings.",
  },
  {
    heading: "What other members see",
    body: "Your display name (not your full name), profile picture, city, member-since date, completed deals, ratings and comments, active listings and preferred exchange method. Your email, phone number, postal code, saved items and bid history stay private.",
  },
  {
    heading: "No payment data",
    body: "BidCa never handles payments, so we never collect card or bank details.",
  },
  {
    heading: "Service providers",
    body: "Placeholder: email delivery, SMS verification codes, CAPTCHA, image hosting and hosting providers to be listed here.",
  },
  {
    heading: "Deleting your account",
    body: "You can delete your account in Account settings once you have no open transactions or listings with bids. We remove your personal details; records of completed transactions and ratings are kept, without your name.",
  },
  {
    heading: "Contact",
    body: "Placeholder: privacy contact details to be added.",
  },
];

export default function PrivacyPage() {
  return <InfoPage title="Privacy Policy" sections={SECTIONS} />;
}
