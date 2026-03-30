import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import {
  Gavel,
  ShieldCheck,
  MapPin,
  Clock,
  ArrowRight,
  Users,
  Trophy,
  Handshake,
  Lightning
} from "@phosphor-icons/react";

// Countdown Timer Component
function CountdownTimer({ endTime }) {
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
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);
    return () => clearInterval(timer);
  }, [endTime]);

  if (timeLeft.ended) {
    return <span className="text-muted-foreground">Ended</span>;
  }

  const isUrgent = timeLeft.days === 0 && timeLeft.hours < 1;

  return (
    <div className={`font-mono tabular-nums ${isUrgent ? 'text-primary animate-bid-pulse' : 'text-foreground'}`}>
      {timeLeft.days > 0 && <span>{timeLeft.days}d </span>}
      <span>{String(timeLeft.hours).padStart(2, '0')}:</span>
      <span>{String(timeLeft.minutes).padStart(2, '0')}:</span>
      <span>{String(timeLeft.seconds).padStart(2, '0')}</span>
    </div>
  );
}

// Auction Card Component
function AuctionCard({ auction }) {
  return (
    <Link
      to={`/auctions/${auction._id}`}
      className="group auction-card block bg-white border border-border overflow-hidden"
      data-testid={`auction-card-${auction._id}`}
    >
      {/* Image */}
      <div className="relative aspect-[4/3] bg-muted overflow-hidden">
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
        
        {/* Live Badge */}
        <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 bg-primary text-white text-xs font-bold uppercase live-badge">
          <span className="w-1.5 h-1.5 bg-white rounded-full" />
          Live
        </div>

        {/* Verified Badge */}
        {auction.seller_verified && (
          <div className="absolute top-3 right-3 p-1.5 bg-secondary text-white">
            <ShieldCheck className="h-4 w-4" weight="fill" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-heading font-bold text-lg mb-2 line-clamp-1 group-hover:text-primary transition-colors">
          {auction.title}
        </h3>
        
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
          <MapPin className="h-4 w-4" />
          <span>{auction.city}</span>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-border">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Current Bid</p>
            <p className="font-heading font-bold text-xl bid-amount">${auction.current_bid?.toLocaleString()}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Ends In</p>
            <CountdownTimer endTime={auction.end_time} />
          </div>
        </div>

        <div className="mt-3 text-xs text-muted-foreground">
          {auction.bid_count || 0} bids
        </div>
      </div>
    </Link>
  );
}

// Categories
const CATEGORIES = [
  { name: "Electronics", icon: "💻" },
  { name: "Vehicles", icon: "🚗" },
  { name: "Furniture", icon: "🛋️" },
  { name: "Sports & Outdoors", icon: "⚽" },
  { name: "Jewelry & Watches", icon: "💎" },
  { name: "Collectibles & Art", icon: "🎨" },
];

export default function Home() {
  const { isAuthenticated } = useAuth();
  const [featuredAuctions, setFeaturedAuctions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFeaturedAuctions();
  }, []);

  const fetchFeaturedAuctions = async () => {
    try {
      const { data } = await axios.get(`${API}/listings/featured`);
      setFeaturedAuctions(data.listings || []);
    } catch (error) {
      console.error("Error fetching featured auctions:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* Hero Section */}
      <section 
        className="relative min-h-[600px] flex items-center"
        style={{
          backgroundImage: `url('https://static.prod-images.emergentagent.com/jobs/b315255c-ba1a-48ba-bb14-ed2debb047ec/images/d624dc5759685430fed48ed7924834b37f15fcdf2c0f8e61c948b8a98ba8b308.png')`,
          backgroundSize: 'cover',
          backgroundPosition: 'center'
        }}
        data-testid="hero-section"
      >
        <div className="absolute inset-0 hero-overlay" />
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-primary/20 border border-primary/30 text-primary mb-6">
              <MapPin className="h-4 w-4" weight="fill" />
              <span className="text-sm font-medium">Exclusively for British Columbia</span>
            </div>
            
            <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-black text-white uppercase tracking-tighter mb-6 animate-fade-in-up">
              Your Local
              <br />
              <span className="text-primary">Trusted</span> Auction
              <br />
              Platform
            </h1>
            
            <p className="text-lg text-gray-300 mb-8 max-w-lg animate-fade-in-up animation-delay-100">
              Buy and sell with confidence in your BC community. Verified sellers, secure bidding, and local transactions only.
            </p>
            
            <div className="flex flex-wrap gap-4 animate-fade-in-up animation-delay-200">
              <Link
                to="/auctions"
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-white font-bold hover:bg-primary/90 transition-colors"
                data-testid="browse-auctions-btn"
              >
                Browse Auctions
                <ArrowRight className="h-5 w-5" />
              </Link>
              {!isAuthenticated && (
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 px-6 py-3 bg-white text-secondary font-bold hover:bg-gray-100 transition-colors"
                  data-testid="start-selling-btn"
                >
                  Start Selling
                  <Gavel className="h-5 w-5" />
                </Link>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-white" data-testid="how-it-works">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="font-heading text-3xl sm:text-4xl font-bold mb-4">
              How It Works
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Simple, secure, and local. Start bidding or selling in minutes.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { icon: Users, title: "Sign Up", desc: "Create your BC-verified account" },
              { icon: ShieldCheck, title: "Get Verified", desc: "Upload your ID for trust badge" },
              { icon: Gavel, title: "Bid or List", desc: "Start buying or selling locally" },
              { icon: Handshake, title: "Connect", desc: "Meet locally and complete the deal" },
            ].map((step, i) => (
              <div key={i} className="text-center group">
                <div className="relative inline-flex items-center justify-center w-16 h-16 bg-muted mb-4 group-hover:bg-primary transition-colors">
                  <step.icon className="h-8 w-8 text-primary group-hover:text-white transition-colors" weight="fill" />
                  <span className="absolute -top-2 -right-2 w-6 h-6 bg-secondary text-white text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                </div>
                <h3 className="font-heading font-bold text-lg mb-2">{step.title}</h3>
                <p className="text-sm text-muted-foreground">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="py-20 bg-muted" data-testid="categories-section">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <h2 className="font-heading text-2xl sm:text-3xl font-bold">
              Browse Categories
            </h2>
            <Link
              to="/auctions"
              className="text-sm font-medium text-primary hover:underline flex items-center gap-1"
            >
              View All <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {CATEGORIES.map((cat) => (
              <Link
                key={cat.name}
                to={`/auctions?category=${encodeURIComponent(cat.name)}`}
                className="flex flex-col items-center justify-center p-6 bg-white border border-border hover:border-primary hover:-translate-y-1 transition-all"
                data-testid={`category-${cat.name.toLowerCase().replace(/\s+/g, '-')}`}
              >
                <span className="text-3xl mb-3">{cat.icon}</span>
                <span className="text-sm font-medium text-center">{cat.name}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Auctions */}
      <section className="py-20 bg-white" data-testid="featured-auctions">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="font-heading text-2xl sm:text-3xl font-bold mb-2">
                Featured Live Auctions
              </h2>
              <p className="text-muted-foreground">Hot items ending soon</p>
            </div>
            <Link
              to="/auctions"
              className="hidden sm:flex items-center gap-2 px-4 py-2 bg-secondary text-white font-medium hover:bg-secondary/90 transition-colors"
            >
              View All
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-muted animate-pulse aspect-[4/5]" />
              ))}
            </div>
          ) : featuredAuctions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {featuredAuctions.map((auction) => (
                <AuctionCard key={auction._id} auction={auction} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 bg-muted">
              <Gavel className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No active auctions yet. Be the first to list!</p>
              <Link
                to="/create-listing"
                className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
              >
                Create Listing
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </div>
      </section>

      {/* Why BidCa */}
      <section className="py-20 bg-secondary text-white" data-testid="why-bidca">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="font-heading text-3xl sm:text-4xl font-bold mb-6">
                Why Choose <span className="text-primary">BidCa</span>.ca?
              </h2>
              <div className="space-y-6">
                {[
                  { icon: MapPin, title: "Local Only", desc: "Exclusively for BC residents. No out-of-province scams." },
                  { icon: ShieldCheck, title: "Verified Sellers", desc: "Every seller is manually verified for your protection." },
                  { icon: Lightning, title: "Real-Time Bidding", desc: "Live updates. Never miss a winning bid." },
                  { icon: Trophy, title: "Trusted Community", desc: "Build your reputation with successful transactions." },
                ].map((item, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="flex-shrink-0 w-12 h-12 bg-primary/20 flex items-center justify-center">
                      <item.icon className="h-6 w-6 text-primary" weight="fill" />
                    </div>
                    <div>
                      <h3 className="font-bold mb-1">{item.title}</h3>
                      <p className="text-gray-400 text-sm">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <img
                src="https://images.unsplash.com/photo-1559511260-66a654ae982a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwyfHx2YW5jb3V2ZXIlMjBza3lsaW5lfGVufDB8fHx8MTc3NDg5NjE4MXww&ixlib=rb-4.1.0&q=85"
                alt="Vancouver Skyline"
                className="w-full aspect-[4/3] object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-secondary/80 to-transparent" />
              <div className="absolute bottom-6 left-6 right-6">
                <p className="font-heading text-2xl font-bold">
                  Proudly serving British Columbia
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      {!isAuthenticated && (
        <section className="py-16 bg-primary" data-testid="cta-section">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="font-heading text-2xl sm:text-3xl font-bold text-white mb-4">
              Ready to Start Bidding?
            </h2>
            <p className="text-white/80 mb-6">
              Join thousands of BC residents buying and selling locally.
            </p>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-8 py-4 bg-white text-secondary font-bold hover:bg-gray-100 transition-colors"
              data-testid="cta-register-btn"
            >
              Create Free Account
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </section>
      )}

      <Footer />
    </div>
  );
}
