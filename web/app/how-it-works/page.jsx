import { InfoPage } from "@/components/info/InfoPage";

export const metadata = {
  title: "How It Works",
  description: "How peer-to-peer auctions work on BidCa: bid, win, message the seller and exchange in person. BidCa never handles money.",
  alternates: { canonical: "/how-it-works" },
};

// Placeholder copy (Q014). Must stay accurate about the no-payment, peer-to-peer model (NFR-07).
const SECTIONS = [
  {
    heading: "BidCa connects buyers and sellers — it never handles money",
    body: [
      "BidCa is a local, peer-to-peer auction site for people who live in British Columbia. We list the items and run the auctions; the buyer and the seller finish the deal between themselves.",
      "There are no payments through BidCa. We never take, hold or refund money, and we offer no payment protection. You agree on how to pay when you meet.",
    ],
  },
  {
    heading: "1. Sign up",
    body: "Create an account with your email, phone number and BC city. You must be 19 or older. Verify your email and phone number — one account per phone number.",
  },
  {
    heading: "2. Bid or buy",
    body: "Bid on auctions or buy fixed-price items. Every listing is checked by our team before it goes live. Once an auction is open, its price cannot be changed or negotiated.",
  },
  {
    heading: "3. Win and arrange the exchange",
    body: "When you win, you and the seller are both told straight away and a transaction page opens with a private chat. Reply within 24 hours and agree on a time and a public place to meet.",
  },
  {
    heading: "4. Meet in person",
    body: "Inspect the item, pay the seller the way you agreed (for example cash or e-transfer) and take it home. Meet somewhere public and bring someone if you can.",
  },
  {
    heading: "5. Rate each other",
    body: "After the exchange, buyer and seller each leave one rating: a green thumb for a completed deal, yellow for a dispute and red when the deal was not completed. Ratings and comments are public and build trust.",
  },
  {
    heading: "If something goes wrong",
    body: "Either side can open a dispute from the transaction page. Our team reviews the conversation and can warn, suspend or ban accounts — but because BidCa never handles money, we cannot refund payments.",
  },
];

export default function HowItWorksPage() {
  return <InfoPage title="How It Works" intro="Local auctions, settled in person." sections={SECTIONS} />;
}
