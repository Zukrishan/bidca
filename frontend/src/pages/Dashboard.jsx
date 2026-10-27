import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, API } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import {
  User,
  ShieldCheck,
  Gavel,
  Tag,
  Bell,
  Plus,
  MapPin,
  CheckCircle,
  Warning,
  ArrowRight
} from "@phosphor-icons/react";

// Countdown Timer
function CountdownTimer({ endTime }) {
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft());

  function calculateTimeLeft() {
    const difference = new Date(endTime) - new Date();
    if (difference <= 0) return { ended: true };
    return {
      days: Math.floor(difference / (1000 * 60 * 60 * 24)),
      hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
      minutes: Math.floor((difference / 1000 / 60) % 60),
      seconds: Math.floor((difference / 1000) % 60),
      ended: false
    };
  }

  useEffect(() => {
    const timer = setInterval(() => setTimeLeft(calculateTimeLeft()), 1000);
    return () => clearInterval(timer);
  }, [endTime]);

  if (timeLeft.ended) return <span className="text-muted-foreground">Ended</span>;

  return (
    <span className="font-mono tabular-nums">
      {timeLeft.days > 0 && `${timeLeft.days}d `}
      {String(timeLeft.hours).padStart(2, '0')}:
      {String(timeLeft.minutes).padStart(2, '0')}:
      {String(timeLeft.seconds).padStart(2, '0')}
    </span>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("bids");
  const [bids, setBids] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [bidsRes, notifRes] = await Promise.all([
        axios.get(`${API}/users/me/bids`),
        axios.get(`${API}/notifications`)
      ]);
      setBids(bidsRes.data.bids || []);
      setNotifications(notifRes.data.notifications || []);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  const markNotificationRead = async (id) => {
    try {
      await axios.put(`${API}/notifications/${id}/read`);
      setNotifications(notifications.map(n => n._id === id ? { ...n, read: true } : n));
    } catch (error) {
      console.error("Error marking notification read:", error);
    }
  };

  const markAllRead = async () => {
    try {
      await axios.put(`${API}/notifications/read-all`);
      setNotifications(notifications.map(n => ({ ...n, read: true })));
    } catch (error) {
      console.error("Error marking all read:", error);
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Profile Header */}
          <div className="bg-white border border-border p-6 mb-6" data-testid="profile-header">
            <div className="flex flex-col sm:flex-row sm:items-center gap-6">
              <div className="flex items-center justify-center w-20 h-20 bg-secondary text-white font-heading font-bold text-2xl">
                {(user?.display_name || user?.full_name)?.charAt(0) || "U"}
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="font-heading text-2xl font-bold">{user?.display_name || user?.full_name}</h1>
                  {/* Phone verification is the only trust mark users see (Q009) */}
                  {user?.phone_verified ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-secondary text-white text-xs font-bold">
                      <ShieldCheck className="h-4 w-4" weight="fill" />
                      Phone verified
                    </span>
                  ) : (
                    <Link to="/account" className="inline-flex items-center gap-1 px-2 py-1 bg-muted text-muted-foreground text-xs font-bold hover:underline">
                      Phone not verified
                    </Link>
                  )}
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <MapPin className="h-4 w-4" />
                    {user?.city}
                  </span>
                  <span>{user?.email}</span>
                </div>
              </div>

              <div className="flex gap-3">
                <Link
                  to="/create-listing"
                  className="px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors flex items-center gap-2"
                  data-testid="create-listing-btn"
                >
                  <Plus className="h-5 w-5" />
                  Sell Item
                </Link>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="bg-white border border-border mb-6">
            <div className="flex border-b border-border">
              <button
                onClick={() => setActiveTab("bids")}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                  activeTab === "bids"
                    ? "border-b-2 border-primary text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                data-testid="tab-bids"
              >
                <Gavel className="h-5 w-5 inline mr-2" />
                My Bids
              </button>
              <button
                onClick={() => setActiveTab("notifications")}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors relative ${
                  activeTab === "notifications"
                    ? "border-b-2 border-primary text-primary"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                data-testid="tab-notifications"
              >
                <Bell className="h-5 w-5 inline mr-2" />
                Notifications
                {unreadCount > 0 && (
                  <span className="absolute top-2 ml-1 w-5 h-5 bg-primary text-white text-xs rounded-full flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>
            </div>

            <div className="p-6">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : activeTab === "bids" ? (
                <div>
                  {bids.length === 0 ? (
                    <div className="text-center py-12">
                      <Gavel className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground mb-4">You haven't placed any bids yet.</p>
                      <Link
                        to="/auctions"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
                      >
                        Browse Auctions
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {bids.map((bid) => (
                        <Link
                          key={bid.bid_id}
                          to={`/auctions/${bid.listing_id}`}
                          className="flex items-center gap-4 p-4 border border-border hover:border-primary transition-colors"
                          data-testid={`bid-item-${bid.bid_id}`}
                        >
                          <div className="w-16 h-16 bg-muted flex-shrink-0">
                            {bid.listing_image ? (
                              <img src={bid.listing_image} alt="" className="w-full h-full object-cover" />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center">
                                <Gavel className="h-6 w-6 text-muted-foreground" />
                              </div>
                            )}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium truncate">{bid.listing_title}</h3>
                            <p className="text-sm text-muted-foreground">
                              Your bid: <span className="font-bold text-foreground">${bid.amount?.toLocaleString()}</span>
                            </p>
                          </div>

                          <div className="text-right flex-shrink-0">
                            {bid.is_winning ? (
                              <span className="inline-flex items-center gap-1 text-sm text-green-600 font-medium">
                                <CheckCircle className="h-4 w-4" />
                                Winning
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
                                <Warning className="h-4 w-4" />
                                Outbid
                              </span>
                            )}
                            <p className="text-xs text-muted-foreground mt-1">
                              {bid.status === "active" ? (
                                <CountdownTimer endTime={bid.end_time} />
                              ) : (
                                <span className="capitalize">{bid.status}</span>
                              )}
                            </p>
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  {notifications.length > 0 && (
                    <div className="flex justify-end mb-4">
                      <button
                        onClick={markAllRead}
                        className="text-sm text-primary hover:underline"
                        data-testid="mark-all-read-btn"
                      >
                        Mark all as read
                      </button>
                    </div>
                  )}
                  {notifications.length === 0 ? (
                    <div className="text-center py-12">
                      <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">No notifications yet.</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {notifications.map((notif) => (
                        <div
                          key={notif._id}
                          onClick={() => !notif.read && markNotificationRead(notif._id)}
                          className={`p-4 border cursor-pointer transition-colors ${
                            notif.read
                              ? "border-border bg-white"
                              : "border-primary/30 bg-primary/5"
                          }`}
                          data-testid={`notification-${notif._id}`}
                        >
                          <div className="flex items-start gap-3">
                            <div className={`w-2 h-2 rounded-full mt-2 ${notif.read ? 'bg-muted' : 'bg-primary'}`} />
                            <div className="flex-1">
                              <p className="text-sm">{notif.message}</p>
                              <p className="text-xs text-muted-foreground mt-1">
                                {new Date(notif.created_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              to="/seller"
              className="p-6 bg-white border border-border hover:border-primary transition-colors flex items-center gap-4"
              data-testid="seller-dashboard-link"
            >
              <Tag className="h-8 w-8 text-primary" />
              <div>
                <h3 className="font-medium">Seller Dashboard</h3>
                <p className="text-sm text-muted-foreground">Manage your listings</p>
              </div>
            </Link>
            <Link
              to="/auctions"
              className="p-6 bg-white border border-border hover:border-primary transition-colors flex items-center gap-4"
              data-testid="browse-link"
            >
              <Gavel className="h-8 w-8 text-primary" />
              <div>
                <h3 className="font-medium">Browse Auctions</h3>
                <p className="text-sm text-muted-foreground">Find great deals</p>
              </div>
            </Link>
            <Link
              to="/account"
              className="p-6 bg-white border border-border hover:border-primary transition-colors flex items-center gap-4"
              data-testid="account-link"
            >
              <User className="h-8 w-8 text-primary" />
              <div>
                <h3 className="font-medium">Account Settings</h3>
                <p className="text-sm text-muted-foreground">Profile, phone and exchange methods</p>
              </div>
            </Link>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
