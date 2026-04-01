import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { API, formatCAD } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import {
  User,
  Star,
  ShieldCheck,
  MapPin,
  Calendar,
  Package,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Gavel
} from "@phosphor-icons/react";

export default function UserProfile() {
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [activeListings, setActiveListings] = useState([]);
  const [activeTab, setActiveTab] = useState("feedback");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
    fetchFeedback();
    fetchListings();
  }, [id]);

  const fetchProfile = async () => {
    try {
      const { data } = await axios.get(`${API}/users/${id}/profile`);
      setProfile(data);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFeedback = async () => {
    try {
      const { data } = await axios.get(`${API}/users/${id}/feedback`);
      setFeedback(data.feedback || []);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const fetchListings = async () => {
    try {
      const { data } = await axios.get(`${API}/listings?seller_id=${id}&status=active`);
      setActiveListings(data.listings || []);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground">User not found</p>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Profile Header */}
          <div className="bg-white border border-border p-6 mb-6">
            <div className="flex flex-col md:flex-row gap-6">
              <div className="flex items-center justify-center w-24 h-24 bg-secondary text-white font-heading font-bold text-3xl flex-shrink-0">
                {profile.full_name?.charAt(0) || 'U'}
              </div>
              
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="font-heading text-2xl font-bold">{profile.full_name}</h1>
                  {profile.verification_badge && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary text-white text-xs font-bold">
                      <ShieldCheck className="h-4 w-4" weight="fill" />
                      Verified
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mb-4">
                  <span className="flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {profile.city}, {profile.province}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    Member since {new Date(profile.member_since).toLocaleDateString()}
                  </span>
                  <span className="flex items-center gap-1">
                    <Package className="h-4 w-4" />
                    {profile.total_sales} sales
                  </span>
                </div>

                {/* Rating */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Star className="h-6 w-6 text-yellow-500" weight="fill" />
                    <span className="font-bold text-xl">{profile.seller_rating?.toFixed(1) || '5.0'}</span>
                  </div>
                  <div className="text-sm">
                    <span className="font-medium">{profile.total_ratings}</span>
                    <span className="text-muted-foreground"> ratings</span>
                  </div>
                  <div className="text-sm">
                    <span className="font-medium text-green-600">{profile.positive_percentage?.toFixed(0) || 100}%</span>
                    <span className="text-muted-foreground"> positive</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="bg-white border border-border mb-6">
            <div className="flex border-b border-border">
              <button
                onClick={() => setActiveTab("feedback")}
                className={`flex-1 px-4 py-3 text-sm font-medium ${
                  activeTab === "feedback"
                    ? "border-b-2 border-primary text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Feedback ({profile.total_ratings})
              </button>
              <button
                onClick={() => setActiveTab("listings")}
                className={`flex-1 px-4 py-3 text-sm font-medium ${
                  activeTab === "listings"
                    ? "border-b-2 border-primary text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Active Listings ({profile.active_listings})
              </button>
            </div>

            <div className="p-6">
              {activeTab === "feedback" ? (
                feedback.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No feedback yet</p>
                ) : (
                  <div className="space-y-4">
                    {feedback.map(f => (
                      <div key={f._id} className="border-b border-border pb-4 last:border-0 last:pb-0">
                        <div className="flex items-center gap-3 mb-2">
                          {f.rating === "positive" ? (
                            <ThumbsUp className="h-5 w-5 text-green-600" weight="fill" />
                          ) : f.rating === "negative" ? (
                            <ThumbsDown className="h-5 w-5 text-destructive" weight="fill" />
                          ) : (
                            <Minus className="h-5 w-5 text-muted-foreground" />
                          )}
                          <span className="font-medium">{f.from_user_name}</span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(f.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">{f.comment}</p>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                activeListings.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">No active listings</p>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {activeListings.map(listing => (
                      <Link
                        key={listing._id}
                        to={`/auctions/${listing._id}`}
                        className="border border-border overflow-hidden hover:shadow-md transition-all"
                      >
                        <div className="aspect-square bg-muted">
                          {listing.images?.[0] ? (
                            <img src={listing.images[0]} alt="" className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <Gavel className="h-8 w-8 text-muted-foreground" />
                            </div>
                          )}
                        </div>
                        <div className="p-3">
                          <h3 className="text-sm font-medium line-clamp-1">{listing.title}</h3>
                          <p className="font-bold">{formatCAD(listing.current_bid)}</p>
                        </div>
                      </Link>
                    ))}
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
