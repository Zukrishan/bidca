import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth, API, formatCAD, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import axios from "axios";
import { toast } from "sonner";
import {
  ShieldCheck,
  Gavel,
  Tag,
  Clock,
  Bell,
  Plus,
  MapPin,
  CheckCircle,
  Warning,
  ArrowRight,
  ChatCircle,
  Handshake
} from "@phosphor-icons/react";

// Transaction states (no money involved: open → completed, or disputed / cancelled)
const TX_LABELS = {
  open: "Awaiting completion",
  completed: "Completed",
  disputed: "Disputed",
  cancelled: "Cancelled"
};

const LISTING_LABELS = {
  pending: "Pending review",
  active: "Active",
  sold: "Sold",
  unsold: "Ended, unsold",
  ended: "Ended",
  rejected: "Rejected"
};

// The transaction page lives in the Next.js app (web), so it's a plain link, not a router Link
function MessageButton({ transactionId }) {
  return (
    <a
      href={`/messages/${transactionId}`}
      className="inline-flex items-center gap-1 px-3 py-2 bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
      data-testid={`message-${transactionId}`}
    >
      <ChatCircle className="h-4 w-4" />
      Message
    </a>
  );
}

function Thumb({ src }) {
  return (
    <div className="w-16 h-16 bg-muted flex-shrink-0">
      {src ? (
        <img src={src} alt="" className="w-full h-full object-cover" />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <Gavel className="h-6 w-6 text-muted-foreground" />
        </div>
      )}
    </div>
  );
}

function Empty({ icon: Icon, text, children }) {
  return (
    <div className="text-center py-12">
      <Icon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
      <p className="text-muted-foreground mb-4">{text}</p>
      {children}
    </div>
  );
}

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
  // FR-23: Selling / Current Bids / Successfully Completed (+ Notifications)
  const [activeTab, setActiveTab] = useState("bids");
  const [selling, setSelling] = useState([]);
  const [bids, setBids] = useState([]);
  const [won, setWon] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [sellingRes, bidsRes, completedRes, notifRes] = await Promise.all([
        axios.get(`${API}/users/me/selling`),
        axios.get(`${API}/users/me/current-bids`),
        axios.get(`${API}/users/me/completed`),
        axios.get(`${API}/notifications`)
      ]);
      setSelling(sellingRes.data.listings || []);
      setBids(bidsRes.data.bids || []);
      setWon(bidsRes.data.won || []);
      setCompleted(completedRes.data.transactions || []);
      setNotifications(notifRes.data.notifications || []);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  const relist = async (listingId) => {
    try {
      await axios.post(`${API}/listings/${listingId}/relist`);
      toast.success("Relisted — it goes live after review");
      fetchData();
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    }
  };

  const tabs = [
    { id: "selling", label: "Selling", icon: Tag },
    { id: "bids", label: "Current Bids", icon: Gavel, count: won.length },
    { id: "completed", label: "Successfully Completed", icon: Handshake },
    { id: "notifications", label: "Notifications", icon: Bell }
  ];

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
                {user?.full_name?.charAt(0) || "U"}
              </div>
              
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="font-heading text-2xl font-bold">{user?.full_name}</h1>
                  {user?.verification_badge ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-secondary text-white text-xs font-bold">
                      <ShieldCheck className="h-4 w-4" weight="fill" />
                      Verified
                    </span>
                  ) : user?.verification_status === "pending" ? (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-500 text-white text-xs font-bold">
                      <Clock className="h-4 w-4" />
                      Pending
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-muted text-muted-foreground text-xs font-bold">
                      Unverified
                    </span>
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
                {!user?.verification_badge && user?.verification_status !== "pending" && (
                  <Link
                    to="/verification"
                    className="px-4 py-2 bg-secondary text-white font-medium hover:bg-secondary/90 transition-colors flex items-center gap-2"
                    data-testid="get-verified-btn"
                  >
                    <ShieldCheck className="h-5 w-5" />
                    Get Verified
                  </Link>
                )}
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

          {/* Tabs (FR-23) */}
          <div className="bg-white border border-border mb-6">
            <div className="flex overflow-x-auto border-b border-border" role="tablist">
              {tabs.map(({ id, label, icon: Icon, count }) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={activeTab === id}
                  onClick={() => setActiveTab(id)}
                  className={`flex-1 flex-shrink-0 whitespace-nowrap px-4 py-3 text-sm font-medium transition-colors relative ${
                    activeTab === id
                      ? "border-b-2 border-primary text-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  data-testid={`tab-${id}`}
                >
                  <Icon className="h-5 w-5 inline mr-2" />
                  {label}
                  {id === "notifications" && unreadCount > 0 && (
                    <span className="ml-2 inline-flex w-5 h-5 bg-primary text-white text-xs rounded-full items-center justify-center">
                      {unreadCount}
                    </span>
                  )}
                  {count > 0 && (
                    <span className="ml-2 inline-flex w-5 h-5 bg-primary text-white text-xs rounded-full items-center justify-center">
                      {count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="p-6">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : activeTab === "selling" ? (
                selling.length === 0 ? (
                  <Empty icon={Tag} text="You aren't selling anything yet.">
                    <Link
                      to="/create-listing"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
                    >
                      Sell an item
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Empty>
                ) : (
                  <div className="space-y-4">
                    {selling.map((l) => {
                      const tx = l.transaction;
                      const fellThrough = tx && tx.status === "cancelled";
                      return (
                        <div
                          key={l._id}
                          className="flex flex-col sm:flex-row sm:items-center gap-4 p-4 border border-border"
                          data-testid={`selling-${l._id}`}
                        >
                          <div className="flex items-center gap-4 flex-1 min-w-0">
                            <Thumb src={l.image} />
                            <div className="flex-1 min-w-0">
                              <Link to={`/auctions/${l._id}`} className="font-medium truncate block hover:underline">
                                {l.title}
                              </Link>
                              <p className="text-sm text-muted-foreground">
                                {LISTING_LABELS[l.status] || l.status}
                                {tx ? ` · ${TX_LABELS[tx.status] || tx.status}` : ""}
                                {fellThrough && tx.cancelled_reason === "no_response" ? " (buyer didn't respond)" : ""}
                              </p>
                              <p className="text-sm">
                                <span className="font-bold">
                                  {formatCAD(l.status === "sold" ? l.sold_price : l.current_bid ?? l.buy_it_now_price)}
                                </span>
                                {l.status === "active" && l.listing_type !== "fixed_price" && (
                                  <span className="text-muted-foreground"> · {l.bid_count || 0} bids · <CountdownTimer endTime={l.end_time} /></span>
                                )}
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-2 flex-shrink-0">
                            {tx && !fellThrough && <MessageButton transactionId={tx._id} />}
                            {(l.status === "unsold" || l.status === "ended" || (l.status === "sold" && fellThrough)) && (
                              <button
                                onClick={() => relist(l._id)}
                                className="px-3 py-2 border border-border text-sm font-medium hover:border-primary transition-colors"
                                data-testid={`relist-${l._id}`}
                              >
                                Relist
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )
              ) : activeTab === "bids" ? (
                bids.length === 0 && won.length === 0 ? (
                  <Empty icon={Gavel} text="You have no active bids or items waiting to be completed.">
                    <Link
                      to="/auctions"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
                    >
                      Browse Auctions
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Empty>
                ) : (
                  <div className="space-y-6">
                    {won.length > 0 && (
                      <section>
                        <h2 className="font-heading font-bold mb-3">Won — message the seller to complete</h2>
                        <div className="space-y-4">
                          {won.map((t) => (
                            <div
                              key={t._id}
                              className="flex flex-col sm:flex-row sm:items-center gap-4 p-4 border border-primary/40"
                              data-testid={`won-${t._id}`}
                            >
                              <div className="flex items-center gap-4 flex-1 min-w-0">
                                <Thumb src={t.listing.image} />
                                <div className="flex-1 min-w-0">
                                  <h3 className="font-medium truncate">{t.listing.title}</h3>
                                  <p className="text-sm text-muted-foreground">
                                    {formatCAD(t.amount)} · from {t.other_party.full_name} · {TX_LABELS[t.status] || t.status}
                                    {t.my_completed && t.status === "open" ? " (waiting for the seller)" : ""}
                                  </p>
                                </div>
                              </div>
                              <MessageButton transactionId={t._id} />
                            </div>
                          ))}
                        </div>
                      </section>
                    )}
                    {bids.length > 0 && (
                      <section>
                        <h2 className="font-heading font-bold mb-3">Bidding now</h2>
                        <div className="space-y-4">
                          {bids.map((b) => (
                            <Link
                              key={b._id}
                              to={`/auctions/${b._id}`}
                              className="flex items-center gap-4 p-4 border border-border hover:border-primary transition-colors"
                              data-testid={`bid-item-${b._id}`}
                            >
                              <Thumb src={b.image} />
                              <div className="flex-1 min-w-0">
                                <h3 className="font-medium truncate">{b.title}</h3>
                                <p className="text-sm text-muted-foreground">
                                  Current bid: <span className="font-bold text-foreground">{formatCAD(b.current_bid)}</span>
                                  {b.my_max_bid ? ` · your max ${formatCAD(b.my_max_bid)}` : ""}
                                </p>
                              </div>
                              <div className="text-right flex-shrink-0">
                                {b.is_winning ? (
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
                                  <CountdownTimer endTime={b.end_time} />
                                </p>
                              </div>
                            </Link>
                          ))}
                        </div>
                      </section>
                    )}
                  </div>
                )
              ) : activeTab === "completed" ? (
                completed.length === 0 ? (
                  <Empty icon={Handshake} text="No completed transactions yet." />
                ) : (
                  <div className="space-y-4">
                    {completed.map((t) => (
                      <div
                        key={t._id}
                        className="flex flex-col sm:flex-row sm:items-center gap-4 p-4 border border-border"
                        data-testid={`completed-${t._id}`}
                      >
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <Thumb src={t.listing.image} />
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium truncate">{t.listing.title}</h3>
                            <p className="text-sm text-muted-foreground">
                              {t.role === "buyer" ? "Bought from" : "Sold to"} {t.other_party.full_name} · {formatCAD(t.amount)}
                              {t.completed_at ? ` · ${new Date(t.completed_at).toLocaleDateString()}` : ""}
                            </p>
                          </div>
                        </div>
                        <a
                          href={`/messages/${t._id}`}
                          className="px-3 py-2 border border-border text-sm font-medium hover:border-primary transition-colors text-center"
                        >
                          {t.rated ? "View" : "Rate"}
                        </a>
                      </div>
                    ))}
                  </div>
                )
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
                    <Empty icon={Bell} text="No notifications yet." />
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
              to="/verification"
              className="p-6 bg-white border border-border hover:border-primary transition-colors flex items-center gap-4"
              data-testid="verification-link"
            >
              <ShieldCheck className="h-8 w-8 text-primary" />
              <div>
                <h3 className="font-medium">Verification</h3>
                <p className="text-sm text-muted-foreground">Build trust</p>
              </div>
            </Link>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
