# Google OAuth Implementation - Setup Guide

## Implementation Complete ✅

Google OAuth has been successfully integrated into PharmaNexus across all three backend services (Node.js, Python Flask) and the React frontend.

---

## What Was Changed

### 1. **Dependencies Updated**
- ✅ `frontend/package.json`: Added `@react-oauth/google`
- ✅ `node-backend/package.json`: Added `google-auth-library`  
- ✅ `backend/requirements.txt`: Added `google-auth`

### 2. **Node.js Backend** (`node-backend/src/app.js`)
- ✅ Replaced email/password validation with Google ID token verification
- ✅ Added `/api/auth/login` endpoint to accept & verify `idToken`
- ✅ Added `/api/auth/me` endpoint to return authenticated user info
- ✅ Added `/api/auth/logout` endpoint
- ✅ Updated `/api/auth/verify` endpoint (removed hardcoded admin reference)

### 3. **Python Flask Backend** (`backend/api.py`)
- ✅ Added Google OAuth imports: `google.oauth2.id_token`, `google.auth.transport.requests`
- ✅ Added `/auth/google/verify` endpoint to validate Google ID tokens
- ✅ Made `/auth/google/verify` a public path (no JWT required)
- ✅ All existing `/predict` and other routes continue to work with JWT from Node

### 4. **React Frontend**
- ✅ `src/main.tsx`: Wrapped app with `<GoogleOAuthProvider>`
- ✅ `src/pages/LoginPage.tsx`: Replaced email/password form with Google OAuth button
- ✅ `src/services/api.ts`: Replaced `login(email, password)` with `loginWithGoogle(idToken)`

### 5. **Environment Configuration**
- ✅ `.env.example`: Added `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- ✅ `node-backend/.env.example`: Updated with Google OAuth credentials
- ✅ `frontend/.env.example`: Added `VITE_GOOGLE_CLIENT_ID`
- ✅ Removed deprecated `PHARMA_NEXUS_LOGIN_EMAIL` and `PHARMA_NEXUS_LOGIN_PASSWORD`

---

## Setup Instructions

### Step 1: Create Google OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Web application**
6. Add Authorized redirect URIs:
   - `http://localhost:5173` (React frontend)
   - `http://localhost:5050/api/auth/login` (Node backend)
   - For production: `https://yourdomain.com`, `https://yourdomain.com/api/auth/login`, etc.
7. Copy **Client ID** and **Client Secret**

### Step 2: Configure Environment Variables

Create `.env` files in root, backend, and frontend directories:

**Root directory (`.env`)**:
```
GOOGLE_CLIENT_ID=your-client-id-from-google-console
GOOGLE_CLIENT_SECRET=your-client-secret-from-google-console
AUTH_JWT_SECRET=your-jwt-secret-change-in-production
DATABASE_URL=postgresql://novacura:novacura123@localhost:5432/novacura
# ... other existing vars
```

**Node backend (`node-backend/.env`)**:
```
PORT=5050
GOOGLE_CLIENT_ID=your-client-id-from-google-console
GOOGLE_CLIENT_SECRET=your-client-secret-from-google-console
AUTH_JWT_SECRET=your-jwt-secret-change-in-production
DATABASE_URL=postgresql://novacura:novacura123@localhost:5432/novacura
```

**Frontend (`frontend/.env`)**:
```
VITE_GOOGLE_CLIENT_ID=your-client-id-from-google-console
```

### Step 3: Install Dependencies (Already Done)

```bash
# Frontend
cd frontend
npm install

# Node backend
cd ../node-backend
npm install

# Python backend
cd ../backend
pip install -r requirements.txt
```

---

## Authentication Flow

```
User clicks "Login with Google"
                ↓
Google OAuth popup appears (user authenticates with Google account)
                ↓
Google returns ID token to frontend
                ↓
Frontend sends ID token → Node backend: POST /api/auth/login
                ↓
Node backend verifies token with Google, extracts user info
                ↓
Node backend issues JWT (signed with AUTH_JWT_SECRET)
                ↓
Frontend stores JWT in localStorage
                ↓
Frontend redirects to /app
                ↓
All subsequent API calls include: Authorization: Bearer {JWT}
                ↓
Both Node and Flask backends validate JWT using AUTH_JWT_SECRET
```

---

## API Endpoints

### Node Backend (`http://localhost:5050/api`)
- `POST /auth/login` - Login with Google
  - Request: `{ "idToken": "google-id-token" }`
  - Response: `{ "token": "jwt", "user": { "email": "...", "name": "...", "picture": "..." } }`

- `GET /auth/me` - Get current user info
  - Headers: `Authorization: Bearer {jwt}`
  - Response: `{ "email": "...", "name": "...", "picture": "..." }`

- `POST /auth/logout` - Logout
  - Response: `{ "message": "Logged out successfully." }`

### Python Flask Backend (`http://localhost:5000`)
- `POST /auth/google/verify` - Verify Google ID token (alternative to Node backend)
  - Request: `{ "idToken": "google-id-token" }`
  - Response: `{ "token": "jwt", "user": { "email": "...", "name": "...", "picture": "..." } }`

- All other endpoints (e.g., `/predict`, `/predict-ensemble`, etc.):
  - Headers: `Authorization: Bearer {jwt}`
  - JWT can come from Node backend or Flask backend (using same AUTH_JWT_SECRET)

---

## Testing the Implementation

### 1. Start the services:
```bash
# Terminal 1: Node backend
cd node-backend
npm run dev

# Terminal 2: React frontend
cd frontend
npm run dev

# Terminal 3: Python Flask backend
cd backend
python api.py
```

### 2. Navigate to `http://localhost:5173/login`

### 3. Click "Login with Google" button

### 4. Authenticate with a Google account

### 5. Verify you're redirected to `/app` dashboard

### 6. Check browser DevTools → Application → Cookies/LocalStorage → `pharma_nexus_auth_token` (JWT should be stored)

### 7. Make a prediction request to verify JWT is accepted by backends

---

## Key Security Changes

✅ **Removed hardcoded credentials** - No more `admin@pharmanexus.ai` / `pharmanexus123`

✅ **Google OAuth verification** - Only valid Google accounts can log in

✅ **JWT-only authentication** - Stateless, industry-standard JWT tokens

✅ **Token expiration** - 8-hour expiration on Node-issued tokens (Google ID tokens ~1 hour)

---

## Troubleshooting

### "GOOGLE_CLIENT_ID not found" error
- Ensure `.env` files are created with correct values from Google Console
- Verify `frontend/.env` has `VITE_GOOGLE_CLIENT_ID=...`
- Note: `VITE_` prefix is required for frontend environment variables

### Login button not appearing
- Ensure `frontend/.env` has `VITE_GOOGLE_CLIENT_ID` set
- Check browser console for errors
- Verify `@react-oauth/google` is installed: `npm list @react-oauth/google`

### "Invalid or expired token" error from Node backend
- Verify Google Client ID matches between Google Console and `.env` files
- Check that Google token is being sent correctly to Node backend
- Ensure `GOOGLE_CLIENT_ID` environment variable is set in Node process

### CORS errors
- Ensure all services are running on correct ports:
  - Frontend: 5173
  - Node backend: 5050
  - Flask backend: 5000
- Check CORS configuration in app.js and api.py

### "Authorization token required" from Flask backend
- Ensure JWT from Node backend is being sent in request headers: `Authorization: Bearer {token}`
- Verify `AUTH_JWT_SECRET` is the same in both Node and Flask `.env` files
- Check that token hasn't expired (8 hours)

---

## Next Steps (Optional)

1. **Token Refresh** - Implement token refresh endpoint for long sessions
2. **User Roles** - Add role-based access control based on Google email domain
3. **Logout UI** - Add logout button in navbar that clears localStorage
4. **Production Deployment** - Update redirect URIs for production domain
5. **Multiple Providers** - Add GitHub/Microsoft OAuth as fallback options

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `node-backend/src/app.js` | Replaced email/password auth with Google OAuth |
| `node-backend/package.json` | Added google-auth-library |
| `node-backend/.env.example` | Updated with Google OAuth vars |
| `backend/api.py` | Added Google ID token verification endpoint |
| `backend/requirements.txt` | Added google-auth |
| `frontend/src/main.tsx` | Added GoogleOAuthProvider wrapper |
| `frontend/src/pages/LoginPage.tsx` | Replaced form with Google OAuth button |
| `frontend/src/services/api.ts` | Added loginWithGoogle method |
| `frontend/package.json` | Added @react-oauth/google |
| `frontend/.env.example` | Added VITE_GOOGLE_CLIENT_ID |
| `.env.example` | Added Google OAuth configuration |

---

**Implementation completed successfully!** All services are ready to use Google OAuth for authentication.
