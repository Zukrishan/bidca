import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, API } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import {
  Tag,
  Clock,
  Plus,
  Gavel,
  CheckCircle,
  Warning,
  Eye,
  ArrowRight
} from "@phosphor-icons/react";

export default function SellerDashboard() {
  const { user } = useAuth();
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

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

  const filteredListings = listings.filter((l) => {
    if (filter === "all") return true;
    return l.status === filter;
  });

  const getStatusBadge = (status) => {
    const styles = {
      pending: "bg-yellow-500 text-white",
      active: "bg-green-600 text-white",
      ended: "bg-muted text-muted-foreground",
      unsold: "bg-muted text-muted-foreground",
      sold: "bg-secondary text-white",
      completed: "bg-secondary text-white",
      rejected: "bg-destructive text-white"
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
              <p className="text-sm text-muted-foreground mb-1">Sold</p>
              <p className="font-heading text-2xl font-bold">
                {listings.filter((l) => l.status === "sold").length}
              </p>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white border border-border mb-6">
            <div className="flex overflow-x-auto">
              {["all", "active", "pending", "sold", "unsold"].map((f) => (
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
                      <h3 className="font-medium truncate">{listing.title}</h3>
                      {getStatusBadge(listing.status)}
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      {listing.listing_type === "auction" ? "Auction" : "Marketplace"} • {listing.category}
                    </p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="font-bold">
                        ${listing.listing_type === "auction"
                          ? listing.current_bid?.toLocaleString()
                          : listing.fixed_price?.toLocaleString()}
                      </span>
                      {listing.listing_type === "auction" && (
                        <span className="text-muted-foreground">
                          {listing.bid_count || 0} bids
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/auctions/${listing._id}`}
                      className="p-2 border border-border hover:border-primary transition-colors"
                    >
                      <Eye className="h-5 w-5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}
