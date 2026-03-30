import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../App";
import {
  Gavel,
  User,
  SignOut,
  List,
  House,
  MagnifyingGlass,
  Bell,
  Plus,
  ShieldCheck,
  Gear
} from "@phosphor-icons/react";

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();

  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-border" data-testid="navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2" data-testid="logo-link">
            <div className="flex items-center">
              <Gavel className="h-8 w-8 text-primary" weight="fill" />
              <span className="font-heading font-bold text-xl tracking-tight">
                <span className="text-primary">Bid</span>
                <span className="text-secondary">Ca</span>
                <span className="text-muted-foreground">.ca</span>
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
            <Link
              to="/auctions"
              className="flex items-center gap-1.5 text-sm font-medium text-foreground hover:text-primary transition-colors"
              data-testid="browse-auctions-link"
            >
              <MagnifyingGlass className="h-4 w-4" />
              Browse Auctions
            </Link>
            
            {isAuthenticated && (
              <>
                <Link
                  to="/create-listing"
                  className="flex items-center gap-1.5 text-sm font-medium text-foreground hover:text-primary transition-colors"
                  data-testid="create-listing-link"
                >
                  <Plus className="h-4 w-4" />
                  Sell Item
                </Link>
                <Link
                  to="/dashboard"
                  className="flex items-center gap-1.5 text-sm font-medium text-foreground hover:text-primary transition-colors"
                  data-testid="dashboard-link"
                >
                  <House className="h-4 w-4" />
                  Dashboard
                </Link>
              </>
            )}
          </div>

          {/* Right Side */}
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                {/* Notifications */}
                <Link
                  to="/dashboard"
                  className="relative p-2 text-foreground hover:text-primary transition-colors"
                  data-testid="notifications-btn"
                >
                  <Bell className="h-5 w-5" />
                </Link>

                {/* User Menu */}
                <div className="flex items-center gap-3">
                  {user?.verification_badge && (
                    <ShieldCheck className="h-5 w-5 text-primary" weight="fill" />
                  )}
                  <span className="hidden sm:block text-sm font-medium">
                    {user?.full_name?.split(" ")[0]}
                  </span>
                  
                  {user?.role === "admin" && (
                    <Link
                      to="/admin"
                      className="p-2 text-foreground hover:text-primary transition-colors"
                      data-testid="admin-link"
                    >
                      <Gear className="h-5 w-5" />
                    </Link>
                  )}
                  
                  <button
                    onClick={logout}
                    className="p-2 text-foreground hover:text-primary transition-colors"
                    data-testid="logout-btn"
                  >
                    <SignOut className="h-5 w-5" />
                  </button>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  to="/login"
                  className="text-sm font-medium text-foreground hover:text-primary transition-colors"
                  data-testid="login-link"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="px-4 py-2 bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
                  data-testid="register-link"
                >
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
