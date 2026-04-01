import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import axios from "axios";
import { API, formatCAD } from "../App";
import Navbar from "../components/layout/Navbar";
import Footer from "../components/layout/Footer";
import {
  MagnifyingGlass,
  Funnel,
  MapPin,
  Gavel,
  ShieldCheck,
  Clock,
  X,
  CaretDown,
  CaretRight,
  Heart,
  Tag,
  Fire,
  SortAscending
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

  if (timeLeft.ended) return <span className="text-muted-foreground text-xs">Ended</span>;

  const isUrgent = timeLeft.days === 0 && timeLeft.hours < 1;

  return (
    <span className={`font-mono tabular-nums text-xs ${isUrgent ? 'text-primary font-bold animate-bid-pulse' : ''}`}>
      {timeLeft.days > 0 && `${timeLeft.days}d `}
      {String(timeLeft.hours).padStart(2, '0')}:
      {String(timeLeft.minutes).padStart(2, '0')}:
      {String(timeLeft.seconds).padStart(2, '0')}
    </span>
  );
}

// Auction Card
function AuctionCard({ listing }) {
  const isUrgent = listing.listing_type !== "fixed_price" && new Date(listing.end_time) - new Date() < 3600000;

  return (
    <Link
      to={`/auctions/${listing._id}`}
      className="group auction-card flex flex-col bg-white border border-border overflow-hidden hover:shadow-md transition-all"
      data-testid={`listing-card-${listing._id}`}
    >
      {/* Image */}
      <div className="relative aspect-square bg-muted overflow-hidden">
        {listing.images?.[0] ? (
          <img
            src={listing.images[0]}
            alt={listing.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Gavel className="h-10 w-10 text-muted-foreground" />
          </div>
        )}
        
        {/* Type badge */}
        <div className="absolute top-2 left-2 flex flex-col gap-1">
          {listing.listing_type === "fixed_price" ? (
            <span className="px-2 py-0.5 bg-green-600 text-white text-xs font-bold">BUY NOW</span>
          ) : isUrgent ? (
            <span className="px-2 py-0.5 bg-primary text-white text-xs font-bold flex items-center gap-1 live-badge">
              <Fire className="h-3 w-3" weight="fill" /> ENDING SOON
            </span>
          ) : (
            <span className="px-2 py-0.5 bg-secondary text-white text-xs font-bold">AUCTION</span>
          )}
          {listing.buy_it_now_price && listing.listing_type !== "fixed_price" && (
            <span className="px-2 py-0.5 bg-blue-600 text-white text-xs font-bold">BIN</span>
          )}
        </div>

        {listing.seller_verified && (
          <div className="absolute top-2 right-2 p-1 bg-white/90 rounded-full">
            <ShieldCheck className="h-4 w-4 text-primary" weight="fill" />
          </div>
        )}

        {listing.watchers_count > 0 && (
          <div className="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-0.5 bg-black/70 text-white text-xs">
            <Heart className="h-3 w-3" /> {listing.watchers_count}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 p-3 flex flex-col">
        <p className="text-xs text-muted-foreground mb-1">{listing.category}</p>
        <h3 className="font-medium text-sm mb-2 line-clamp-2 group-hover:text-primary transition-colors flex-1">
          {listing.title}
        </h3>
        
        <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
          <MapPin className="h-3 w-3" />
          <span>{listing.city}</span>
          <span>•</span>
          <span className="capitalize">{listing.condition?.replace('_', ' ')}</span>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <p className="text-xs text-muted-foreground">
              {listing.listing_type === "fixed_price" ? "Price" : `${listing.bid_count || 0} bids`}
            </p>
            <p className="font-bold bid-amount">
              {formatCAD(listing.listing_type === "fixed_price" ? listing.buy_it_now_price : listing.current_bid)}
            </p>
          </div>
          {listing.listing_type !== "fixed_price" && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">Time left</p>
              <CountdownTimer endTime={listing.end_time} />
            </div>
          )}
        </div>

        {listing.reserve_price && !listing.reserve_met && (
          <p className="text-xs text-yellow-600 mt-1">Reserve not met</p>
        )}
      </div>
    </Link>
  );
}

export default function BrowseAuctions() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [listings, setListings] = useState([]);
  const [categories, setCategories] = useState({});
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [expandedCats, setExpandedCats] = useState({});

  const [filters, setFilters] = useState({
    q: searchParams.get("q") || "",
    category: searchParams.get("category") || "",
    subcategory: searchParams.get("subcategory") || "",
    city: searchParams.get("city") || "",
    condition: searchParams.get("condition") || "",
    listing_type: searchParams.get("type") || "",
    min_price: searchParams.get("min_price") || "",
    max_price: searchParams.get("max_price") || "",
    free_shipping: searchParams.get("free_shipping") === "true",
    sort: searchParams.get("sort") || "ending_soonest",
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
      setCategories(data.categories || {});
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const fetchCities = async () => {
    try {
      const { data } = await axios.get(`${API}/cities`);
      setCities(data.cities || []);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  const fetchListings = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.q) params.append("q", filters.q);
      if (filters.category) params.append("category", filters.category);
      if (filters.subcategory) params.append("subcategory", filters.subcategory);
      if (filters.city) params.append("city", filters.city);
      if (filters.condition) params.append("condition", filters.condition);
      if (filters.listing_type) params.append("listing_type", filters.listing_type);
      if (filters.min_price) params.append("min_price", filters.min_price);
      if (filters.max_price) params.append("max_price", filters.max_price);
      if (filters.free_shipping) params.append("free_shipping", "true");
      params.append("sort", filters.sort);
      params.append("page", filters.page);
      params.append("status", "active");

      const { data } = await axios.get(`${API}/listings?${params}`);
      setListings(data.listings || []);
      setTotalPages(data.pages || 1);
      setTotal(data.total || 0);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const updateFilter = (key, value) => {
    const newFilters = { ...filters, [key]: value, page: 1 };
    setFilters(newFilters);
    
    const params = new URLSearchParams();
    Object.entries(newFilters).forEach(([k, v]) => {
      if (v && v !== false) params.set(k, v);
    });
    setSearchParams(params);
  };

  const clearFilters = () => {
    const newFilters = {
      q: "", category: "", subcategory: "", city: "", condition: "",
      listing_type: "", min_price: "", max_price: "", free_shipping: false,
      sort: "ending_soonest", page: 1
    };
    setFilters(newFilters);
    setSearchParams({});
  };

  const hasActiveFilters = filters.category || filters.city || filters.condition || 
    filters.listing_type || filters.min_price || filters.max_price || filters.free_shipping;

  const sortOptions = [
    { value: "ending_soonest", label: "Ending Soonest" },
    { value: "newly_listed", label: "Newly Listed" },
    { value: "lowest_price", label: "Lowest Price" },
    { value: "highest_price", label: "Highest Price" },
    { value: "most_bids", label: "Most Bids" }
  ];

  const conditions = [
    { value: "new", label: "New" },
    { value: "like_new", label: "Like New" },
    { value: "good", label: "Good" },
    { value: "fair", label: "Fair" },
    { value: "poor", label: "Poor" }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-muted">
      <Navbar />

      <div className="flex-1">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Search Bar */}
          <div className="bg-white border border-border p-4 mb-4">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search auctions..."
                  value={filters.q}
                  onChange={(e) => updateFilter("q", e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-input bg-background outline-none focus:border-primary"
                  data-testid="search-input"
                />
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`px-4 py-2 border flex items-center gap-2 ${showFilters ? 'bg-primary text-white border-primary' : 'border-input hover:border-primary'}`}
              >
                <Funnel className="h-5 w-5" />
                <span className="hidden sm:inline">Filters</span>
                {hasActiveFilters && <span className="w-2 h-2 bg-primary rounded-full" />}
              </button>
            </div>

            {/* Sort */}
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
              <p className="text-sm text-muted-foreground">
                {total.toLocaleString()} results
                {filters.q && <span> for "{filters.q}"</span>}
              </p>
              <div className="flex items-center gap-2">
                <SortAscending className="h-4 w-4 text-muted-foreground" />
                <select
                  value={filters.sort}
                  onChange={(e) => updateFilter("sort", e.target.value)}
                  className="text-sm border border-input py-1 px-2 bg-white outline-none focus:border-primary"
                  data-testid="sort-select"
                >
                  {sortOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="flex gap-6">
            {/* Filters Sidebar */}
            <aside className={`w-64 flex-shrink-0 ${showFilters ? 'block' : 'hidden lg:block'}`}>
              <div className="bg-white border border-border p-4 sticky top-20">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold">Filters</h3>
                  {hasActiveFilters && (
                    <button onClick={clearFilters} className="text-xs text-primary hover:underline">
                      Clear all
                    </button>
                  )}
                </div>

                {/* Categories */}
                <div className="mb-4 pb-4 border-b border-border">
                  <h4 className="font-medium text-sm mb-2">Category</h4>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {Object.entries(categories).map(([cat, subcats]) => (
                      <div key={cat}>
                        <button
                          onClick={() => {
                            setExpandedCats({ ...expandedCats, [cat]: !expandedCats[cat] });
                            if (filters.category !== cat) updateFilter("category", cat);
                          }}
                          className={`w-full flex items-center justify-between py-1 text-sm text-left hover:text-primary ${filters.category === cat ? 'text-primary font-medium' : ''}`}
                        >
                          <span className="truncate">{cat}</span>
                          {expandedCats[cat] ? <CaretDown className="h-3 w-3" /> : <CaretRight className="h-3 w-3" />}
                        </button>
                        {expandedCats[cat] && (
                          <div className="pl-3 space-y-1">
                            {subcats.map((sub) => (
                              <button
                                key={sub}
                                onClick={() => {
                                  updateFilter("category", cat);
                                  updateFilter("subcategory", sub);
                                }}
                                className={`block text-xs py-0.5 hover:text-primary ${filters.subcategory === sub ? 'text-primary font-medium' : 'text-muted-foreground'}`}
                              >
                                {sub}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Listing Type */}
                <div className="mb-4 pb-4 border-b border-border">
                  <h4 className="font-medium text-sm mb-2">Listing Type</h4>
                  <div className="space-y-2">
                    {[
                      { value: "", label: "All" },
                      { value: "auction", label: "Auction" },
                      { value: "auction_bin", label: "Auction + BIN" },
                      { value: "fixed_price", label: "Buy Now Only" }
                    ].map((opt) => (
                      <label key={opt.value} className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="radio"
                          name="listing_type"
                          checked={filters.listing_type === opt.value}
                          onChange={() => updateFilter("listing_type", opt.value)}
                          className="accent-primary"
                        />
                        {opt.label}
                      </label>
                    ))}
                  </div>
                </div>

                {/* Price Range */}
                <div className="mb-4 pb-4 border-b border-border">
                  <h4 className="font-medium text-sm mb-2">Price Range (CAD)</h4>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.min_price}
                      onChange={(e) => updateFilter("min_price", e.target.value)}
                      className="w-1/2 px-2 py-1 text-sm border border-input outline-none focus:border-primary"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.max_price}
                      onChange={(e) => updateFilter("max_price", e.target.value)}
                      className="w-1/2 px-2 py-1 text-sm border border-input outline-none focus:border-primary"
                    />
                  </div>
                </div>

                {/* Condition */}
                <div className="mb-4 pb-4 border-b border-border">
                  <h4 className="font-medium text-sm mb-2">Condition</h4>
                  <div className="space-y-2">
                    {conditions.map((c) => (
                      <label key={c.value} className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={filters.condition === c.value}
                          onChange={() => updateFilter("condition", filters.condition === c.value ? "" : c.value)}
                          className="accent-primary"
                        />
                        {c.label}
                      </label>
                    ))}
                  </div>
                </div>

                {/* Location */}
                <div className="mb-4 pb-4 border-b border-border">
                  <h4 className="font-medium text-sm mb-2">Location</h4>
                  <select
                    value={filters.city}
                    onChange={(e) => updateFilter("city", e.target.value)}
                    className="w-full text-sm border border-input py-1 px-2 bg-white outline-none focus:border-primary"
                  >
                    <option value="">All Cities</option>
                    {cities.map((city) => (
                      <option key={city} value={city}>{city}</option>
                    ))}
                  </select>
                </div>

                {/* Free Shipping */}
                <div>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.free_shipping}
                      onChange={(e) => updateFilter("free_shipping", e.target.checked)}
                      className="accent-primary"
                    />
                    Free Shipping Only
                  </label>
                </div>
              </div>
            </aside>

            {/* Results */}
            <main className="flex-1 min-w-0">
              {/* Active filters */}
              {hasActiveFilters && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {filters.category && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-border text-sm">
                      {filters.category}
                      <button onClick={() => { updateFilter("category", ""); updateFilter("subcategory", ""); }}>
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  )}
                  {filters.subcategory && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-border text-sm">
                      {filters.subcategory}
                      <button onClick={() => updateFilter("subcategory", "")}>
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  )}
                  {filters.condition && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-border text-sm capitalize">
                      {filters.condition.replace('_', ' ')}
                      <button onClick={() => updateFilter("condition", "")}>
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  )}
                  {filters.city && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-border text-sm">
                      {filters.city}
                      <button onClick={() => updateFilter("city", "")}>
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  )}
                  {(filters.min_price || filters.max_price) && (
                    <span className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-border text-sm">
                      {filters.min_price && `$${filters.min_price}`}
                      {filters.min_price && filters.max_price && " - "}
                      {filters.max_price && `$${filters.max_price}`}
                      <button onClick={() => { updateFilter("min_price", ""); updateFilter("max_price", ""); }}>
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  )}
                </div>
              )}

              {loading ? (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                    <div key={i} className="bg-white animate-pulse aspect-[3/4]" />
                  ))}
                </div>
              ) : listings.length === 0 ? (
                <div className="text-center py-16 bg-white border border-border">
                  <Gavel className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                  <h2 className="font-heading text-xl font-bold mb-2">No auctions found</h2>
                  <p className="text-muted-foreground mb-4">Try adjusting your filters</p>
                  {hasActiveFilters && (
                    <button onClick={clearFilters} className="px-4 py-2 bg-primary text-white font-medium">
                      Clear Filters
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {listings.map((listing) => (
                      <AuctionCard key={listing._id} listing={listing} />
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex justify-center gap-2 mt-8">
                      {Array.from({ length: Math.min(totalPages, 10) }, (_, i) => i + 1).map((page) => (
                        <button
                          key={page}
                          onClick={() => updateFilter("page", page)}
                          className={`w-10 h-10 font-medium transition-colors ${
                            filters.page === page
                              ? "bg-primary text-white"
                              : "bg-white border border-border hover:border-primary"
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                      {totalPages > 10 && <span className="px-2 py-2">...</span>}
                    </div>
                  )}
                </>
              )}
            </main>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
