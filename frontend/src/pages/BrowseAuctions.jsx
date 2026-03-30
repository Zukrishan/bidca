import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { API } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import {
  MagnifyingGlass,
  Funnel,
  MapPin,
  Gavel,
  ShieldCheck,
  Clock,
  X
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

  const isUrgent = timeLeft.days === 0 && timeLeft.hours < 1;

  return (
    <span className={`font-mono tabular-nums ${isUrgent ? 'text-primary animate-bid-pulse' : ''}`}>
      {timeLeft.days > 0 && `${timeLeft.days}d `}
      {String(timeLeft.hours).padStart(2, '0')}:
      {String(timeLeft.minutes).padStart(2, '0')}:
      {String(timeLeft.seconds).padStart(2, '0')}
    </span>
  );
}

export default function BrowseAuctions() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [listings, setListings] = useState([]);
  const [categories, setCategories] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalPages, setTotalPages] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  const [filters, setFilters] = useState({
    search: searchParams.get("search") || "",
    category: searchParams.get("category") || "",
    city: searchParams.get("city") || "",
    listing_type: searchParams.get("type") || "",
    page: parseInt(searchParams.get("page")) || 1
  });

  useEffect(() => {
    fetchCategories();
    fetchCities();
  }, []);

  useEffect(() => {
    fetchListings();
  }, [filters]);

  const fetchCategories = async () => {
    try {
      const { data } = await axios.get(`${API}/categories`);
      setCategories(data.categories || []);
    } catch (error) {
      console.error("Error fetching categories:", error);
    }
  };

  const fetchCities = async () => {
    try {
      const { data } = await axios.get(`${API}/cities`);
      setCities(data.cities || []);
    } catch (error) {
      console.error("Error fetching cities:", error);
    }
  };

  const fetchListings = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.search) params.append("search", filters.search);
      if (filters.category) params.append("category", filters.category);
      if (filters.city) params.append("city", filters.city);
      if (filters.listing_type) params.append("listing_type", filters.listing_type);
      params.append("page", filters.page);
      params.append("status", "active");

      const { data } = await axios.get(`${API}/listings?${params}`);
      setListings(data.listings || []);
      setTotalPages(data.pages || 1);
    } catch (error) {
      console.error("Error fetching listings:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateFilter = (key, value) => {
    const newFilters = { ...filters, [key]: value, page: 1 };
    setFilters(newFilters);
    
    const params = new URLSearchParams();
    Object.entries(newFilters).forEach(([k, v]) => {
      if (v) params.set(k, v);
    });
    setSearchParams(params);
  };

  const clearFilters = () => {
    const newFilters = { search: "", category: "", city: "", listing_type: "", page: 1 };
    setFilters(newFilters);
    setSearchParams({});
  };

  const hasActiveFilters = filters.category || filters.city || filters.listing_type;

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="font-heading text-3xl font-bold mb-2" data-testid="browse-title">
              Browse Auctions
            </h1>
            <p className="text-muted-foreground">
              Find great deals from verified BC sellers
            </p>
          </div>

          {/* Search & Filters */}
          <div className="bg-white border border-border p-4 mb-6">
            <div className="flex flex-col md:flex-row gap-4">
              {/* Search */}
              <div className="flex-1 relative">
                <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search auctions..."
                  value={filters.search}
                  onChange={(e) => updateFilter("search", e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-input bg-background focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                  data-testid="search-input"
                />
              </div>

              {/* Filter Toggle (Mobile) */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="md:hidden px-4 py-3 border border-input flex items-center justify-center gap-2"
              >
                <Funnel className="h-5 w-5" />
                Filters
                {hasActiveFilters && (
                  <span className="w-2 h-2 bg-primary rounded-full" />
                )}
              </button>

              {/* Desktop Filters */}
              <div className="hidden md:flex gap-4">
                <select
                  value={filters.category}
                  onChange={(e) => updateFilter("category", e.target.value)}
                  className="px-4 py-3 border border-input bg-background focus:border-primary outline-none min-w-[150px]"
                  data-testid="category-filter"
                >
                  <option value="">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>

                <select
                  value={filters.city}
                  onChange={(e) => updateFilter("city", e.target.value)}
                  className="px-4 py-3 border border-input bg-background focus:border-primary outline-none min-w-[150px]"
                  data-testid="city-filter"
                >
                  <option value="">All Cities</option>
                  {cities.map((city) => (
                    <option key={city} value={city}>{city}</option>
                  ))}
                </select>

                <select
                  value={filters.listing_type}
                  onChange={(e) => updateFilter("listing_type", e.target.value)}
                  className="px-4 py-3 border border-input bg-background focus:border-primary outline-none min-w-[150px]"
                  data-testid="type-filter"
                >
                  <option value="">All Types</option>
                  <option value="auction">Auctions</option>
                  <option value="marketplace">Marketplace</option>
                </select>
              </div>
            </div>

            {/* Mobile Filters */}
            {showFilters && (
              <div className="md:hidden mt-4 pt-4 border-t border-border space-y-4">
                <select
                  value={filters.category}
                  onChange={(e) => updateFilter("category", e.target.value)}
                  className="w-full px-4 py-3 border border-input bg-background"
                >
                  <option value="">All Categories</option>
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>

                <select
                  value={filters.city}
                  onChange={(e) => updateFilter("city", e.target.value)}
                  className="w-full px-4 py-3 border border-input bg-background"
                >
                  <option value="">All Cities</option>
                  {cities.map((city) => (
                    <option key={city} value={city}>{city}</option>
                  ))}
                </select>

                <select
                  value={filters.listing_type}
                  onChange={(e) => updateFilter("listing_type", e.target.value)}
                  className="w-full px-4 py-3 border border-input bg-background"
                >
                  <option value="">All Types</option>
                  <option value="auction">Auctions</option>
                  <option value="marketplace">Marketplace</option>
                </select>
              </div>
            )}

            {/* Active Filters */}
            {hasActiveFilters && (
              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                <span className="text-sm text-muted-foreground">Active filters:</span>
                {filters.category && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-muted text-sm">
                    {filters.category}
                    <button onClick={() => updateFilter("category", "")}>
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.city && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-muted text-sm">
                    {filters.city}
                    <button onClick={() => updateFilter("city", "")}>
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                )}
                {filters.listing_type && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-muted text-sm">
                    {filters.listing_type}
                    <button onClick={() => updateFilter("listing_type", "")}>
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                )}
                <button
                  onClick={clearFilters}
                  className="text-sm text-primary hover:underline"
                >
                  Clear all
                </button>
              </div>
            )}
          </div>

          {/* Results */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="bg-muted animate-pulse aspect-[4/5]" />
              ))}
            </div>
          ) : listings.length === 0 ? (
            <div className="text-center py-16 bg-white border border-border">
              <Gavel className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
              <h2 className="font-heading text-xl font-bold mb-2">No auctions found</h2>
              <p className="text-muted-foreground mb-4">
                Try adjusting your filters or search terms
              </p>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="px-4 py-2 bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {listings.map((listing) => (
                  <Link
                    key={listing._id}
                    to={`/auctions/${listing._id}`}
                    className="group auction-card block bg-white border border-border overflow-hidden"
                    data-testid={`listing-card-${listing._id}`}
                  >
                    {/* Image */}
                    <div className="relative aspect-[4/3] bg-muted overflow-hidden">
                      {listing.images?.[0] ? (
                        <img
                          src={listing.images[0]}
                          alt={listing.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Gavel className="h-12 w-12 text-muted-foreground" />
                        </div>
                      )}
                      
                      {listing.listing_type === "auction" && (
                        <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 bg-primary text-white text-xs font-bold uppercase live-badge">
                          <span className="w-1.5 h-1.5 bg-white rounded-full" />
                          Live
                        </div>
                      )}

                      {listing.listing_type === "marketplace" && (
                        <div className="absolute top-3 left-3 px-2 py-1 bg-secondary text-white text-xs font-bold uppercase">
                          Buy Now
                        </div>
                      )}

                      {listing.seller_verified && (
                        <div className="absolute top-3 right-3 p-1.5 bg-secondary text-white">
                          <ShieldCheck className="h-4 w-4" weight="fill" />
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="p-4">
                      <div className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                        {listing.category}
                      </div>
                      <h3 className="font-heading font-bold text-lg mb-2 line-clamp-1 group-hover:text-primary transition-colors">
                        {listing.title}
                      </h3>
                      
                      <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                        <MapPin className="h-4 w-4" />
                        <span>{listing.city}</span>
                      </div>

                      <div className="flex items-center justify-between pt-3 border-t border-border">
                        <div>
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                            {listing.listing_type === "auction" ? "Current Bid" : "Price"}
                          </p>
                          <p className="font-heading font-bold text-xl bid-amount">
                            ${(listing.listing_type === "auction" ? listing.current_bid : listing.fixed_price)?.toLocaleString()}
                          </p>
                        </div>
                        {listing.listing_type === "auction" && (
                          <div className="text-right">
                            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Ends In</p>
                            <CountdownTimer endTime={listing.end_time} />
                          </div>
                        )}
                      </div>

                      <div className="mt-3 text-xs text-muted-foreground">
                        {listing.bid_count || 0} bids
                      </div>
                    </div>
                  </Link>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-8">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => updateFilter("page", page)}
                      className={`w-10 h-10 font-medium transition-colors ${
                        filters.page === page
                          ? "bg-primary text-white"
                          : "bg-white border border-border hover:border-primary"
                      }`}
                      data-testid={`page-${page}`}
                    >
                      {page}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}
