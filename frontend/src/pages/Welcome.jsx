import React from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/layout/Navbar";
import { useAuth } from "../App";
import {
  HandCoins,
  ChatCircleText,
  Handshake,
  ThumbsUp,
  Scales,
  Clock,
  ArrowRight,
} from "@phosphor-icons/react";

// FR-21: shown once, right after sign-up — how peer-to-peer auctions work on BidCa.
const RULES = [
  {
    Icon: HandCoins,
    title: "BidCa never handles money",
    text: "There are no payments through BidCa. We don't take, hold or refund money. You pay the seller directly when you meet.",
  },
  {
    Icon: Clock,
    title: "Reply within 24 hours",
    text: "When you win, you and the seller are both notified and a private chat opens. Answer within 24 hours — ignoring a deal you won gets a red rating.",
  },
  {
    Icon: Handshake,
    title: "Exchange in person",
    text: "Agree on a time and a public place, inspect the item, then pay the way you agreed (cash, e-transfer…). There is no shipping.",
  },
  {
    Icon: ThumbsUp,
    title: "Rate each other",
    text: "After the exchange each side leaves one rating: green for a completed deal, yellow for a dispute, red when the deal didn't happen. Ratings are public.",
  },
  {
    Icon: Scales,
    title: "Disputes",
    text: "If something goes wrong, open a dispute from the transaction page. Our team reviews it and can suspend or ban accounts — but cannot refund money.",
  },
  {
    Icon: ChatCircleText,
    title: "Bids are binding",
    text: "A bid is a promise to buy at that price if you win. Sellers can't change the price once an auction is open.",
  },
];

export default function Welcome() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />
      <div className="flex-1 px-4 py-12">
        <div className="max-w-2xl mx-auto bg-white border border-border p-8">
          <h1 className="font-heading text-2xl font-bold mb-2" data-testid="welcome-title">
            Welcome to BidCa{user?.display_name ? `, ${user.display_name}` : ""}
          </h1>
          <p className="text-muted-foreground mb-8">
            BidCa is a peer-to-peer auction site: we connect buyers and sellers in BC, and you finish the deal
            between yourselves. Here is how it works.
          </p>

          <ol className="space-y-6 mb-8">
            {RULES.map(({ Icon, title, text }) => (
              <li key={title} className="flex gap-4">
                <Icon className="h-8 w-8 text-primary flex-shrink-0" weight="duotone" />
                <div>
                  <h2 className="font-bold">{title}</h2>
                  <p className="text-sm text-muted-foreground">{text}</p>
                </div>
              </li>
            ))}
          </ol>

          <p className="text-sm text-muted-foreground mb-6">
            Read more in <a href="/how-it-works" className="text-primary underline">How It Works</a> and the{" "}
            <a href="/terms" className="text-primary underline">Terms of Service</a>.
          </p>

          <button
            type="button"
            onClick={() => navigate("/dashboard", { replace: true })}
            className="w-full py-3 bg-primary text-white font-bold hover:bg-primary/90 flex items-center justify-center gap-2"
            data-testid="welcome-continue"
          >
            I understand — continue
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
