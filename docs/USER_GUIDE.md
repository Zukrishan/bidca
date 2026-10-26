> Imported from `origin/v10:DOCUMENTATION.md` (last updated 3 Apr 2026). Rank 6 — describes the prototype, not a spec. Endpoint names here may drift; `docs/API_CONTRACT.md` wins.
> **26 Oct 2026:** the client source `docs/source/BIDCA.txt` changes several things described below — 12 h login lockout (not 15 min), phone-based verified badge, no shipping, no payment of any kind, ratings only after both sides complete. See `docs/srs/02-functional.md`; rewrite this guide when Phase 9 ships.

# BidCa.ca — Platform Documentation

## What is BidCa.ca?
BidCa.ca is an online auction and marketplace platform exclusively for British Columbia (BC) residents. Think of it as a Canadian version of Yahoo Japan Auctions — users can list items for auction or fixed-price sale, place bids, and buy items with confidence.

---

## Getting Started

### 1. Create an Account
- Go to **Register** page
- Enter your email, full name, password, city, and **BC postal code** (must start with "V", e.g., V6B1A1)
- Only BC residents can register

### 2. Log In
- Use your email and password
- After 5 failed attempts, your account is locked for 15 minutes (brute force protection)

### 3. Get Verified (Optional but Recommended)
- Go to **Dashboard → Verification**
- Upload your government ID and a selfie holding the ID
- Admin reviews and approves — you get a verified badge (shield icon) next to your name
- Verified sellers get more trust from buyers

---

## For Buyers

### Browsing Items
- **Home Page**: See featured auctions, ending soon items, and browse by category
- **Browse Auctions**: Filter by category, subcategory, city, condition, price range, and listing type
- **Search**: Use the search bar to find specific items

### Categories Available
| Category | Examples |
|---|---|
| Electronics | Computers, Smartphones, Cameras, Gaming |
| Vehicles | Cars, Motorcycles, Boats, Parts |
| Collectibles & Art | Antiques, Coins, Trading Cards, Art |
| Fashion | Clothing, Shoes, Bags, Watches |
| Home & Garden | Furniture, Appliances, Decor |
| Sports & Outdoors | Fitness, Cycling, Camping, Golf |
| Toys & Games | Video Games, Board Games, LEGO |
| Books & Media | Books, Music, Movies |
| Jewelry & Watches | Fine Jewelry, Luxury Watches, Vintage |
| Musical Instruments | Guitars, Pianos, Drums, DJ Equipment |
| Tools & Equipment | Power Tools, Hand Tools, Industrial |
| Other | Miscellaneous |

### Bidding on Auctions
1. Open an auction listing
2. **Standard Bid**: Enter your bid amount (must be at least current bid + increment)
3. **Proxy Bid**: Set your maximum amount — the system automatically bids for you up to that limit (like eBay)
4. **Sniper Bid**: Schedule a bid to be placed in the final seconds of the auction
5. **Buy It Now (BIN)**: Some auctions have a BIN price — click to buy instantly at that price

### Bid Increments
| Current Price | Minimum Increment |
|---|---|
| Under $25 | $1 |
| $25 – $99 | $5 |
| $100 – $249 | $10 |
| $250 – $499 | $25 |
| $500 – $999 | $50 |
| $1,000 – $2,499 | $100 |
| $2,500 – $4,999 | $250 |
| $5,000+ | $500 |

### Watchlist
- Click the heart icon on any listing to add it to your Watchlist
- Track prices and time remaining from one place
- Access via the heart icon in the navbar

### Dashboard
- View your active bids and their status (winning/outbid)
- Read notifications about bid updates, listing approvals, etc.

---

## For Sellers

### Creating a Listing
1. Click **+ Sell** in the navbar
2. Fill in:
   - **Title** and **Description**
   - **Category** and **Subcategory**
   - **Condition**: New, Like New, Very Good, Good, Acceptable
   - **Listing Type**: Auction or Fixed Price
   - **Starting Bid** (for auctions) or **Fixed Price**
   - **Buy It Now Price** (optional for auctions)
   - **Reserve Price** (optional — minimum price to sell)
   - **Duration**: 24h, 48h, or 72h (for auctions)
   - **Images**: Upload up to 10 photos
3. Submit — listing goes to admin for approval

### Listing Statuses
| Status | Meaning |
|---|---|
| Pending | Awaiting admin approval |
| Active | Live and visible to buyers |
| Ended | Auction time expired |
| Rejected | Admin declined the listing |

### Seller Dashboard
- View all your listings and their statuses
- Track bids on your auctions
- See your seller rating and feedback

### Seller Ratings
- Buyers can leave feedback after a transaction
- Your profile shows: overall rating, total ratings, and positive percentage
- Higher ratings = more trust from buyers

---

## For Admins

### Access
- Login with admin credentials
- Navigate to **Admin Panel** via the gear icon in the user menu

### Admin Dashboard
| Metric | Description |
|---|---|
| Total Users | All registered accounts |
| Total Listings | All listings ever created |
| Active Auctions | Currently live auctions |
| Pending Listings | Awaiting your approval |
| Pending Verifications | ID verification requests |
| Total Bids | All bids placed |
| GMV (Gross Merchandise Value) | Total value of completed transactions |
| Platform Fee | Currently FREE |
| Pending Reports | User-submitted reports to review |

### Admin Actions
- **Listings Tab**: Approve or reject pending listings, delete any listing
- **Users Tab**: Suspend or ban users
- **Verifications Tab**: Review ID submissions, approve or reject
- **Reports Tab**: View reported listings and take action

---

## Real-Time Features
- **Live Bid Updates**: When someone bids, all users viewing that auction see the update instantly (WebSocket)
- **Countdown Timers**: Red countdown when less than 1 hour remains
- **Notifications**: Get notified when you're outbid, when your listing is approved, etc.

---

## Platform Rules
1. **BC Residents Only** — Postal code must start with "V"
2. **All listings require admin approval** before going live
3. **Verified sellers** get a shield badge for extra trust
4. **No platform fees** currently — listing and selling is free
5. **Brute force protection** — 5 failed login attempts = 15 minute lockout

---

## Deployment Guide (DigitalOcean + MongoDB Atlas)

### Prerequisites
- DigitalOcean Droplet (Ubuntu recommended)
- MongoDB Atlas account (free tier works)
- Node.js 18+ and Python 3.11+

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

### Environment Variables (backend/.env)
```
MONGO_URL="mongodb+srv://USER:PASSWORD@HOST/"
DB_NAME="bidca_db"
CORS_ORIGINS="https://yourdomain.com"
JWT_SECRET="your-secret-key-here"
ADMIN_EMAIL="admin@bidca.ca"
ADMIN_PASSWORD="your-admin-password"
FRONTEND_URL="https://yourdomain.com"
```

### Frontend Setup
```bash
cd frontend
yarn install
```

### Environment Variables (frontend/.env)
```
REACT_APP_BACKEND_URL="https://yourdomain.com"
```

### MongoDB Atlas Setup
1. Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Create a database user (username: `bidca`, set a strong password)
3. **Network Access** → Add your server's IP address (or `0.0.0.0/0` for testing)
4. Copy the connection string and paste in `MONGO_URL`
5. The admin account auto-seeds on first startup

### Required Python Packages
- `fastapi`, `uvicorn`, `motor`, `pymongo`, `dnspython`
- `python-jose`, `bcrypt`, `python-socketio`
- `pydantic[email]`

### Start the App
```bash
# Backend
uvicorn server:fastapi_app --host 0.0.0.0 --port 8001

# Frontend
yarn start
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register (BC postal codes only) |
| POST | `/api/auth/login` | Login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/auth/refresh` | Refresh token |

### Listings
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/listings` | Browse (supports filters: category, city, search, etc.) |
| GET | `/api/listings/featured` | Featured auctions |
| GET | `/api/listings/ending-soon` | Ending soon auctions |
| GET | `/api/listings/{id}` | Listing detail |
| POST | `/api/listings` | Create listing (auth required) |
| POST | `/api/listings/{id}/bid` | Place bid (supports proxy) |
| POST | `/api/listings/{id}/snipe` | Schedule sniper bid |
| POST | `/api/listings/{id}/report` | Report listing |

### User
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/users/me/bids` | My active bids |
| GET | `/api/users/me/listings` | My listings |
| GET | `/api/notifications` | My notifications |
| GET | `/api/categories` | All categories |
| GET | `/api/popular-keywords` | Trending search terms |

### Admin (requires admin role)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/admin/listings` | Manage listings |
| PUT | `/api/admin/listings/{id}` | Approve/reject listing |
| DELETE | `/api/admin/listings/{id}` | Delete listing |
| GET | `/api/admin/users` | Manage users |
| PUT | `/api/admin/users/{id}` | Suspend/ban user |
| GET | `/api/admin/verifications` | Review verifications |
| PUT | `/api/admin/verifications/{id}` | Approve/reject verification |

---

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Phosphor Icons, Socket.io-client
- **Backend**: FastAPI (Python), Motor (async MongoDB), python-socketio
- **Database**: MongoDB (Atlas or local)
- **Auth**: JWT with httpOnly cookies + bcrypt
- **Real-time**: WebSocket via Socket.IO

---

*Last updated: April 3, 2026*
