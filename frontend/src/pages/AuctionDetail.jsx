import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { io } from "socket.io-client";
import axios from "axios";
import { API, useAuth, formatApiErrorDetail, formatCAD } from "../App";
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
  Heart,
  HeartStraight,
  Flag,
  Star,
  Lightning,
  Tag,
  Package,
  Timer,
  CheckCircle,
  Warning,
  Eye,
  CaretLeft,
  CaretRight
} from "@phosphor-icons/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Countdown Timer
function CountdownTimer({ endTime, onEnd, large = false }) {
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
    return <span className="text-muted-foreground">Auction Ended</span>;
  }

  const isUrgent = timeLeft.days === 0 && timeLeft.hours < 1;

  if (large) {
    return (
      <div className={`flex gap-3 ${isUrgent ? 'animate-bid-pulse' : ''}`}>
        {timeLeft.days > 0 && (
          <div className="text-center">
            <div className={`text-2xl font-bold font-mono ${isUrgent ? 'text-primary' : ''}`}>{timeLeft.days}</div>
            <div className="text-xs text-muted-foreground uppercase">Days</div>
          </div>
        )}
        <div className="text-center">
          <div className={`text-2xl font-bold font-mono tabular-nums ${isUrgent ? 'text-primary' : ''}`}>
            {String(timeLeft.hours).padStart(2, '0')}
          </div>
          <div className="text-xs text-muted-foreground uppercase">Hrs</div>
        </div>
        <div className="text-center">
          <div className={`text-2xl font-bold font-mono tabular-nums ${isUrgent ? 'text-primary' : ''}`}>
            {String(timeLeft.minutes).padStart(2, '0')}
          </div>
          <div className="text-xs text-muted-foreground uppercase">Min</div>
        </div>
        <div className="text-center">
          <div className={`text-2xl font-bold font-mono tabular-nums ${isUrgent ? 'text-primary' : ''}`}>
            {String(timeLeft.seconds).padStart(2, '0')}
          </div>
          <div className="text-xs text-muted-foreground uppercase">Sec</div>
        </div>
      </div>
    );
  }

  return (
    <span className={`font-mono tabular-nums ${isUrgent ? 'text-primary font-bold' : ''}`}>
      {timeLeft.days > 0 && `${timeLeft.days}d `}
      {String(timeLeft.hours).padStart(2, '0')}:
      {String(timeLeft.minutes).padStart(2, '0')}:
      {String(timeLeft.seconds).padStart(2, '0')}
    </span>
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
  const [isWatching, setIsWatching] = useState(false);
  const [showBidConfirm, setShowBidConfirm] = useState(false);
  const [showBuyNowConfirm, setShowBuyNowConfirm] = useState(false);
  const [showSniperModal, setShowSniperModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [sniperMinutes, setSniperMinutes] = useState(5);
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
      socketRef.current.emit("join_auction", { auction_id: id });
    });

    socketRef.current.on("bid_update", (data) => {
      if (data.listing_id === id) {
        setListing((prev) => prev ? ({
          ...prev,
          current_bid: data.current_bid,
          bid_count: data.bid_count,
          bid_increment: data.bid_increment,
          reserve_met: data.reserve_met
        }) : prev);
        toast.info(`New bid: ${formatCAD(data.current_bid)}`);
      }
    });

    socketRef.current.on("auction_ended", (data) => {
      if (data.listing_id === id) {
        setListing((prev) => prev ? ({ ...prev, status: "sold" }) : prev);
        toast.info("Auction has ended!");
      }
    });
  }, [id]);

  const fetchListing = async () => {
    try {
      const { data } = await axios.get(`${API}/listings/${id}`);
      setListing(data);
      setIsWatching(data.is_watching || false);
      if (data.current_bid && data.bid_increment) {
        const minBid = data.bid_count > 0 ? data.current_bid + data.bid_increment : data.current_bid;
        setBidAmount(minBid.toFixed(2));
      }
    } catch (error) {
      console.error("Error:", error);
      toast.error("Listing not found");
      navigate("/auctions");
    } finally {
      setLoading(false);
    }
  };

  const handleWatch = async () => {
    if (!isAuthenticated) {
      toast.error("Please login to watch items");
      navigate("/login");
      return;
    }
    try {
      const { data } = await axios.post(`${API}/listings/${id}/watch`);
      setIsWatching(data.watching);
      toast.success(data.message);
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    }
  };

  const handleBidSubmit = async () => {
    if (!isAuthenticated) {
      toast.error("Please login to bid");
      navigate("/login");
      return;
    }

    setBidding(true);
    try {
      const { data } = await axios.post(`${API}/listings/${id}/bid`, { max_bid: parseFloat(bidAmount) });
      toast.success(data.message);
      setShowBidConfirm(false);
      
      // Update bid amount for next bid
      const newMinBid = data.current_bid + (listing?.bid_increment || 5);
      setBidAmount(newMinBid.toFixed(2));
      
      // Refresh listing
      fetchListing();
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    } finally {
      setBidding(false);
    }
  };

  const handleBuyNow = async () => {
    if (!isAuthenticated) {
      toast.error("Please login to purchase");
      navigate("/login");
      return;
    }

    setBidding(true);
    try {
      const { data } = await axios.post(`${API}/listings/${id}/buy-now`);
      toast.success(data.message);
      setShowBuyNowConfirm(false);
      navigate("/dashboard");
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    } finally {
      setBidding(false);
    }
  };

  const handleSniperBid = async () => {
    if (!isAuthenticated) {
      toast.error("Please login");
      return;
    }

    try {
      await axios.post(`${API}/listings/${id}/sniper-bid`, {
        max_bid: parseFloat(bidAmount),
        minutes_before_end: sniperMinutes
      });
      toast.success(`Sniper bid scheduled for ${sniperMinutes} minutes before end`);
      setShowSniperModal(false);
    } catch (error) {
      toast.error(formatApiErrorDetail(error.response?.data?.detail));
    }
  };

  const handleReport = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/listings/${id}/report`, { reason: reportReason, description: reportDesc });
      toast.success("Report submitted");
      setShowReportModal(false);
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

  const minBid = listing.bid_count > 0 ? listing.current_bid + listing.bid_increment : listing.current_bid;
  const isAuction = listing.listing_type !== "fixed_price";
  const isActive = listing.status === "active";
  const isSeller = user && listing.seller_id === user._id;
  const sellerInfo = listing.seller_info || {};

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
            <Link to="/auctions" className="hover:text-primary">Auctions</Link>
            <span>/</span>
            <Link to={`/auctions?category=${listing.category}`} className="hover:text-primary">{listing.category}</Link>
            {listing.subcategory && (
              <>
                <span>/</span>
                <span>{listing.subcategory}</span>
              </>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Images */}
            <div className="lg:col-span-2">
              <div className="bg-white border border-border">
                {/* Main Image */}
                <div className="relative aspect-[4/3] bg-muted">
                  {listing.images?.length > 0 ? (
                    <img
                      src={listing.images[currentImageIndex]}
                      alt={listing.title}
                      className="w-full h-full object-contain"
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
                        className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-white/90 flex items-center justify-center hover:bg-white"
                      >
                        <CaretLeft className="h-6 w-6" />
                      </button>
                      <button
                        onClick={() => setCurrentImageIndex((i) => (i < listing.images.length - 1 ? i + 1 : 0))}
                        className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-white/90 flex items-center justify-center hover:bg-white"
                      >
                        <CaretRight className="h-6 w-6" />
                      </button>
                    </>
                  )}

                  {/* Badges */}
                  <div className="absolute top-3 left-3 flex flex-col gap-1">
                    {isAuction && isActive && (
                      <span className="px-2 py-1 bg-primary text-white text-xs font-bold uppercase live-badge flex items-center gap-1">
                        <span className="w-2 h-2 bg-white rounded-full animate-pulse" /> LIVE
                      </span>
                    )}
                  </div>

                  {/* Views & Watchers */}
                  <div className="absolute bottom-3 right-3 flex gap-2">
                    <span className="flex items-center gap-1 px-2 py-1 bg-black/70 text-white text-xs">
                      <Eye className="h-3 w-3" /> {listing.views_count || 0}
                    </span>
                    <span className="flex items-center gap-1 px-2 py-1 bg-black/70 text-white text-xs">
                      <Heart className="h-3 w-3" /> {listing.watchers_count || 0}
                    </span>
                  </div>
                </div>

                {/* Thumbnails */}
                {listing.images?.length > 1 && (
                  <div className="flex gap-2 p-3 overflow-x-auto">
                    {listing.images.map((img, i) => (
                      <button
                        key={i}
                        onClick={() => setCurrentImageIndex(i)}
                        className={`w-16 h-16 flex-shrink-0 border-2 ${i === currentImageIndex ? 'border-primary' : 'border-transparent'}`}
                      >
                        <img src={img} alt="" className="w-full h-full object-cover" />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Description */}
              <div className="bg-white border border-border p-6 mt-4">
                <h2 className="font-bold text-lg mb-4">Description</h2>
                <p className="text-muted-foreground whitespace-pre-wrap">{listing.description}</p>
                
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-border">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase">Condition</p>
                    <p className="font-medium capitalize">{listing.condition?.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase">Location</p>
                    <p className="font-medium">{listing.city}</p>
                  </div>
                </div>
              </div>

              {/* Bid History */}
              {isAuction && listing.bid_history?.length > 0 && (
                <div className="bg-white border border-border p-6 mt-4">
                  <h2 className="font-bold text-lg mb-4">Bid History ({listing.bid_count} bids)</h2>
                  <div className="max-h-64 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="border-b border-border">
                        <tr className="text-left text-muted-foreground">
                          <th className="pb-2">Bidder</th>
                          <th className="pb-2 text-right">Amount</th>
                          <th className="pb-2 text-right">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {listing.bid_history.map((bid, i) => (
                          <tr key={i} className="border-b border-border last:border-0">
                            <td className="py-2">
                              <span className="flex items-center gap-1">
                                <User className="h-4 w-4 text-muted-foreground" />
                                {bid.bidder_name}
                                {bid.is_auto_bid && <span className="text-xs text-muted-foreground">(auto)</span>}
                              </span>
                            </td>
                            <td className="py-2 text-right font-bold">{formatCAD(bid.amount)}</td>
                            <td className="py-2 text-right text-muted-foreground text-xs">
                              {new Date(bid.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Bidding Panel */}
            <div className="lg:col-span-1">
              <div className="bg-white border border-border p-6 sticky top-20">
                {/* Title */}
                <h1 className="font-heading text-xl font-bold mb-2">{listing.title}</h1>
                
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                  <span className="px-2 py-0.5 bg-muted text-xs font-medium">{listing.category}</span>
                  <span>•</span>
                  <span className="capitalize">{listing.condition?.replace('_', ' ')}</span>
                </div>

                {/* Price/Bid Section */}
                {isActive ? (
                  <>
                    {isAuction ? (
                      <div className="mb-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-muted-foreground">Current Bid</span>
                          <span className="text-sm text-muted-foreground">{listing.bid_count} bids</span>
                        </div>
                        <p className="text-3xl font-bold bid-amount">{formatCAD(listing.current_bid)}</p>
                        
                        {/* Reserve indicator */}
                        {listing.reserve_price && (
                          <p className={`text-sm mt-1 ${listing.reserve_met ? 'text-green-600' : 'text-yellow-600'}`}>
                            {listing.reserve_met ? '✓ Reserve met' : '⚠ Reserve not met'}
                          </p>
                        )}

                        {/* Time Left */}
                        <div className="mt-4 p-3 bg-muted">
                          <p className="text-xs text-muted-foreground uppercase mb-1">Time Left</p>
                          <CountdownTimer endTime={listing.end_time} large />
                        </div>

                        {/* Bidding Form */}
                        {!isSeller && (
                          <div className="mt-4">
                            <label className="block text-sm font-medium mb-2">
                              Your Maximum Bid (Min: {formatCAD(minBid)})
                            </label>
                            <p className="text-xs text-muted-foreground mb-2">
                              We'll bid for you up to this amount
                            </p>
                            <div className="flex gap-2">
                              <div className="flex-1 relative">
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                                <input
                                  type="number"
                                  value={bidAmount}
                                  onChange={(e) => setBidAmount(e.target.value)}
                                  min={minBid}
                                  step={listing.bid_increment}
                                  className="w-full pl-8 pr-4 py-3 border border-input focus:border-primary outline-none font-bold text-lg"
                                  data-testid="bid-input"
                                />
                              </div>
                            </div>
                            <button
                              onClick={() => setShowBidConfirm(true)}
                              disabled={parseFloat(bidAmount) < minBid}
                              className="w-full mt-3 py-3 bg-primary text-white font-bold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                              data-testid="place-bid-btn"
                            >
                              <Gavel className="h-5 w-5" />
                              Place Bid
                            </button>

                            {/* Sniper Bid */}
                            <button
                              onClick={() => setShowSniperModal(true)}
                              className="w-full mt-2 py-2 border border-border text-sm font-medium hover:border-primary flex items-center justify-center gap-2"
                            >
                              <Timer className="h-4 w-4" />
                              Set Sniper Bid
                            </button>
                          </div>
                        )}

                        {/* Buy It Now */}
                        {listing.buy_it_now_price && !isSeller && (
                          <div className="mt-4 pt-4 border-t border-border">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium">Buy It Now</span>
                              <span className="font-bold text-lg">{formatCAD(listing.buy_it_now_price)}</span>
                            </div>
                            <button
                              onClick={() => setShowBuyNowConfirm(true)}
                              className="w-full py-3 bg-green-600 text-white font-bold hover:bg-green-700 flex items-center justify-center gap-2"
                              data-testid="buy-now-btn"
                            >
                              <Lightning className="h-5 w-5" />
                              Buy It Now
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      /* Fixed Price */
                      <div className="mb-4">
                        <p className="text-sm text-muted-foreground mb-1">Price</p>
                        <p className="text-3xl font-bold">{formatCAD(listing.buy_it_now_price)}</p>
                        
                        {!isSeller && (
                          <button
                            onClick={() => setShowBuyNowConfirm(true)}
                            className="w-full mt-4 py-3 bg-primary text-white font-bold hover:bg-primary/90 flex items-center justify-center gap-2"
                          >
                            <Tag className="h-5 w-5" />
                            Buy Now
                          </button>
                        )}
                      </div>
                    )}

                    {isSeller && (
                      <div className="p-4 bg-muted text-center text-sm text-muted-foreground">
                        This is your listing
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-6">
                    <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-3" />
                    <p className="font-bold text-lg mb-2">
                      {listing.status === "sold" ? "Sold!" : "Auction Ended"}
                    </p>
                    {listing.sold_price && (
                      <p className="text-muted-foreground">
                        Final price: <span className="font-bold">{formatCAD(listing.sold_price)}</span>
                      </p>
                    )}
                  </div>
                )}

                {/* Watch Button */}
                <button
                  onClick={handleWatch}
                  className={`w-full mt-4 py-2 border flex items-center justify-center gap-2 font-medium ${
                    isWatching ? 'border-primary text-primary bg-primary/5' : 'border-border hover:border-primary'
                  }`}
                  data-testid="watch-btn"
                >
                  {isWatching ? (
                    <>
                      <HeartStraight className="h-5 w-5" weight="fill" />
                      Watching
                    </>
                  ) : (
                    <>
                      <Heart className="h-5 w-5" />
                      Add to Watchlist
                    </>
                  )}
                </button>

                {/* Seller Info */}
                <div className="mt-6 pt-6 border-t border-border">
                  <h3 className="font-bold mb-3">Seller</h3>
                  <Link
                    to={`/users/${listing.seller_id}`}
                    className="flex items-center gap-3 p-3 bg-muted hover:bg-muted/80 transition-colors"
                  >
                    <div className="w-12 h-12 bg-secondary text-white flex items-center justify-center font-bold text-lg">
                      {sellerInfo.display_name?.charAt(0) || 'S'}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{sellerInfo.display_name || listing.seller_name}</span>
                        {(listing.seller_verified || sellerInfo.verification_badge) && (
                          <ShieldCheck className="h-4 w-4 text-primary" weight="fill" />
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Star className="h-4 w-4 text-yellow-500" weight="fill" />
                        <span>{sellerInfo.seller_rating?.toFixed(1) || '5.0'}</span>
                        <span className="text-muted-foreground">
                          ({sellerInfo.total_ratings || 0} ratings)
                        </span>
                        <span className="text-green-600">
                          {sellerInfo.positive_percentage?.toFixed(0) || 100}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        <MapPin className="h-3 w-3 inline" /> {sellerInfo.city || listing.seller_city}
                      </p>
                    </div>
                  </Link>
                </div>

                {/* Exchange: in person, no payments through BidCa (NFR-07) */}
                <div className="mt-4 p-3 bg-muted">
                  <div className="flex items-center gap-2 mb-2">
                    <Package className="h-5 w-5 text-muted-foreground" />
                    <span className="font-medium">Exchange</span>
                  </div>
                  <p className="text-sm">Arrange the exchange directly with the seller in {listing.city}. BidCa does not handle payments.</p>
                </div>

                {/* Report */}
                <button
                  onClick={() => setShowReportModal(true)}
                  className="w-full mt-4 text-sm text-muted-foreground hover:text-destructive flex items-center justify-center gap-1"
                >
                  <Flag className="h-4 w-4" />
                  Report this listing
                </button>
              </div>
            </div>
          </div>

          {/* Related Items */}
          {listing.related_items?.length > 0 && (
            <div className="mt-8">
              <h2 className="font-heading text-xl font-bold mb-4">Similar Items</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {listing.related_items.map((item) => (
                  <Link
                    key={item._id}
                    to={`/auctions/${item._id}`}
                    className="bg-white border border-border overflow-hidden hover:shadow-md transition-all"
                  >
                    <div className="aspect-square bg-muted">
                      {item.images?.[0] ? (
                        <img src={item.images[0]} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Gavel className="h-8 w-8 text-muted-foreground" />
                        </div>
                      )}
                    </div>
                    <div className="p-2">
                      <p className="text-sm font-medium line-clamp-1">{item.title}</p>
                      <p className="font-bold text-sm">{formatCAD(item.current_bid)}</p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bid Confirmation Modal */}
      {showBidConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white border border-border p-6 max-w-md w-full" data-testid="bid-confirm-modal">
            <h3 className="font-heading text-xl font-bold mb-4">Confirm Your Bid</h3>
            <div className="bg-yellow-50 border border-yellow-200 p-3 mb-4 text-sm">
              <Warning className="h-5 w-5 text-yellow-600 inline mr-2" />
              <strong>Bids are binding.</strong> You agree to pay this amount if you win.
            </div>
            <div className="space-y-2 mb-4">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Your Maximum Bid</span>
                <span className="font-bold text-xl">{formatCAD(parseFloat(bidAmount))}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Current Bid</span>
                <span>{formatCAD(listing.current_bid)}</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              We'll automatically bid for you up to your maximum. You'll only pay what's needed to win.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowBidConfirm(false)}
                className="flex-1 py-3 border border-border font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleBidSubmit}
                disabled={bidding}
                className="flex-1 py-3 bg-primary text-white font-bold hover:bg-primary/90 disabled:opacity-50"
                data-testid="confirm-bid-btn"
              >
                {bidding ? "Placing..." : "Confirm Bid"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Buy Now Confirmation Modal */}
      {showBuyNowConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white border border-border p-6 max-w-md w-full">
            <h3 className="font-heading text-xl font-bold mb-4">Confirm Purchase</h3>
            <div className="space-y-2 mb-4">
              <p className="font-medium">{listing.title}</p>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Price</span>
                <span className="font-bold text-xl">{formatCAD(listing.buy_it_now_price)}</span>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              This will end the auction immediately and you'll be the winner.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowBuyNowConfirm(false)}
                className="flex-1 py-3 border border-border font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleBuyNow}
                disabled={bidding}
                className="flex-1 py-3 bg-green-600 text-white font-bold hover:bg-green-700 disabled:opacity-50"
              >
                {bidding ? "Processing..." : "Confirm Purchase"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sniper Bid Modal */}
      {showSniperModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white border border-border p-6 max-w-md w-full">
            <h3 className="font-heading text-xl font-bold mb-4">Schedule Sniper Bid</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Your bid will be automatically placed just before the auction ends.
            </p>
            <div className="space-y-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-2">Maximum Bid</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                  <input
                    type="number"
                    value={bidAmount}
                    onChange={(e) => setBidAmount(e.target.value)}
                    className="w-full pl-8 pr-4 py-2 border border-input outline-none focus:border-primary"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Place bid at</label>
                <select
                  value={sniperMinutes}
                  onChange={(e) => setSniperMinutes(parseInt(e.target.value))}
                  className="w-full py-2 px-3 border border-input outline-none focus:border-primary"
                >
                  <option value={1}>1 minute before end</option>
                  <option value={2}>2 minutes before end</option>
                  <option value={3}>3 minutes before end</option>
                  <option value={5}>5 minutes before end</option>
                  <option value={10}>10 minutes before end</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowSniperModal(false)}
                className="flex-1 py-3 border border-border font-medium hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={handleSniperBid}
                className="flex-1 py-3 bg-secondary text-white font-bold hover:bg-secondary/90"
              >
                Schedule Sniper Bid
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report Modal */}
      {showReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white border border-border p-6 max-w-md w-full">
            <h3 className="font-heading text-xl font-bold mb-4">Report Listing</h3>
            <form onSubmit={handleReport}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Reason</label>
                <select
                  value={reportReason}
                  onChange={(e) => setReportReason(e.target.value)}
                  required
                  className="w-full py-2 px-3 border border-input outline-none focus:border-primary"
                >
                  <option value="">Select a reason</option>
                  <option value="fraud">Suspected Fraud</option>
                  <option value="prohibited">Prohibited Item</option>
                  <option value="misleading">Misleading Description</option>
                  <option value="counterfeit">Counterfeit Item</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Details</label>
                <textarea
                  value={reportDesc}
                  onChange={(e) => setReportDesc(e.target.value)}
                  required
                  rows={3}
                  className="w-full px-3 py-2 border border-input outline-none focus:border-primary resize-none"
                  placeholder="Please provide details..."
                />
              </div>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowReportModal(false)}
                  className="flex-1 py-3 border border-border font-medium hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 bg-destructive text-white font-bold hover:bg-destructive/90"
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
