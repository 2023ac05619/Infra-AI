# InfraChat - AI Infrastructure Assistant

InfraChat is an AI-powered web application that provides natural language interaction with comprehensive infrastructure management capabilities. Powered by the InfraAI backend, it offers intelligent AIOps features including VMware ESXi management, Kubernetes operations, Prometheus monitoring, and Grafana dashboard access through MCP (Model Context Protocol) integrations.

The interface features a ChatGPT-like design with dynamic sliding panes that automatically display structured information like URLs, credentials, SSH commands, and infrastructure data when the AI responds.

##  Features

###  Authentication & User Management
- **Simple email/password** authentication with NextAuth.js
- **Local user management** - no external OAuth required
- **Secure password hashing** with bcrypt
- **Persistent user sessions** with secure token management
- **User profiles** with email display
- **Auto-registration** - new users are created automatically
- **Perfect for internal company use**

###  Chat History Management
- **Left sidebar** with chat history (similar to GLM chat.z.ai)
- **Persistent chat sessions** stored in database
- **Session management** with titles and timestamps
- **Message count** indicators for each session
- **New chat creation** with one click
- **Chat session switching** with smooth transitions

### ️ Chat Interface
- **ChatGPT-like layout** with left-aligned user messages and right-aligned AI responses
- **Markdown support** with syntax highlighting for code blocks
- **Streaming text** support for real-time responses
- **Smart input** with "Enter to send" and "Shift+Enter" for new lines
- **Session-based** message history (no more localStorage only)

###  Dynamic Panes

#### Bottom Pane
Slides up when AI response includes infrastructure information:
-  **URLs** and web endpoints
-  **Usernames**, passwords, and tokens
- ️ **Configuration data** and key-value pairs
-  **Copy-to-clipboard** functionality for each item
- **Copy All** button for bulk copying

#### Right Pane
Slides in from the right when AI response contains technical data:
-  **SSH commands** and terminal instructions
-  **Logs** and monitoring information
-  **Code snippets** and script previews
- **Syntax highlighting** for better readability
- **Pin/Unpin** functionality to keep pane open

###  AI Infrastructure Assistant Capabilities
InfraChat provides access to comprehensive infrastructure management through natural language:

#### VMware ESXi Management (16 tools)
- **VM Operations**: Create, delete, clone, power on/off VMs
- **VM Monitoring**: Get VM info, list all VMs, check host status
- **Storage Management**: List datastores and storage resources
- **Network Management**: List available networks
- **Snapshots**: Create, list, and delete VM snapshots

#### Kubernetes Operations (11 tools)
- **Resource Management**: Get, describe, delete pods, deployments, services
- **Scaling**: Scale deployments and check rollout status
- **Debugging**: View logs, execute commands in containers
- **Networking**: Port forward to pods, manage node taints
- **Configuration**: Apply manifests and manage resources

#### Prometheus Monitoring (6 tools)
- **Metrics Queries**: Execute instant and range PromQL queries
- **Discovery**: List available metrics and get metadata
- **Health Checks**: Monitor Prometheus connectivity
- **Target Management**: View scrape targets and their status

#### Grafana Dashboard Access (3 tools)
- **Dashboard Management**: List and retrieve dashboard configurations
- **Data Source Discovery**: View configured data sources

###  User Experience
- **Dark/Light mode** toggle with system preference detection
- **Smooth animations** using Framer Motion
- **Responsive design** that works on all devices
- **Modern DevOps aesthetic** with rounded corners and soft shadows
- **Auto-close** panes on next query (unless pinned)
- **Mobile-friendly** sidebar with overlay

##  Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd infrachat
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Push database schema:
```bash
npm run db:push
```

5. Start the development server:
```bash
npm run dev
```

6. Open [http://localhost:3001](http://localhost:3001) in your browser

7. **Sign in with any email/password** - new users are created automatically

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL="file:./db/custom.db"

# NextAuth Configuration
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="your-secret-key-here-change-this-in-production"

# Note: No external OAuth providers needed for local company use
# Authentication uses email/password with local database
```

## ️ Architecture

### Frontend
- **Next.js 15** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** component library
- **Framer Motion** for animations
- **react-markdown** for message rendering
- **react-syntax-highlighter** for code highlighting
- **next-themes** for dark/light mode
- **NextAuth.js** for authentication

### Backend
- **Next.js API Routes** for server-side functionality
- **Prisma ORM** with SQLite database
- **z-ai-web-dev-sdk** for AI integration
- **NextAuth.js** for session management
- **Structured JSON responses** for pane management

### Database Schema
- **Users** - Authentication and user profiles
- **ChatSessions** - Chat conversation containers
- **Messages** - Individual chat messages with roles

##  API Integration

The app uses a structured response format:

```json
{
  "reply": "Here's the app URL and SSH command you asked for:",
  "panes": [
    {
      "position": "bottom",
      "type": "key_values", 
      "data": {
        "web_url": "https://app.internal:7000",
        "username": "admin",
        "password": "*****"
      }
    },
    {
      "position": "right",
      "type": "terminal",
      "data": "ssh user@server01.internal"
    }
  ]
}
```

### Authentication Endpoints
- `GET/POST /api/auth/[...nextauth]` - NextAuth.js authentication
- `GET /api/auth/session` - Get current session
- `/auth/signin` - Sign in page

### Chat Management Endpoints
- `GET /api/chat-sessions` - Get user's chat sessions
- `POST /api/chat-sessions` - Create new chat session
- `GET /api/sessions/[sessionId]/messages` - Get session messages
- `POST /api/sessions/[sessionId]/messages` - Add message to session
- `POST /api/chat` - Send message to AI

### Pane Types

#### Bottom Pane Types
- `key_values`: Displays key-value pairs with icons and copy buttons

#### Right Pane Types  
- `terminal`: Shows terminal-style command blocks
- `code`: Displays syntax-highlighted code snippets
- `logs`: Shows log output in terminal format

##  Example User Flows

### 1. Authentication & Setup
**User:** Visits the app → Redirected to sign in → Enters any email/password → Auto-registered → Lands on main interface

### 2. Starting a New Chat
**User:** Clicks "New Chat" in sidebar → Gets fresh chat interface → Begins conversation

### 3. Managing Chat History
**User:** Clicks menu button → Sidebar slides open → Shows all previous chats → Clicks any chat to load

### 4. Getting Application Access
**User:** "Give me the URL of the web app and admin login."

**AI Response:** Main chat + bottom pane slides up showing:
-  Webapp URL: https://dashboard.internal:8080
-  Username: admin  
-  Token: xxxxx

### 5. Server Access
**User:** "SSH into redis cluster node 02."

**AI Response:** Main chat + right pane opens with:
```bash
ssh redis02.internal -u admin
```

## ️ Development

### Available Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run db:push` - Push schema changes to database
- `npm run db:generate` - Generate Prisma client
- `npm run db:migrate` - Run database migrations

### Project Structure
```
src/
├── app/
│   ├── api/
│   │   ├── auth/[...nextauth]/    # NextAuth endpoints
│   │   ├── chat-sessions/         # Chat session management
│   │   ├── sessions/[sessionId]/messages/  # Message management
│   │   └── chat/                  # AI chat endpoint
│   ├── auth/signin/               # Sign in page
│   ├── layout.tsx                 # Root layout with providers
│   └── page.tsx                   # Main InfraChat component
├── components/
│   ├── providers/                 # React providers
│   ├── sidebar.tsx               # Chat history sidebar
│   └── ui/                       # shadcn/ui components
└── lib/                          # Utility functions
```

##  Design System

### Theme
- **Dark mode** by default with DevOps aesthetic
- **Semantic colors** using Tailwind CSS variables
- **Consistent spacing** and typography
- **Glass-morphism effects** for modern look

### Animations
- **Slide-up** animation for bottom pane
- **Slide-in** animation for right pane  
- **Slide-in/out** animation for sidebar
- **Fade-in** for messages
- **Smooth transitions** throughout

### Responsive Design
- **Mobile-first** approach
- **Adaptive layouts** for different screen sizes
- **Touch-friendly** interactions
- **Sidebar overlay** on mobile devices

##  Configuration

### Authentication Setup
**No external setup required!** The app uses local email/password authentication:

1. **Auto-registration**: Any email/password combination creates a new user
2. **Secure storage**: Passwords are hashed with bcrypt
3. **Perfect for internal use**: No external OAuth providers needed

For production, just update the `NEXTAUTH_SECRET` environment variable.

### Database Management
- Uses SQLite for development (can be switched to PostgreSQL for production)
- Prisma migrations for schema changes
- Automatic client generation on schema changes

##  Responsive Behavior

### Desktop (1024px+)
- Sidebar visible by default, can be toggled
- Full-width chat interface
- Both panes can be open simultaneously

### Tablet (768px - 1023px)
- Sidebar hidden by default, overlay when open
- Adaptive chat width
- Panes adjust to available space

### Mobile (< 768px)
- Sidebar as full-screen overlay
- Compact chat interface
- Panes take full width when open
- Touch-optimized interactions

##  Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

##  License

This project is licensed under the MIT License.

##  Acknowledgments

- Built with [Next.js](https://nextjs.org/)
- UI components by [shadcn/ui](https://ui.shadcn.com/)
- Icons by [Lucide](https://lucide.dev/)
- Animations by [Framer Motion](https://www.framer.com/motion/)
- AI integration by [Z.ai](https://z.ai/)
- Authentication by [NextAuth.js](https://next-auth.js.org/)
- Database by [Prisma](https://www.prisma.io/)
