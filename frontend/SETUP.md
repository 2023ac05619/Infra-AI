# Quick Setup Guide for InfraChat

##  5-Minute Setup

### 1. Environment Setup
```bash
# Copy the environment template
cp .env.example .env

# Add a secret key (any random string works for local development)
echo "NEXTAUTH_SECRET=$(openssl rand -base64 32)" >> .env
```

### 2. Database Setup
```bash
# Push the database schema (creates users, chats, messages tables)
npm run db:push
```

### 3. Start the App
```bash
npm run dev
```

### 4. Sign In
- Open http://localhost:3001
- You'll be redirected to the sign-in page
- **Enter any email and password** - a new user account will be created automatically
- Example: email `admin@company.com`, password `admin123`

##  That's it!

Your InfraChat instance is now running with:
-  Local authentication (no Google OAuth needed)
-  Persistent chat history
-  AI infrastructure assistant
-  Dynamic panes for commands and credentials
-  Modern UI with sidebar

##  Perfect for Internal Company Use

- **No external dependencies** - everything runs locally
- **Auto-registration** - any employee can sign up
- **Secure** - passwords are properly hashed
- **Private** - all data stays in your local database

##  For Production

1. Set a strong `NEXTAUTH_SECRET` in your `.env` file
2. Consider switching from SQLite to PostgreSQL for better performance
3. Deploy to your preferred hosting platform

Enjoy your AI infrastructure assistant! 