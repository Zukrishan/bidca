import React from "react";
import { Link } from "react-router-dom";
import { MapPin, EnvelopeSimple } from "@phosphor-icons/react";

export default function Footer() {
  return (
    <footer className="bg-secondary text-white" data-testid="footer">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <img src="/logo_bidca.jpeg" alt="BidCa.ca" className="h-10 brightness-0 invert" />
            </div>
            <p className="text-gray-400 text-sm mb-4 max-w-sm">
              British Columbia's trusted local auction platform. Buy and sell with confidence in your community.
            </p>
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <MapPin className="h-4 w-4" />
              <span>Exclusively serving British Columbia</span>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-heading font-bold text-sm uppercase tracking-wider mb-4">
              Quick Links
            </h4>
            <ul className="space-y-2">
              <li>
                <Link to="/auctions" className="text-gray-400 hover:text-white text-sm transition-colors">
                  Browse Auctions
                </Link>
              </li>
              <li>
                <Link to="/create-listing" className="text-gray-400 hover:text-white text-sm transition-colors">
                  Start Selling
                </Link>
              </li>
              <li>
                <Link to="/verification" className="text-gray-400 hover:text-white text-sm transition-colors">
                  Get Verified
                </Link>
              </li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="font-heading font-bold text-sm uppercase tracking-wider mb-4">
              Support
            </h4>
            <ul className="space-y-2">
              <li>
                <a href="#" className="text-gray-400 hover:text-white text-sm transition-colors">
                  How It Works
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-400 hover:text-white text-sm transition-colors">
                  Safety Tips
                </a>
              </li>
              <li>
                <a href="#" className="text-gray-400 hover:text-white text-sm transition-colors">
                  Contact Us
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 mt-8 pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-gray-500 text-sm">
            © {new Date().getFullYear()} BidCa.ca. All rights reserved.
          </p>
          <p className="text-gray-500 text-sm">
            Made with pride in British Columbia 🍁
          </p>
        </div>
      </div>
    </footer>
  );
}
