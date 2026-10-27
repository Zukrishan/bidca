import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth, API, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import { toast } from "sonner";
import {
  Tag,
  Clock,
  Plus,
  Gavel,
  CheckCircle,
  Warning,
  Eye,
  ArrowRight,
  PencilSimple,
  PaperPlaneTilt,
  XCircle,
  LockSimple,
  UserPlus,
  Copy
} from "@phosphor-icons/react";

// Cancel / withdraw with a confirmation step that states any penalty (FR-29, Q012)
function CancelDialog({ listing, onClose, onDone }) {
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios
      .get(`${API}/listings/${listing._id}/cancel-preview`)
      .then(({ data }) => setPreview(data))
      .catch((e) => {
        toast.error(formatApiErrorDetail(e.response?.data?.detail));
        onClose();
      });
  }, [listing._id, onClose]);

  const confirm = async () => {
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/listings/${listing._id}/cancel`, {
        confirm_penalty: preview?.outcome === "cancel_with_penalty"
      });
      toast.success(data.outcome === "withdraw" ? "Listing withdrawn" : "Listing cancelled");
      onDone();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
      setBusy(false);
    }
  };

  const withPenalty = preview?.outcome === "cancel_with_penalty";
  const verb = preview?.outcome === "withdraw" ? "Withdraw" : "Cancel";
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="cancel-title">
      <div className="bg-white border border-border max-w-md w-full p-6">
        <h2 id="cancel-title" className="font-heading text-xl font-bold mb-2">{verb} “{listing.title}”?</h2>
        {!preview ? (
          <p className="text-muted-foreground">Checking…</p>
        ) : (
          <p className={withPenalty ? "text-destructive font-medium" : "text-muted-foreground"} data-testid="cancel-penalty">
            {preview.message}
          </p>
        )}
        <div className="flex gap-3 mt-6">
          <button type="button" onClick={onClose} className="flex-1 py-2 border border-border font-medium">
            Keep listing
          </button>
          <button
            type="button"
            onClick={confirm}
            disabled={!preview || busy || preview.outcome === "not_allowed"}
            className="flex-1 py-2 bg-destructive text-white font-bold disabled:opacity-50"
            data-testid="confirm-cancel-btn"
          >
            {withPenalty ? "Cancel and accept suspension" : `${verb} listing`}
          </button>
        </div>
      </div>
    </div>
  );
}

// Invite management for a private listing (FR-31): add by email/phone, remove, share or reset the link
function InvitesDialog({ listing, onClose }) {
  const [data, setData] = useState(null);
  const [identifier, setIdentifier] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios
      .get(`${API}/listings/${listing._id}/invites`)
      .then(({ data }) => setData(data))
      .catch((e) => toast.error(formatApiErrorDetail(e.response?.data?.detail)));
  }, [listing._id]);

  const act = async (fn) => {
    setBusy(true);
    try {
      const { data } = await fn();
      setData(data);
      return true;
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const add = async (e) => {
    e.preventDefault();
    if (!identifier.trim()) return;
    if (await act(() => axios.post(`${API}/listings/${listing._id}/invites`, { identifier: identifier.trim() }))) {
      setIdentifier("");
    }
  };

  const link = data?.invite_token ? `${window.location.origin}/invite/${data.invite_token}` : "";
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      toast.success("Invite link copied");
    } catch {
      toast.error("Couldn't copy — select the link and copy it");
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="invites-title">
      <div className="bg-white border border-border max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 id="invites-title" className="font-heading text-xl font-bold mb-1">Invites — {listing.title}</h2>
        <p className="text-sm text-muted-foreground mb-4">Only these people can see and bid on this listing.</p>

        <form onSubmit={add} className="flex gap-2 mb-4">
          <input
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="BidCa email or phone number"
            aria-label="Email or phone number to invite"
            className="flex-1 px-3 py-2 border border-input focus:border-primary outline-none"
            data-testid="invite-identifier"
          />
          <button type="submit" disabled={busy} className="px-4 py-2 bg-primary text-white font-medium inline-flex items-center gap-1 disabled:opacity-50">
            <UserPlus className="h-4 w-4" /> Invite
          </button>
        </form>

        {!data ? (
          <p className="text-muted-foreground">Loading…</p>
        ) : (
          <>
            {data.invitees.length === 0 ? (
              <p className="text-sm text-muted-foreground mb-4">No one invited yet.</p>
            ) : (
              <ul className="divide-y divide-border border border-border mb-4">
                {data.invitees.map((p) => (
                  <li key={p.user_id} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
                    <span>
                      {p.full_name || "BidCa member"}
                      {p.email ? <span className="text-muted-foreground"> · {p.email}</span> : null}
                    </span>
                    <button
                      type="button"
                      onClick={() => act(() => axios.delete(`${API}/listings/${listing._id}/invites/${p.user_id}`))}
                      className="text-destructive hover:underline"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <p className="text-sm font-medium mb-1">Private invite link</p>
            <p className="text-xs text-muted-foreground mb-2">
              Send it by text or WhatsApp. People need a BidCa account to bid; the link stops working when the listing ends.
            </p>
            <div className="flex gap-2">
              <input
                readOnly
                value={link}
                aria-label="Invite link"
                className="flex-1 px-3 py-2 border border-input text-sm bg-muted"
                onFocus={(e) => e.target.select()}
              />
              <button type="button" onClick={copy} className="px-3 py-2 border border-border inline-flex items-center gap-1 text-sm">
                <Copy className="h-4 w-4" /> Copy
              </button>
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={() => act(() => axios.post(`${API}/listings/${listing._id}/invite-link`))}
              className="mt-2 text-sm text-primary hover:underline"
            >
              Make a new link (the old one stops working)
            </button>
          </>
        )}

        <button type="button" onClick={onClose} className="w-full mt-6 py-2 border border-border font-medium">
          Done
        </button>
      </div>
    </div>
  );
}

export default function SellerDashboard() {
  const { user } = useAuth();
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [cancelling, setCancelling] = useState(null);
  const [inviting, setInviting] = useState(null);
  const closeCancel = useCallback(() => setCancelling(null), []);

  useEffect(() => {
    fetchListings();
  }, []);

  const fetchListings = async () => {
    try {
      const { data } = await axios.get(`${API}/users/me/listings`);
      setListings(data.listings || []);
    } catch (error) {
      console.error("Error fetching listings:", error);
    } finally {
      setLoading(false);
    }
  };

  const submitDraft = async (listing) => {
    try {
      await axios.post(`${API}/listings/${listing._id}/submit`);
      toast.success("Submitted for admin review");
      fetchListings();
    } catch (e) {
      toast.error(formatApiErrorDetail(e.response?.data?.detail));
    }
  };

  const filteredListings = listings.filter((l) => {
    if (filter === "all") return true;
    return l.status === filter;
  });

  const getStatusBadge = (status) => {
    const styles = {
      pending: "bg-yellow-500 text-white",
      active: "bg-green-600 text-white",
      ended: "bg-muted text-muted-foreground",
      completed: "bg-secondary text-white",
      rejected: "bg-destructive text-white",
      draft: "bg-muted text-foreground border border-border",
      cancelled: "bg-muted text-muted-foreground"
    };
    return (
      <span className={`px-2 py-1 text-xs font-bold uppercase ${styles[status] || styles.pending}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            <div>
              <h1 className="font-heading text-3xl font-bold" data-testid="seller-dashboard-title">
                Seller Dashboard
              </h1>
              <p className="text-muted-foreground mt-1">
                Manage your listings and track sales
              </p>
            </div>
            <Link
              to="/create-listing"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
              data-testid="new-listing-btn"
            >
              <Plus className="h-5 w-5" />
              New Listing
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white border border-border p-4">
              <p className="text-sm text-muted-foreground mb-1">Total Listings</p>
              <p className="font-heading text-2xl font-bold">{listings.length}</p>
            </div>
            <div className="bg-white border border-border p-4">
              <p className="text-sm text-muted-foreground mb-1">Active</p>
              <p className="font-heading text-2xl font-bold text-green-600">
                {listings.filter((l) => l.status === "active").length}
              </p>
            </div>
            <div className="bg-white border border-border p-4">
              <p className="text-sm text-muted-foreground mb-1">Pending Review</p>
              <p className="font-heading text-2xl font-bold text-yellow-600">
                {listings.filter((l) => l.status === "pending").length}
              </p>
            </div>
            <div className="bg-white border border-border p-4">
              <p className="text-sm text-muted-foreground mb-1">Completed</p>
              <p className="font-heading text-2xl font-bold">
                {listings.filter((l) => l.status === "completed").length}
              </p>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white border border-border mb-6">
            <div className="flex overflow-x-auto">
              {["all", "draft", "active", "pending", "ended", "completed", "cancelled"].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`flex-shrink-0 px-6 py-3 text-sm font-medium transition-colors ${
                    filter === f
                      ? "border-b-2 border-primary text-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  data-testid={`filter-${f}`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Listings */}
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-muted animate-pulse h-24" />
              ))}
            </div>
          ) : filteredListings.length === 0 ? (
            <div className="text-center py-16 bg-white border border-border">
              <Tag className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h2 className="font-heading text-xl font-bold mb-2">No listings found</h2>
              <p className="text-muted-foreground mb-4">
                {filter === "all"
                  ? "You haven't created any listings yet."
                  : `No ${filter} listings.`}
              </p>
              <Link
                to="/create-listing"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
              >
                Create Your First Listing
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredListings.map((listing) => (
                <div
                  key={listing._id}
                  className="bg-white border border-border p-4 flex flex-col sm:flex-row sm:items-center gap-4"
                  data-testid={`listing-${listing._id}`}
                >
                  {/* Image */}
                  <div className="w-full sm:w-24 h-24 bg-muted flex-shrink-0">
                    {listing.images?.[0] ? (
                      <img
                        src={listing.images[0]}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Gavel className="h-8 w-8 text-muted-foreground" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-medium truncate">{listing.title || "Untitled draft"}</h3>
                      {getStatusBadge(listing.status)}
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      {listing.listing_type === "private" ? (
                        <span className="inline-flex items-center gap-1"><LockSimple className="h-3 w-3" /> Private auction</span>
                      ) : listing.listing_type === "fixed_price" ? "Marketplace" : "Auction"}
                      {listing.category ? ` • ${listing.category}` : ""}
                    </p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="font-bold">
                        ${listing.listing_type === "fixed_price"
                          ? listing.buy_it_now_price?.toLocaleString()
                          : listing.current_bid?.toLocaleString()}
                      </span>
                      {listing.listing_type !== "fixed_price" && (
                        <span className="text-muted-foreground">
                          {listing.bid_count || 0} bids
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-wrap items-center gap-2">
                    {listing.status === "draft" && (
                      <>
                        <Link
                          to={`/create-listing?draft=${listing._id}`}
                          className="inline-flex items-center gap-1 px-3 py-2 border border-border hover:border-primary text-sm"
                          data-testid={`edit-draft-${listing._id}`}
                        >
                          <PencilSimple className="h-4 w-4" /> Edit
                        </Link>
                        <button
                          type="button"
                          onClick={() => submitDraft(listing)}
                          className="inline-flex items-center gap-1 px-3 py-2 bg-primary text-white text-sm"
                        >
                          <PaperPlaneTilt className="h-4 w-4" /> Submit
                        </button>
                      </>
                    )}
                    {listing.listing_type === "private" && ["draft", "pending", "active"].includes(listing.status) && (
                      <button
                        type="button"
                        onClick={() => setInviting(listing)}
                        className="inline-flex items-center gap-1 px-3 py-2 border border-border hover:border-primary text-sm"
                        data-testid={`invites-${listing._id}`}
                      >
                        <UserPlus className="h-4 w-4" /> Invites
                      </button>
                    )}
                    {["draft", "pending", "active"].includes(listing.status) && (
                      <button
                        type="button"
                        onClick={() => setCancelling(listing)}
                        className="inline-flex items-center gap-1 px-3 py-2 border border-border hover:border-destructive text-destructive text-sm"
                        data-testid={`cancel-${listing._id}`}
                      >
                        <XCircle className="h-4 w-4" /> {listing.status === "active" ? "Cancel" : "Withdraw"}
                      </button>
                    )}
                    {/* The listing page is served by the Next.js app: a plain link, not a router Link */}
                    <a
                      href={`/auctions/${listing._id}`}
                      aria-label="View listing"
                      className="p-2 border border-border hover:border-primary transition-colors"
                    >
                      <Eye className="h-5 w-5" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {cancelling && (
        <CancelDialog
          listing={cancelling}
          onClose={closeCancel}
          onDone={() => {
            setCancelling(null);
            fetchListings();
          }}
        />
      )}
      {inviting && <InvitesDialog listing={inviting} onClose={() => setInviting(null)} />}

      <Footer />
    </div>
  );
}
