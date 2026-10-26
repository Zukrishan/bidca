import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth, formatCAD } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import {
  MagnifyingGlass,
  Gavel,
  Clock,
  Fire,
  Star,
  ArrowRight,
  MapPin,
  ShieldCheck,
  Lightning,
  Tag,
  Heart,
  Users,
  Trophy,
  Package
} from "@phosphor-icons/react";

// Countdown Timer Component
function CountdownTimer({ endTime, compact = false }) {
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft());

  function calculateTimeLeft() {
    const difference = new Date(endTime) - new Date();
    if (difference <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0, ended: true };
    
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

  if (compact) {
    return (
      <span className={`font-mono tabular-nums ${isUrgent ? 'text-primary animate-bid-pulse font-bold' : ''}`}>
        {timeLeft.days > 0 && `${timeLeft.days}d `}
        {String(timeLeft.hours).padStart(2, '0')}:
        {String(timeLeft.minutes).padStart(2, '0')}:
        {String(timeLeft.seconds).padStart(2, '0')}
      </span>
    );
  }

  return (
    <div className={`flex gap-1 ${isUrgent ? 'text-primary' : ''}`}>
      {timeLeft.days > 0 && <span className="font-mono">{timeLeft.days}d</span>}
      <span className="font-mono tabular-nums">
        {String(timeLeft.hours).padStart(2, '0')}:{String(timeLeft.minutes).padStart(2, '0')}:{String(timeLeft.seconds).padStart(2, '0')}
      </span>
    </div>
  );
}

// Auction Card Component
function AuctionCard({ auction }) {
  const isUrgent = new Date(auction.end_time) - new Date() < 3600000; // Less than 1 hour

  return (
    <Link
      to={`/auctions/${auction._id}`}
      className="group auction-card block bg-white border border-border overflow-hidden hover:shadow-lg transition-all"
      data-testid={`auction-card-${auction._id}`}
    >
      {/* Image */}
      <div className="relative aspect-square bg-muted overflow-hidden">
        {auction.images?.[0] ? (
          <img
            src={auction.images[0]}
            alt={auction.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Gavel className="h-12 w-12 text-muted-foreground" />
          </div>
        )}
        
        {/* Badges */}
        <div className="absolute top-2 left-2 flex flex-col gap-1">
          {auction.listing_type !== "fixed_price" && (
            <div className={`flex items-center gap-1 px-2 py-0.5 text-xs font-bold uppercase ${isUrgent ? 'bg-primary text-white live-badge' : 'bg-secondary text-white'}`}>
              {isUrgent && <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />}
              {isUrgent ? 'Ending Soon' : 'Auction'}
            </div>
          )}
          {auction.buy_it_now_price && (
            <div className="px-2 py-0.5 bg-green-600 text-white text-xs font-bold uppercase">
              BIN Available
            </div>
          )}
        </div>

        {auction.seller_verified && (
          <div className="absolute top-2 right-2 p-1 bg-white/90 rounded-full">
            <ShieldCheck className="h-4 w-4 text-primary" weight="fill" />
          </div>
        )}

        {/* Watch count */}
        {auction.watchers_count > 0 && (
          <div className="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-0.5 bg-black/70 text-white text-xs">
            <Heart className="h-3 w-3" />
            {auction.watchers_count}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-3">
        <h3 className="font-medium text-sm mb-1 line-clamp-2 group-hover:text-primary transition-colors min-h-[40px]">
          {auction.title}
        </h3>
        
        <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
          <MapPin className="h-3 w-3" />
          <span>{auction.city}</span>
          {auction.condition && (
            <>
              <span>•</span>
              <span className="capitalize">{auction.condition.replace('_', ' ')}</span>
            </>
          )}
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">
              {auction.listing_type === "fixed_price" ? "Price" : `${auction.bid_count || 0} bids`}
            </p>
            <p className="font-bold text-lg bid-amount">
              {formatCAD(auction.listing_type === "fixed_price" ? auction.buy_it_now_price : auction.current_bid)}
            </p>
          </div>
          {auction.listing_type !== "fixed_price" && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Time left</p>
              <CountdownTimer endTime={auction.end_time} compact />
            </div>
          )}
        </div>

        {/* Reserve indicator */}
        {auction.reserve_price && !auction.reserve_met && (
          <p className="text-xs text-yellow-600 mt-1 font-medium">Reserve not met</p>
        )}
      </div>
    </Link>
  );
}

// Category icons
const categoryIcons = {
  "Electronics": "💻",
  "Vehicles": "🚗",
  "Collectibles & Art": "🎨",
  "Fashion": "👔",
  "Home & Garden": "🏠",
  "Sports & Outdoors": "⚽",
  "Toys & Games": "🎮",
  "Jewelry & Watches": "💎",
  "Musical Instruments": "🎸",
  "Books & Media": "📚",
  "Tools & Equipment": "🔧",
  "Other": "📦"
};

export default function Home() {
  const { isAuthenticated } = useAuth();
  const [featuredAuctions, setFeaturedAuctions] = useState([]);
  const [endingSoon, setEndingSoon] = useState([]);
  const [categories, setCategories] = useState({});
  const [popularKeywords, setPopularKeywords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [featuredRes, endingRes, catRes, keywordsRes] = await Promise.all([
        axios.get(`${API}/listings/featured`),
        axios.get(`${API}/listings/ending-soon`),
        axios.get(`${API}/categories`),
        axios.get(`${API}/popular-keywords`)
      ]);
      setFeaturedAuctions(featuredRes.data.listings || []);
      setEndingSoon(endingRes.data.listings || []);
      setCategories(catRes.data.categories || {});
      setPopularKeywords(keywordsRes.data.keywords || []);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />

      {/* Hero / Search Section */}
      <section className="bg-secondary text-white py-8 md:py-12" data-testid="hero-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-6">
            <h1 className="font-heading text-3xl md:text-4xl font-bold mb-2">
              Canada's Trusted Auction Platform
            </h1>
            <p className="text-gray-300">
              Buy and sell with confidence • BC Residents Only
            </p>
          </div>

          {/* One search bar only — it lives in the Navbar (client source L25) */}
          {/* Popular Keywords */}
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            <span className="text-gray-400 text-sm">Popular:</span>
            {popularKeywords.slice(0, 6).map((keyword) => (
              <Link
                key={keyword}
                to={`/auctions?q=${encodeURIComponent(keyword)}`}
                className="px-3 py-1 bg-white/10 text-white text-sm hover:bg-white/20 transition-colors"
              >
                {keyword}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="py-8 border-b border-border" data-testid="categories-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading text-xl font-bold">Browse Categories</h2>
            <Link to="/auctions" className="text-sm text-primary hover:underline flex items-center gap-1">
              View All <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2">
            {Object.keys(categories).map((cat) => (
              <Link
                key={cat}
                to={`/auctions?category=${encodeURIComponent(cat)}`}
                className="flex flex-col items-center p-3 bg-white border border-border hover:border-primary hover:shadow-sm transition-all text-center group"
                data-testid={`category-${cat.toLowerCase().replace(/\s+/g, '-')}`}
              >
                <span className="text-2xl mb-1">{categoryIcons[cat] || "📦"}</span>
                <span className="text-xs font-medium group-hover:text-primary transition-colors line-clamp-1">{cat}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Ending Soon - Hot Auctions */}
      {endingSoon.length > 0 && (
        <section className="py-8 bg-gradient-to-r from-primary/5 to-orange-50" data-testid="ending-soon">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Fire className="h-6 w-6 text-primary" weight="fill" />
                <h2 className="font-heading text-xl font-bold">Ending Soon</h2>
                <span className="px-2 py-0.5 bg-primary text-white text-xs font-bold rounded-full">
                  HOT
                </span>
              </div>
              <Link to="/auctions?sort=ending_soonest" className="text-sm text-primary hover:underline flex items-center gap-1">
                See All <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {endingSoon.slice(0, 6).map((auction) => (
                <AuctionCard key={auction._id} auction={auction} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Featured Auctions */}
      <section className="py-8" data-testid="featured-auctions">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Star className="h-6 w-6 text-yellow-500" weight="fill" />
              <h2 className="font-heading text-xl font-bold">Popular Right Now</h2>
            </div>
            <Link to="/auctions?sort=most_bids" className="text-sm text-primary hover:underline flex items-center gap-1">
              View All <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-muted animate-pulse aspect-square rounded" />
              ))}
            </div>
          ) : featuredAuctions.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {featuredAuctions.map((auction) => (
                <AuctionCard key={auction._id} auction={auction} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-muted rounded">
              <Gavel className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground mb-4">No active auctions yet. Be the first to list!</p>
              <Link
                to="/create-listing"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
              >
                Create Listing
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* How It Works */}
      <section className="py-12 bg-muted" data-testid="how-it-works">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="font-heading text-2xl font-bold text-center mb-8">How BidCa Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { icon: Users, title: "Create Account", desc: "Sign up with your BC postal code" },
              { icon: MagnifyingGlass, title: "Find Items", desc: "Search or browse categories" },
              { icon: Gavel, title: "Place Bids", desc: "Set your maximum, we bid for you" },
              { icon: Trophy, title: "Win & Meet", desc: "Chat with the seller and exchange in person" }
            ].map((step, i) => (
              <div key={i} className="text-center">
                <div className="w-16 h-16 bg-primary text-white rounded-full flex items-center justify-center mx-auto mb-4">
                  <step.icon className="h-8 w-8" weight="fill" />
                </div>
                <h3 className="font-bold mb-2">{step.title}</h3>
                <p className="text-sm text-muted-foreground">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why BidCa */}
      <section className="py-12" data-testid="features">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 border border-border">
              <ShieldCheck className="h-10 w-10 text-primary mb-4" weight="fill" />
              <h3 className="font-bold text-lg mb-2">Verified Sellers</h3>
              <p className="text-sm text-muted-foreground">
                All sellers are manually verified. Look for the verified badge for extra confidence.
              </p>
            </div>
            <div className="p-6 border border-border">
              <Lightning className="h-10 w-10 text-primary mb-4" weight="fill" />
              <h3 className="font-bold text-lg mb-2">Proxy Bidding</h3>
              <p className="text-sm text-muted-foreground">
                Set your max bid and we'll automatically bid for you up to that amount.
              </p>
            </div>
            <div className="p-6 border border-border">
              <Package className="h-10 w-10 text-primary mb-4" weight="fill" />
              <h3 className="font-bold text-lg mb-2">Local Exchange</h3>
              <p className="text-sm text-muted-foreground">
                Buyer and seller meet in BC and exchange directly. BidCa never handles your money.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      {!isAuthenticated && (
        <section className="py-12 bg-primary" data-testid="cta-section">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-heading text-2xl font-bold text-white mb-4">
              Ready to Start?
            </h2>
            <p className="text-white/80 mb-6">
              Join thousands of BC residents buying and selling on BidCa.ca
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/register"
                className="px-8 py-3 bg-white text-primary font-bold hover:bg-gray-100 transition-colors"
                data-testid="cta-register-btn"
              >
                Create Free Account
              </Link>
              <Link
                to="/auctions"
                className="px-8 py-3 border-2 border-white text-white font-bold hover:bg-white/10 transition-colors"
              >
                Browse Auctions
              </Link>
            </div>
          </div>
        </section>
      )}

      <Footer />
    </div>
  );
}
