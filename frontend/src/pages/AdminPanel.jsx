import React, { useState, useEffect } from "react";
import { useAuth, API, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import axios from "axios";
import { toast } from "sonner";
import {
  Gear,
  Users,
  Tag,
  ShieldCheck,
  Flag,
  ChartBar,
  CheckCircle,
  X,
  Eye,
  Warning,
  Trash,
  UserCircle
} from "@phosphor-icons/react";

export default function AdminPanel() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [stats, setStats] = useState(null);
  const [listings, setListings] = useState([]);
  const [users, setUsers] = useState([]);
  const [verifications, setVerifications] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listingFilter, setListingFilter] = useState("pending");

  useEffect(() => {
    fetchData();
  }, [activeTab, listingFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === "dashboard") {
        const { data } = await axios.get(`${API}/admin/stats`);
        setStats(data);
      } else if (activeTab === "listings") {
        const { data } = await axios.get(`${API}/admin/listings?status=${listingFilter}`);
        setListings(data.listings || []);
      } else if (activeTab === "users") {
        const { data } = await axios.get(`${API}/admin/users`);
        setUsers(data.users || []);
      } else if (activeTab === "verifications") {
        const { data } = await axios.get(`${API}/admin/verifications`);
        setVerifications(data.verifications || []);
      } else if (activeTab === "reports") {
        const { data } = await axios.get(`${API}/admin/reports`);
        setReports(data.reports || []);
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Failed to fetch data");
    } finally {
      setLoading(false);
    }
  };

  const handleListingAction = async (listingId, status) => {
    try {
      await axios.put(`${API}/admin/listings/${listingId}`, { status });
      toast.success(`Listing ${status}`);
      fetchData();
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    }
  };

  const handleDeleteListing = async (listingId) => {
    if (!window.confirm("Are you sure you want to delete this listing?")) return;
    try {
      await axios.delete(`${API}/admin/listings/${listingId}`);
      toast.success("Listing deleted");
      fetchData();
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    }
  };

  const handleUserAction = async (userId, action) => {
    try {
      const update = {};
      if (action === "suspend") update.is_suspended = true;
      if (action === "unsuspend") update.is_suspended = false;
      if (action === "ban") update.is_banned = true;
      if (action === "unban") update.is_banned = false;
      
      await axios.put(`${API}/admin/users/${userId}`, update);
      toast.success(`User ${action}ed`);
      fetchData();
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    }
  };

  const handleVerificationAction = async (verificationId, status) => {
    try {
      await axios.put(`${API}/admin/verifications/${verificationId}?status=${status}`);
      toast.success(`Verification ${status}`);
      fetchData();
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    }
  };

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: ChartBar },
    { id: "listings", label: "Listings", icon: Tag },
    { id: "users", label: "Users", icon: Users },
    { id: "verifications", label: "Verifications", icon: ShieldCheck },
    { id: "reports", label: "Reports", icon: Flag },
  ];

  return (
    <div className="min-h-screen bg-muted">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Gear className="h-8 w-8 text-primary" />
          <h1 className="font-heading text-3xl font-bold" data-testid="admin-title">
            Admin Panel
          </h1>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar */}
          <div className="lg:w-64 flex-shrink-0">
            <div className="bg-white border border-border">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                    activeTab === tab.id
                      ? "bg-primary/10 text-primary border-l-4 border-primary"
                      : "hover:bg-muted"
                  }`}
                  data-testid={`tab-${tab.id}`}
                >
                  <tab.icon className="h-5 w-5" />
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <>
                {/* Dashboard */}
                {activeTab === "dashboard" && stats && (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="bg-white border border-border p-6">
                      <p className="text-sm text-muted-foreground mb-1">Total Users</p>
                      <p className="font-heading text-3xl font-bold">{stats.total_users}</p>
                    </div>
                    <div className="bg-white border border-border p-6">
                      <p className="text-sm text-muted-foreground mb-1">Total Listings</p>
                      <p className="font-heading text-3xl font-bold">{stats.total_listings}</p>
                    </div>
                    <div className="bg-white border border-border p-6">
                      <p className="text-sm text-muted-foreground mb-1">Active Auctions</p>
                      <p className="font-heading text-3xl font-bold text-green-600">{stats.active_auctions}</p>
                    </div>
                    <div className="bg-white border border-border p-6">
                      <p className="text-sm text-muted-foreground mb-1">Pending Listings</p>
                      <p className="font-heading text-3xl font-bold text-yellow-600">{stats.pending_listings}</p>
                    </div>
                    <div className="bg-white border border-border p-6">
                      <p className="text-sm text-muted-foreground mb-1">Pending Verifications</p>
                      <p className="font-heading text-3xl font-bold text-yellow-600">{stats.pending_verifications}</p>
                    </div>
                    <div className="bg-white border border-border p-6">
                      <p className="text-sm text-muted-foreground mb-1">Total Bids</p>
                      <p className="font-heading text-3xl font-bold">{stats.total_bids}</p>
                    </div>
                  </div>
                )}

                {/* Listings */}
                {activeTab === "listings" && (
                  <div className="bg-white border border-border">
                    <div className="flex border-b border-border">
                      {["pending", "active", "ended", "rejected"].map((status) => (
                        <button
                          key={status}
                          onClick={() => setListingFilter(status)}
                          className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                            listingFilter === status
                              ? "border-b-2 border-primary text-primary"
                              : "text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          {status.charAt(0).toUpperCase() + status.slice(1)}
                        </button>
                      ))}
                    </div>

                    <div className="divide-y divide-border">
                      {listings.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                          No {listingFilter} listings
                        </div>
                      ) : (
                        listings.map((listing) => (
                          <div key={listing._id} className="p-4 flex items-center gap-4">
                            <div className="w-16 h-16 bg-muted flex-shrink-0">
                              {listing.images?.[0] ? (
                                <img src={listing.images[0]} alt="" className="w-full h-full object-cover" />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                  <Tag className="h-6 w-6 text-muted-foreground" />
                                </div>
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <h3 className="font-medium truncate">{listing.title}</h3>
                              <p className="text-sm text-muted-foreground">
                                {listing.seller_name} • {listing.city}
                              </p>
                              <p className="text-sm font-bold">${listing.current_bid?.toLocaleString()}</p>
                            </div>
                            <div className="flex gap-2">
                              {listingFilter === "pending" && (
                                <>
                                  <button
                                    onClick={() => handleListingAction(listing._id, "active")}
                                    className="p-2 bg-green-600 text-white hover:bg-green-700 transition-colors"
                                    title="Approve"
                                  >
                                    <CheckCircle className="h-5 w-5" />
                                  </button>
                                  <button
                                    onClick={() => handleListingAction(listing._id, "rejected")}
                                    className="p-2 bg-destructive text-white hover:bg-destructive/90 transition-colors"
                                    title="Reject"
                                  >
                                    <X className="h-5 w-5" />
                                  </button>
                                </>
                              )}
                              <button
                                onClick={() => handleDeleteListing(listing._id)}
                                className="p-2 border border-border hover:border-destructive hover:text-destructive transition-colors"
                                title="Delete"
                              >
                                <Trash className="h-5 w-5" />
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* Users */}
                {activeTab === "users" && (
                  <div className="bg-white border border-border">
                    <div className="divide-y divide-border">
                      {users.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                          No users found
                        </div>
                      ) : (
                        users.map((u) => (
                          <div key={u._id} className="p-4 flex items-center gap-4">
                            <div className="w-12 h-12 bg-secondary text-white flex items-center justify-center font-bold flex-shrink-0">
                              {u.full_name?.charAt(0) || "U"}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <h3 className="font-medium">{u.full_name}</h3>
                                {u.role === "admin" && (
                                  <span className="px-2 py-0.5 bg-primary text-white text-xs font-bold">
                                    Admin
                                  </span>
                                )}
                                {u.verification_badge && (
                                  <ShieldCheck className="h-4 w-4 text-primary" weight="fill" />
                                )}
                                {u.is_suspended && (
                                  <span className="px-2 py-0.5 bg-yellow-500 text-white text-xs font-bold">
                                    Suspended
                                  </span>
                                )}
                                {u.is_banned && (
                                  <span className="px-2 py-0.5 bg-destructive text-white text-xs font-bold">
                                    Banned
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground">{u.email}</p>
                              <p className="text-sm text-muted-foreground">{u.city}</p>
                            </div>
                            {u.role !== "admin" && (
                              <div className="flex gap-2">
                                {u.is_suspended ? (
                                  <button
                                    onClick={() => handleUserAction(u._id, "unsuspend")}
                                    className="px-3 py-1 bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
                                  >
                                    Unsuspend
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleUserAction(u._id, "suspend")}
                                    className="px-3 py-1 bg-yellow-500 text-white text-sm font-medium hover:bg-yellow-600 transition-colors"
                                  >
                                    Suspend
                                  </button>
                                )}
                                {u.is_banned ? (
                                  <button
                                    onClick={() => handleUserAction(u._id, "unban")}
                                    className="px-3 py-1 bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
                                  >
                                    Unban
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleUserAction(u._id, "ban")}
                                    className="px-3 py-1 bg-destructive text-white text-sm font-medium hover:bg-destructive/90 transition-colors"
                                  >
                                    Ban
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* Verifications */}
                {activeTab === "verifications" && (
                  <div className="bg-white border border-border">
                    <div className="divide-y divide-border">
                      {verifications.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                          No pending verifications
                        </div>
                      ) : (
                        verifications.map((v) => (
                          <div key={v._id} className="p-4">
                            <div className="flex items-center gap-4 mb-4">
                              <UserCircle className="h-10 w-10 text-muted-foreground" />
                              <div>
                                <h3 className="font-medium">{v.user_name}</h3>
                                <p className="text-sm text-muted-foreground">{v.user_email}</p>
                              </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4 mb-4">
                              <div>
                                <p className="text-sm font-medium mb-2">Government ID</p>
                                <img
                                  src={v.government_id_url}
                                  alt="ID"
                                  className="w-full h-32 object-cover border border-border"
                                />
                              </div>
                              <div>
                                <p className="text-sm font-medium mb-2">Selfie</p>
                                <img
                                  src={v.selfie_url}
                                  alt="Selfie"
                                  className="w-full h-32 object-cover border border-border"
                                />
                              </div>
                            </div>
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleVerificationAction(v._id, "approved")}
                                className="flex-1 py-2 bg-green-600 text-white font-medium hover:bg-green-700 transition-colors"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => handleVerificationAction(v._id, "rejected")}
                                className="flex-1 py-2 bg-destructive text-white font-medium hover:bg-destructive/90 transition-colors"
                              >
                                Reject
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* Reports */}
                {activeTab === "reports" && (
                  <div className="bg-white border border-border">
                    <div className="divide-y divide-border">
                      {reports.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground">
                          No pending reports
                        </div>
                      ) : (
                        reports.map((r) => (
                          <div key={r._id} className="p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <Warning className="h-5 w-5 text-yellow-600" />
                              <span className="font-medium">{r.listing_title}</span>
                            </div>
                            <p className="text-sm text-muted-foreground mb-1">
                              Reason: <span className="text-foreground">{r.reason}</span>
                            </p>
                            <p className="text-sm text-muted-foreground mb-2">
                              {r.description}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Reported by: {r.reporter_email}
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
