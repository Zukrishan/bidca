# BidCa.ca - Product Requirements Document

## Overview
**BidCa.ca** is a Local Online Bidding Platform exclusively for British Columbia (BC) residents. The platform enables trusted, local auctions and marketplace transactions with a focus on fraud reduction through manual verification.

## Original Problem Statement
Build a Local Online Bidding Platform (BC Only) with:
- Auction listings with timed bidding
- Marketplace direct purchase option
- User verification system
- Admin panel for listing approval and user management
- Real-time WebSocket bidding updates
- BC postal code validation

## User Choices
- **Auth**: JWT-based custom auth
- **Real-time**: WebSocket for live bid updates
- **Images**: Cloudinary (MOCK - needs real credentials)
- **Email**: SendGrid (MOCK - needs real credentials)
- **Design**: Red (#E31B23), Black (#1A1A1A), Grey (#808080) - Canadian maple leaf theme

---

## Architecture

### Tech Stack
- **Frontend**: React 19, Tailwind CSS, Radix UI, Socket.io-client
- **Backend**: FastAPI (Python), Motor (MongoDB async driver)
- **Database**: MongoDB
- **Real-time**: Socket.IO
- **Image Upload**: Cloudinary (MOCK)
- **Email**: SendGrid (MOCK)

### Database Collections
- `users` - User accounts with verification status
- `listings` - Auction and marketplace listings
- `bids` - Bid history for auctions
- `notifications` - User notifications
- `verifications` - ID verification submissions
- `reports` - Listing reports
- `messages` - Seller-buyer communication
- `login_attempts` - Brute force protection

---

## User Personas

### 1. Buyer (BC Resident)
- Browse active auctions and marketplace listings
- Place bids on auctions
- Track bid status and notifications
- Communicate with sellers after winning

### 2. Seller (BC Resident)
- Create auction or marketplace listings
- Track listing performance
- Communicate with buyers
- Get verified for trust badge

### 3. Admin
- Approve/reject pending listings
- Review verification submissions
- Manage users (suspend/ban)
- View platform statistics
- Handle reports

---

## Core Requirements

### Authentication (✅ Implemented)
- Email/password registration with BC postal code validation
- JWT tokens with httpOnly cookies
- Brute force protection (5 attempts = 15 min lockout)
- Admin seeding on startup

### Listings (✅ Implemented)
- Auction listings (24h, 48h, 72h duration)
- Marketplace listings (fixed price)
- Admin approval required before going live
- Multi-image upload (up to 10)
- Category and city filters

### Bidding (✅ Implemented)
- Real-time bid updates via WebSocket
- Minimum bid enforcement (current + increment)
- Bid history (masked usernames)
- Auto-close at auction end time

### Verification (✅ Implemented)
- Government ID upload
- Selfie with ID upload
- Admin review process
- Verification badge on approval

### Admin Panel (✅ Implemented)
- Dashboard with statistics
- Listing approval/rejection
- User management (suspend/ban)
- Verification review
- Report management

---

## What's Been Implemented (Jan 30, 2026)

### Backend
- ✅ Complete auth system with JWT and httpOnly cookies
- ✅ BC postal code validation (V prefix)
- ✅ Full CRUD for listings
- ✅ Bidding system with WebSocket
- ✅ Notification system
- ✅ Verification submission and review
- ✅ Admin panel API endpoints
- ✅ Brute force protection
- ✅ Admin seeding

### Frontend
- ✅ Home page with hero, how it works, categories, featured auctions
- ✅ Registration with BC postal code validation
- ✅ Login page
- ✅ User Dashboard (bids, notifications)
- ✅ Browse Auctions with search/filters
- ✅ Auction Detail with real-time bidding
- ✅ Create Listing page
- ✅ Seller Dashboard
- ✅ Verification page
- ✅ Admin Panel (all tabs)
- ✅ Responsive design
- ✅ Swiss high-contrast design theme

---

## Prioritized Backlog

### P0 (Critical - Needed for Production)
- [ ] Real Cloudinary integration (replace mock)
- [ ] Real SendGrid integration (replace mock)
- [ ] Auction auto-end background task
- [ ] Winner notification system

### P1 (High Priority)
- [ ] Password reset flow (forgot password)
- [ ] Email verification on registration
- [ ] Auction winner page with seller contact
- [ ] Message system for auction winners

### P2 (Medium Priority)
- [ ] User profile page
- [ ] Second bidder fallback logic
- [ ] Purchase failure tracking (3 failures = ban)
- [ ] Advanced search (price range, date)

### P3 (Future Enhancements)
- [ ] Mobile app
- [ ] Integrated payment processing (Stripe)
- [ ] Automated ID verification (third-party)
- [ ] AI fraud detection
- [ ] Social features (following sellers)

---

## Test Credentials
See `/app/memory/test_credentials.md`

---

## API Documentation

### Auth Endpoints
- `POST /api/auth/register` - Register (BC postal codes only)
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user
- `POST /api/auth/refresh` - Refresh access token

### Listing Endpoints
- `GET /api/listings` - Browse listings
- `GET /api/listings/featured` - Featured auctions
- `GET /api/listings/{id}` - Listing detail
- `POST /api/listings` - Create listing
- `POST /api/listings/{id}/bid` - Place bid
- `POST /api/listings/{id}/report` - Report listing

### Admin Endpoints
- `GET /api/admin/stats` - Dashboard stats
- `GET /api/admin/listings` - Manage listings
- `PUT /api/admin/listings/{id}` - Update listing status
- `GET /api/admin/users` - Manage users
- `PUT /api/admin/users/{id}` - Update user
- `GET /api/admin/verifications` - Review verifications
- `PUT /api/admin/verifications/{id}` - Approve/reject

---

## Notes
- Cloudinary and SendGrid are currently MOCKED
- WebSocket path: `/api/socket.io`
- All listings require admin approval before going live
- Only BC postal codes (starting with V) are accepted
