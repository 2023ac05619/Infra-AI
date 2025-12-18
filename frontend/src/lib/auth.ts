import NextAuth from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import { PrismaAdapter } from '@next-auth/prisma-adapter'
import { db } from '@/lib/db'
import bcrypt from 'bcryptjs'

export const authOptions = {
  adapter: PrismaAdapter(db),
  providers: [
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' }
      },
      async authorize(credentials) {
        console.log('Auth attempt for:', credentials?.email)

        if (!credentials?.email || !credentials?.password) {
          console.log('Missing credentials')
          return null
        }

        try {
          // Check if any users exist in the system
          const userCount = await db.user.count()
          console.log('User count:', userCount)

          if (userCount === 0) {
            console.log('Creating first user')
            // First user registration - create as admin
            const hashedPassword = await bcrypt.hash(credentials.password, 12)
            const user = await db.user.create({
              data: {
                email: credentials.email,
                name: credentials.email.split('@')[0], // Use email prefix as display name initially
                password: hashedPassword
              }
            })

            console.log('Created user:', user.id)
            return {
              id: user.id,
              email: user.email,
              name: user.name,
              isFirstUser: true
            }
          } else {
            console.log('Looking for existing user')
            // Normal login - find existing user
            const user = await db.user.findUnique({
              where: { email: credentials.email }
            })

            console.log('Found user:', user ? user.id : 'null')

            if (!user) {
              console.log('User not found')
              return null // User not found
            }

            // Verify password
            const isPasswordValid = await bcrypt.compare(credentials.password, user.password || '')
            console.log('Password valid:', isPasswordValid)

            if (!isPasswordValid) {
              console.log('Invalid password')
              return null
            }

            console.log('Authentication successful')
            return {
              id: user.id,
              email: user.email,
              name: user.name
            }
          }
        } catch (error) {
          console.error('Auth error:', error)
          return null
        }
      }
    })
  ],
  session: {
    strategy: 'jwt' as const,
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
        token.forcePasswordReset = (user as any).forcePasswordReset
      }
      return token
    },
    async session({ session, token }) {
      if (token) {
        session.user.id = token.id as string
        ;(session.user as any).forcePasswordReset = token.forcePasswordReset
      }
      return session
    },
  },
  pages: {
    signIn: '/auth/signin',
  },
}
