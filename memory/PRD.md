# BidCa.ca - Product Requirements Document

## Overview
**BidCa.ca** is a Local Online Bidding Platform exclusively for British Columbia (BC) residents, modeled after Yahoo Japan Auctions but adapted for Canadian users.

## Original Problem Statement
Build a full-featured online auction platform for bidca.ca with:
- Auction listings with timed bidding, proxy/automatic bidding, sniper bids
- Buy It Now (BIN) and Fixed Price listings
- Watchlists, seller feedback/ratings
- Advanced search/filters, category browsing
- Admin panel with listing approval, user management, stats
- Real-time WebSocket bidding updates
- BC postal code validation

## User Choices
- **Auth**: JWT-based custom auth
- **Real-time**: WebSocket for live bid updates
- **Images**: Cloudinary (MOCKED - user explicitly requested mock)
- **Email**: SendGrid (MOCKED - user explicitly requested mock)
- **Design**: Red (#E31B23), Black (#1A1A1A), Grey (#808080) - Canadian maple leaf theme
- **Logo**: Custom BidCa.ca logo (uploaded by user, stored at /frontend/public/logo_bidca.jpeg)
- **Platform Fee**: Free for now (no 10% fee)

---

## Architecture

### Tech Stack
- **Frontend**: React 19, Tailwind CSS, Radix UI, Socket.io-client, Phosphor Icons
- **Backend**: FastAPI (Python), Motor (MongoDB async driver)
- **Database**: MongoDB
- **Real-time**: Socket.IO (python-socketio)
- **Image Upload**: Cloudinary (MOCKED)
- **Email**: SendGrid (MOCKED)

### Database Collections
- `users` - User accounts with verification status
- `listings` - Auction and marketplace listings
- `bids` - Bid history for auctions
- `notifications` - User notifications
- `verifications` - ID verification submissions
- `reports` - Listing reports
- `messages` - Seller-buyer communication
- `login_attempts` - Brute force protection
- `transactions` - Completed transactions (for GMV tracking)
- `watchlists` - User watchlists

---

## What's Been Implemented

### Core Features (Complete)
- Complete auth system with JWT and httpOnly cookies
- BC postal code validation (V prefix)
- Full CRUD for listings (auction + fixed price + BIN)
- Proxy/automatic bidding with bid increments
- Sniper bid feature
- Buy It Now (BIN) & Fixed Price
- Watchlist integration and UI
- Seller rating and feedback display
- Advanced filtering and categories
- Real-time bidding via WebSocket
- Notification system
- Verification submission and review
- Admin Panel with all tabs (Dashboard, Listings, Users, Verifications, Reports)
- Swiss high-contrast design theme
- Custom BidCa.ca logo in Navbar and Footer

### Admin Dashboard Stats
- Total Users, Total Listings, Active Auctions
- Pending Listings, Pending Verifications, Total Bids
- Gross Merchandise Value (GMV)
- Platform Fee (currently Free)
- Pending Reports

### Bug Fixes Applied
- Brute force protection returns 429 on 5th attempt (was 401)
- KeyError 'max_bid' in /api/users/me/bids fixed
- Rate limiting uses email-only identifier (proxy IP rotation issue)

---

## Prioritized Backlog

### P1 (High Priority - Upcoming)
- [ ] English/French bilingual support (Canadian compliance)
- [ ] "Best Offer" option (buyers submit offers below listed price)
- [ ] Relist unsold items with one click from Seller Dashboard
- [ ] Sales fee structure (flat 10% when enabled)

### P2 (Medium Priority)
- [ ] Buyer protection program details (UI pages)
- [ ] Purchase history with order tracking
- [ ] Saved searches with notifications
- [ ] Identity verification via SMS/email (currently mocked)
- [ ] Escrow/Payment Gateway (Stripe/PayPal)

### P3 (Future)
- [ ] Real Cloudinary integration (replace mock)
- [ ] Real SendGrid integration (replace mock)
- [ ] Mobile app
- [ ] AI fraud detection
- [ ] Social features (following sellers)

### Refactoring
- [ ] Break server.py into modular FastAPI routers

---

## Test Credentials
See `/app/memory/test_credentials.md`

## Key API Endpoints
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register (BC postal codes only)
- `GET /api/listings` - Browse listings (with filters)
- `GET /api/listings/{id}` - Listing detail
- `POST /api/listings/{id}/bid` - Place bid (proxy logic)
- `POST /api/listings/{id}/snipe` - Sniper bid
- `GET /api/admin/stats` - Dashboard stats (GMV, reports, etc.)
- `GET /api/admin/listings` - Manage listings
- `GET /api/admin/users` - Manage users

## Notes
- Cloudinary and SendGrid are MOCKED (user request)
- WebSocket path: `/api/socket.io`
- All listings require admin approval
- Only BC postal codes (starting with V) accepted
- Platform fee is FREE for now
