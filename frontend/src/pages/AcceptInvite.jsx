import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { API, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import { LockSimple } from "@phosphor-icons/react";

// /invite/:token — a private listing's invite link (FR-31). The route is login-protected, so a visitor
// signs in (or registers) first and lands back here; then we join the listing and open it.
export default function AcceptInvite() {
  const { token } = useParams();
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .post(`${API}/invites/${encodeURIComponent(token)}/accept`)
      .then(({ data }) => {
        // The listing page is served by the Next.js app: a full page load, not a router navigation
        window.location.replace(`/auctions/${data.listing_id}`);
      })
      .catch((e) => setError(formatApiErrorDetail(e.response?.data?.detail)));
  }, [token]);

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />
      <div className="flex-1 py-16">
        <div className="max-w-md mx-auto px-4 text-center bg-white border border-border p-8">
          <LockSimple className="h-10 w-10 text-primary mx-auto mb-3" />
          <h1 className="font-heading text-2xl font-bold mb-2">Private listing invite</h1>
          {error ? (
            <>
              <p className="text-destructive mb-4" role="alert">{error}</p>
              <a href="/" className="text-primary hover:underline">Back to BidCa</a>
            </>
          ) : (
            <p className="text-muted-foreground">Opening the listing…</p>
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
}
