import { InfoPage } from "@/components/info/InfoPage";

export const metadata = {
  title: "Terms of Service",
  description: "The terms for using BidCa, a peer-to-peer auction site for British Columbia residents.",
  alternates: { canonical: "/terms" },
};

// Placeholder copy (Q014) — the BidCa team supplies the real Terms before launch.
const SECTIONS = [
  {
    heading: "Who can use BidCa",
    body: "You must be 19 or older and live in British Columbia. One account per person and per phone number.",
  },
  {
    heading: "BidCa is a venue, not a party to the sale",
    body: [
      "BidCa lists items and runs auctions. The contract of sale is between the buyer and the seller.",
      "BidCa never processes, holds or refunds payments and does not guarantee any item, payment or exchange.",
    ],
  },
  {
    heading: "Bids are binding",
    body: "A bid is a commitment to buy at that price if you win. Sellers cannot change the price once an auction is open. Sellers who cancel a listing that already has bids may be suspended.",
  },
  {
    heading: "Completing a deal",
    body: "The winner and the seller must respond within 24 hours and exchange the item in person. Not completing a deal can lead to a red rating and to account restrictions.",
  },
  {
    heading: "Listings and conduct",
    body: "Listings must be accurate, legal and allowed under our rules. We review every listing and may remove listings or suspend accounts that break these terms.",
  },
  {
    heading: "Disputes",
    body: "Disputes are reviewed by BidCa moderators, who may warn, suspend or ban accounts. Moderation never involves moving money.",
  },
  {
    heading: "Changes",
    body: "We may update these terms. Placeholder: effective date, governing law (British Columbia) and contact details to be added.",
  },
];

export default function TermsPage() {
  return <InfoPage title="Terms of Service" sections={SECTIONS} />;
}
