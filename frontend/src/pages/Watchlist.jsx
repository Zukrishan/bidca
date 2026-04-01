import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, formatCAD } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import {
  Heart,
  Gavel,
  Clock,
  MapPin,
  Trash,
  ArrowRight
} from "@phosphor-icons/react";

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

  const isUrgent = timeLeft.days === 0 && timeLeft.hours < 1;

  return (
    <span className={`font-mono tabular-nums ${isUrgent ? 'text-primary font-bold' : ''}`}>
      {timeLeft.days > 0 && `${timeLeft.days}d `}
      {String(timeLeft.hours).padStart(2, '0')}:
      {String(timeLeft.minutes).padStart(2, '0')}:
      {String(timeLeft.seconds).padStart(2, '0')}
    </span>
  );
}

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const { data } = await axios.get(`${API}/users/me/watchlist`);
      setWatchlist(data.watchlist || []);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const removeFromWatchlist = async (listingId) => {
    try {
      await axios.post(`${API}/listings/${listingId}/watch`);
      setWatchlist(watchlist.filter(w => w._id !== listingId));
    } catch (error) {
      console.error("Error:", error);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 mb-6">
            <Heart className="h-8 w-8 text-primary" weight="fill" />
            <h1 className="font-heading text-3xl font-bold">My Watchlist</h1>
          </div>

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-white animate-pulse h-32" />
              ))}
            </div>
          ) : watchlist.length === 0 ? (
            <div className="text-center py-16 bg-white border border-border">
              <Heart className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h2 className="font-heading text-xl font-bold mb-2">Your watchlist is empty</h2>
              <p className="text-muted-foreground mb-4">
                Save items you're interested in to track them here
              </p>
              <Link
                to="/auctions"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-medium"
              >
                Browse Auctions
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {watchlist.map(item => (
                <div key={item._id} className="bg-white border border-border p-4 flex gap-4">
                  <Link to={`/auctions/${item._id}`} className="w-32 h-32 bg-muted flex-shrink-0">
                    {item.images?.[0] ? (
                      <img src={item.images[0]} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Gavel className="h-8 w-8 text-muted-foreground" />
                      </div>
                    )}
                  </Link>
                  
                  <div className="flex-1 min-w-0">
                    <Link to={`/auctions/${item._id}`} className="hover:text-primary">
                      <h3 className="font-medium truncate">{item.title}</h3>
                    </Link>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                      <MapPin className="h-4 w-4" />
                      <span>{item.city}</span>
                      <span>•</span>
                      <span className="capitalize">{item.condition?.replace('_', ' ')}</span>
                    </div>
                    
                    <div className="flex items-center gap-6 mt-3">
                      <div>
                        <p className="text-xs text-muted-foreground">Current Bid</p>
                        <p className="font-bold text-lg">{formatCAD(item.current_bid)}</p>
                      </div>
                      {item.listing_type !== "fixed_price" && item.status === "active" && (
                        <div>
                          <p className="text-xs text-muted-foreground">Time Left</p>
                          <CountdownTimer endTime={item.end_time} />
                        </div>
                      )}
                      <div>
                        <p className="text-xs text-muted-foreground">Bids</p>
                        <p className="font-medium">{item.bid_count || 0}</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <Link
                      to={`/auctions/${item._id}`}
                      className="px-4 py-2 bg-primary text-white font-medium text-sm text-center hover:bg-primary/90"
                    >
                      View Auction
                    </Link>
                    <button
                      onClick={() => removeFromWatchlist(item._id)}
                      className="px-4 py-2 border border-border text-sm hover:border-destructive hover:text-destructive flex items-center justify-center gap-1"
                    >
                      <Trash className="h-4 w-4" />
                      Remove
                    </button>
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
