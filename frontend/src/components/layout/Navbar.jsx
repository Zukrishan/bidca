import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth, API } from "../../App";
import axios from "axios";
import {
  Gavel,
  SignOut,
  House,
  MagnifyingGlass,
  Bell,
  Plus,
  ShieldCheck,
  Gear,
  Heart,
  User,
  Tag,
  CaretDown,
  List
} from "@phosphor-icons/react";

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (isAuthenticated) {
      fetchNotifications();
    }
  }, [isAuthenticated]);

  const fetchNotifications = async () => {
    try {
      const { data } = await axios.get(`${API}/notifications?limit=1`);
      setUnreadCount(data.unread_count || 0);
    } catch (error) {
      // Ignore errors
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/auctions?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-border shadow-sm" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-1.5 flex-shrink-0" data-testid="logo-link">
            <Gavel className="h-7 w-7 text-primary" weight="fill" />
            <span className="font-heading font-bold text-lg tracking-tight">
              <span className="text-primary">Bid</span>
              <span className="text-secondary">Ca</span>
              <span className="text-muted-foreground text-sm">.ca</span>
            </span>
          </Link>

          {/* Search Bar - Desktop */}
          <form onSubmit={handleSearch} className="hidden md:flex flex-1 max-w-xl mx-6">
            <div className="flex w-full">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search auctions..."
                className="flex-1 px-4 py-2 border border-r-0 border-input outline-none focus:border-primary text-sm"
                data-testid="nav-search"
              />
              <button
                type="submit"
                className="px-4 bg-primary text-white hover:bg-primary/90 transition-colors"
              >
                <MagnifyingGlass className="h-5 w-5" />
              </button>
            </div>
          </form>

          {/* Right Side */}
          <div className="flex items-center gap-2">
            {/* Browse Link */}
            <Link
              to="/auctions"
              className="hidden sm:flex items-center gap-1 px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              data-testid="browse-link"
            >
              <List className="h-4 w-4" />
              Browse
            </Link>

            {isAuthenticated ? (
              <>
                {/* Sell Button */}
                <Link
                  to="/create-listing"
                  className="hidden sm:flex items-center gap-1 px-3 py-2 bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
                  data-testid="sell-btn"
                >
                  <Plus className="h-4 w-4" />
                  Sell
                </Link>

                {/* Watchlist */}
                <Link
                  to="/watchlist"
                  className="p-2 text-muted-foreground hover:text-primary transition-colors"
                  data-testid="watchlist-link"
                >
                  <Heart className="h-5 w-5" />
                </Link>

                {/* Notifications */}
                <Link
                  to="/dashboard"
                  className="relative p-2 text-muted-foreground hover:text-primary transition-colors"
                  data-testid="notifications-link"
                >
                  <Bell className="h-5 w-5" />
                  {unreadCount > 0 && (
                    <span className="absolute top-0 right-0 w-4 h-4 bg-primary text-white text-xs rounded-full flex items-center justify-center">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  )}
                </Link>

                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center gap-2 p-2 hover:bg-muted rounded transition-colors"
                    data-testid="user-menu-btn"
                  >
                    <div className="w-8 h-8 bg-secondary text-white flex items-center justify-center font-bold text-sm">
                      {user?.full_name?.charAt(0) || 'U'}
                    </div>
                    {user?.verification_badge && (
                      <ShieldCheck className="h-4 w-4 text-primary" weight="fill" />
                    )}
                    <CaretDown className="h-4 w-4 text-muted-foreground" />
                  </button>

                  {showUserMenu && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setShowUserMenu(false)}
                      />
                      <div className="absolute right-0 mt-2 w-56 bg-white border border-border shadow-lg z-50">
                        <div className="p-3 border-b border-border">
                          <p className="font-medium truncate">{user?.full_name}</p>
                          <p className="text-sm text-muted-foreground truncate">{user?.email}</p>
                        </div>
                        <div className="py-2">
                          <Link
                            to="/dashboard"
                            onClick={() => setShowUserMenu(false)}
                            className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors"
                          >
                            <House className="h-4 w-4" />
                            Dashboard
                          </Link>
                          <Link
                            to="/seller"
                            onClick={() => setShowUserMenu(false)}
                            className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors"
                          >
                            <Tag className="h-4 w-4" />
                            Seller Dashboard
                          </Link>
                          <Link
                            to="/watchlist"
                            onClick={() => setShowUserMenu(false)}
                            className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors"
                          >
                            <Heart className="h-4 w-4" />
                            Watchlist
                          </Link>
                          <Link
                            to="/verification"
                            onClick={() => setShowUserMenu(false)}
                            className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors"
                          >
                            <ShieldCheck className="h-4 w-4" />
                            Verification
                          </Link>
                          {user?.role === "admin" && (
                            <Link
                              to="/admin"
                              onClick={() => setShowUserMenu(false)}
                              className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted transition-colors"
                            >
                              <Gear className="h-4 w-4" />
                              Admin Panel
                            </Link>
                          )}
                        </div>
                        <div className="border-t border-border py-2">
                          <button
                            onClick={() => {
                              logout();
                              setShowUserMenu(false);
                            }}
                            className="flex items-center gap-2 px-3 py-2 text-sm w-full text-left hover:bg-muted transition-colors text-destructive"
                          >
                            <SignOut className="h-4 w-4" />
                            Sign Out
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  data-testid="login-link"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-3 py-2 bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
                  data-testid="register-link"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Search */}
      <div className="md:hidden px-4 pb-3">
        <form onSubmit={handleSearch} className="flex">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search auctions..."
            className="flex-1 px-3 py-2 border border-r-0 border-input outline-none focus:border-primary text-sm"
          />
          <button
            type="submit"
            className="px-3 bg-primary text-white"
          >
            <MagnifyingGlass className="h-5 w-5" />
          </button>
        </form>
      </div>
    </nav>
  );
}
