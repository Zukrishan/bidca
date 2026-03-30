import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { io } from "socket.io-client";
import axios from "axios";
import { API, useAuth, formatApiErrorDetail } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import { toast } from "sonner";
import {
  Gavel,
  MapPin,
  ShieldCheck,
  Clock,
  User,
  ArrowLeft,
  ArrowRight,
  Warning,
  CheckCircle,
  Flag
} from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Countdown Timer
function CountdownTimer({ endTime, onEnd }) {
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
    const timer = setInterval(() => {
      const newTime = calculateTimeLeft();
      setTimeLeft(newTime);
      if (newTime.ended && onEnd) onEnd();
    }, 1000);
    return () => clearInterval(timer);
  }, [endTime, onEnd]);

  if (timeLeft.ended) {
    return (
      <div className="text-center">
        <p className="text-2xl font-bold text-muted-foreground">Auction Ended</p>
      </div>
    );
  }

  const isUrgent = timeLeft.days === 0 && timeLeft.hours < 1;

  return (
    <div className={`flex gap-4 ${isUrgent ? 'animate-bid-pulse' : ''}`}>
      {timeLeft.days > 0 && (
        <div className="text-center">
          <div className={`text-3xl font-heading font-bold ${isUrgent ? 'text-primary' : ''}`}>
            {timeLeft.days}
          </div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Days</div>
        </div>
      )}
      <div className="text-center">
        <div className={`text-3xl font-heading font-bold font-mono tabular-nums ${isUrgent ? 'text-primary' : ''}`}>
          {String(timeLeft.hours).padStart(2, '0')}
        </div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">Hours</div>
      </div>
      <div className="text-center">
        <div className={`text-3xl font-heading font-bold font-mono tabular-nums ${isUrgent ? 'text-primary' : ''}`}>
          {String(timeLeft.minutes).padStart(2, '0')}
        </div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">Min</div>
      </div>
      <div className="text-center">
        <div className={`text-3xl font-heading font-bold font-mono tabular-nums ${isUrgent ? 'text-primary' : ''}`}>
          {String(timeLeft.seconds).padStart(2, '0')}
        </div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">Sec</div>
      </div>
    </div>
  );
}

export default function AuctionDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const socketRef = useRef(null);

  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState("");
  const [bidding, setBidding] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [reportReason, setReportReason] = useState("");
  const [reportDesc, setReportDesc] = useState("");

  useEffect(() => {
    fetchListing();
    setupSocket();

    return () => {
      if (socketRef.current?.connected) {
        socketRef.current.emit("leave_auction", { auction_id: id });
        socketRef.current.disconnect();
      }
    };
  }, [id]);

  const setupSocket = useCallback(() => {
    socketRef.current = io(BACKEND_URL, { path: "/api/socket.io" });

    socketRef.current.on("connect", () => {
      console.log("Socket connected");
      socketRef.current.emit("join_auction", { auction_id: id });
    });

    socketRef.current.on("bid_update", (data) => {
      if (data.listing_id === id) {
        setListing((prev) => ({
          ...prev,
          current_bid: data.current_bid,
          bid_count: data.bid_count
        }));
        toast.info(`New bid: $${data.current_bid.toLocaleString()}`);
      }
    });

    socketRef.current.on("auction_ended", (data) => {
      if (data.listing_id === id) {
        setListing((prev) => ({ ...prev, status: "ended" }));
        toast.info("Auction has ended!");
      }
    });
  }, [id]);

  const fetchListing = async () => {
    try {
      const { data } = await axios.get(`${API}/listings/${id}`);
      setListing(data);
      if (data.current_bid && data.bid_increment) {
        setBidAmount((data.current_bid + data.bid_increment).toFixed(2));
      }
    } catch (error) {
      console.error("Error fetching listing:", error);
      toast.error("Listing not found");
      navigate("/auctions");
    } finally {
      setLoading(false);
    }
  };

  const handleBidSubmit = async () => {
    if (!isAuthenticated) {
      toast.error("Please login to place a bid");
      navigate("/login");
      return;
    }

    setBidding(true);
    try {
      await axios.post(`${API}/listings/${id}/bid`, { amount: parseFloat(bidAmount) });
      toast.success("Bid placed successfully!");
      setShowConfirm(false);
      setBidAmount((parseFloat(bidAmount) + listing.bid_increment).toFixed(2));
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    } finally {
      setBidding(false);
    }
  };

  const handleReport = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/listings/${id}/report`, {
        reason: reportReason,
        description: reportDesc
      });
      toast.success("Report submitted successfully");
      setShowReport(false);
      setReportReason("");
      setReportDesc("");
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
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

  if (!listing) return null;

  const minBid = listing.current_bid + listing.bid_increment;
  const isAuction = listing.listing_type === "auction";
  const isActive = listing.status === "active";
  const isSeller = user && listing.seller_id === user._id;

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Back Link */}
          <Link
            to="/auctions"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6"
            data-testid="back-link"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Auctions
          </Link>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Image Gallery */}
            <div className="bg-white border border-border">
              <div className="relative aspect-square bg-muted">
                {listing.images?.length > 0 ? (
                  <img
                    src={listing.images[currentImageIndex]}
                    alt={listing.title}
                    className="w-full h-full object-contain"
                    data-testid="main-image"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Gavel className="h-24 w-24 text-muted-foreground" />
                  </div>
                )}

                {listing.images?.length > 1 && (
                  <>
                    <button
                      onClick={() => setCurrentImageIndex((i) => (i > 0 ? i - 1 : listing.images.length - 1))}
                      className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-white/90 flex items-center justify-center hover:bg-white transition-colors"
                    >
                      <ArrowLeft className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => setCurrentImageIndex((i) => (i < listing.images.length - 1 ? i + 1 : 0))}
                      className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-white/90 flex items-center justify-center hover:bg-white transition-colors"
                    >
                      <ArrowRight className="h-5 w-5" />
                    </button>
                  </>
                )}

                {isAuction && isActive && (
                  <div className="absolute top-4 left-4 flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white text-sm font-bold uppercase live-badge">
                    <span className="w-2 h-2 bg-white rounded-full" />
                    Live Auction
                  </div>
                )}
              </div>

              {/* Thumbnails */}
              {listing.images?.length > 1 && (
                <div className="flex gap-2 p-4 overflow-x-auto">
                  {listing.images.map((img, i) => (
                    <button
                      key={i}
                      onClick={() => setCurrentImageIndex(i)}
                      className={`w-16 h-16 flex-shrink-0 border-2 transition-colors ${
                        i === currentImageIndex ? "border-primary" : "border-transparent"
                      }`}
                    >
                      <img src={img} alt="" className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Details */}
            <div>
              {/* Category */}
              <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                {listing.category}
              </div>

              {/* Title */}
              <h1 className="font-heading text-2xl sm:text-3xl font-bold mb-4" data-testid="listing-title">
                {listing.title}
              </h1>

              {/* Seller Info */}
              <div className="flex items-center gap-3 mb-6 pb-6 border-b border-border">
                <div className="w-10 h-10 bg-secondary text-white flex items-center justify-center font-bold">
                  {listing.seller_name?.charAt(0) || "S"}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{listing.seller_name}</span>
                    {listing.seller_verified && (
                      <ShieldCheck className="h-5 w-5 text-primary" weight="fill" />
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <MapPin className="h-4 w-4" />
                    {listing.seller_city || listing.city}
                  </div>
                </div>
              </div>

              {/* Bid Section */}
              {isAuction ? (
                <div className="bg-white border border-border p-6 mb-6">
                  {isActive ? (
                    <>
                      <div className="flex items-center justify-between mb-6">
                        <div>
                          <p className="text-sm text-muted-foreground mb-1">Current Bid</p>
                          <p className="font-heading text-4xl font-bold bid-amount" data-testid="current-bid">
                            ${listing.current_bid?.toLocaleString()}
                          </p>
                          <p className="text-sm text-muted-foreground mt-1">
                            {listing.bid_count || 0} bids
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-muted-foreground mb-1">Time Left</p>
                          <CountdownTimer endTime={listing.end_time} />
                        </div>
                      </div>

                      {!isSeller && (
                        <div>
                          <label className="block text-sm font-medium mb-2">
                            Your Bid (Min: ${minBid.toLocaleString()})
                          </label>
                          <div className="flex gap-3">
                            <div className="flex-1 relative">
                              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                              <input
                                type="number"
                                value={bidAmount}
                                onChange={(e) => setBidAmount(e.target.value)}
                                min={minBid}
                                step={listing.bid_increment}
                                className="w-full pl-8 pr-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none text-lg font-bold"
                                data-testid="bid-input"
                              />
                            </div>
                            <button
                              onClick={() => setShowConfirm(true)}
                              disabled={parseFloat(bidAmount) < minBid}
                              className="px-6 py-3 bg-primary text-white font-bold hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              data-testid="place-bid-btn"
                            >
                              Place Bid
                            </button>
                          </div>
                        </div>
                      )}

                      {isSeller && (
                        <div className="p-4 bg-muted text-center">
                          <p className="text-muted-foreground">You cannot bid on your own auction</p>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-center py-6">
                      <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-3" />
                      <p className="font-heading text-xl font-bold mb-2">Auction Ended</p>
                      <p className="text-muted-foreground">
                        Final price: <span className="font-bold">${listing.current_bid?.toLocaleString()}</span>
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-white border border-border p-6 mb-6">
                  <div className="mb-4">
                    <p className="text-sm text-muted-foreground mb-1">Price</p>
                    <p className="font-heading text-4xl font-bold" data-testid="fixed-price">
                      ${listing.fixed_price?.toLocaleString()}
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">
                    Contact seller to purchase this item
                  </p>
                </div>
              )}

              {/* Bid History */}
              {isAuction && listing.bid_history?.length > 0 && (
                <div className="bg-white border border-border p-6 mb-6">
                  <h3 className="font-heading font-bold mb-4">Bid History</h3>
                  <div className="space-y-3 max-h-48 overflow-y-auto">
                    {listing.bid_history.map((bid, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">{bid.bidder_name}</span>
                        </div>
                        <span className="font-bold">${bid.amount?.toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              <div className="bg-white border border-border p-6 mb-6">
                <h3 className="font-heading font-bold mb-4">Description</h3>
                <p className="text-muted-foreground whitespace-pre-wrap" data-testid="description">
                  {listing.description}
                </p>
              </div>

              {/* Report */}
              <button
                onClick={() => setShowReport(true)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-destructive transition-colors"
                data-testid="report-btn"
              >
                <Flag className="h-4 w-4" />
                Report this listing
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bid Confirmation Modal */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white border border-border p-6 max-w-md w-full" data-testid="bid-confirm-modal">
            <h3 className="font-heading text-xl font-bold mb-4">Confirm Your Bid</h3>
            <div className="space-y-3 mb-6">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Item</span>
                <span className="font-medium">{listing.title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Your Bid</span>
                <span className="font-bold text-lg">${parseFloat(bidAmount).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Time Remaining</span>
                <span className="font-mono">
                  {Math.ceil((new Date(listing.end_time) - new Date()) / (1000 * 60 * 60))}h
                </span>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 px-4 py-3 border border-border font-medium hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleBidSubmit}
                disabled={bidding}
                className="flex-1 px-4 py-3 bg-primary text-white font-bold hover:bg-primary/90 transition-colors disabled:opacity-50"
                data-testid="confirm-bid-btn"
              >
                {bidding ? "Placing..." : "Confirm Bid"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report Modal */}
      {showReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white border border-border p-6 max-w-md w-full" data-testid="report-modal">
            <h3 className="font-heading text-xl font-bold mb-4">Report Listing</h3>
            <form onSubmit={handleReport}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Reason</label>
                <select
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  required
                  className="w-full px-4 py-3 border border-input bg-background focus:border-primary outline-none"
                >
                  <option value="">Select a reason</option>
                  <option value="fraud">Suspected Fraud</option>
                  <option value="prohibited">Prohibited Item</option>
                  <option value="misleading">Misleading Information</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="mb-6">
                <label className="block text-sm font-medium mb-2">Description</label>
                <textarea
                  value={reportDesc}
                  onChange={(e) => setReportDesc(e.target.value)}
                  required
                  rows={3}
                  className="w-full px-4 py-3 border border-input bg-background focus:border-primary outline-none resize-none"
                  placeholder="Please provide details..."
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowReport(false)}
                  className="flex-1 px-4 py-3 border border-border font-medium hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-3 bg-destructive text-white font-bold hover:bg-destructive/90 transition-colors"
                >
                  Submit Report
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
}
