'use client'

import { useState, useEffect } from 'react'
import { signIn, useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Terminal, User, Lock, UserPlus, Eye, EyeOff } from 'lucide-react'
import { motion } from 'framer-motion'

export default function SignIn() {
  const [isLoading, setIsLoading] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isFirstUser, setIsFirstUser] = useState(false)
  const router = useRouter()
  const { data: session, status } = useSession()

  // Check if this is first user registration
  useEffect(() => {
    const checkFirstUser = async () => {
      try {
        const response = await fetch('/api/auth/check-first-user')
        const data = await response.json()
        setIsFirstUser(data.isFirstUser)
      } catch (error) {
        console.error('Error checking first user status:', error)
      }
    }

    if (status !== 'loading') {
      checkFirstUser()
    }
  }, [status])

  // Redirect authenticated users appropriately
  useEffect(() => {
    if (status === 'loading') return

    if (session) {
      // Check if password reset is required
      if ((session.user as any)?.forcePasswordReset) {
        router.push('/auth/change-password')
      } else {
        router.push('/')
      }
    }
  }, [session, status, router])

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const result = await signIn('credentials', {
        email,
        password,
        redirect: false,
      })

      if (result?.error) {
        setError('Invalid credentials. Please try again.')
      }
      // The useEffect will handle redirection based on session state
    } catch (error) {
      setError('An error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Card className="border-border/50 shadow-xl">
          <CardHeader className="text-center pb-6">
            <div className="flex justify-center mb-4">
              <div className="w-12 h-12 bg-primary rounded-xl flex items-center justify-center">
                {isFirstUser ? (
                  <UserPlus className="w-7 h-7 text-primary-foreground" />
                ) : (
                  <Terminal className="w-7 h-7 text-primary-foreground" />
                )}
              </div>
            </div>
            <CardTitle className="text-2xl font-bold">
              {isFirstUser ? 'Set Up InfraChat' : 'Welcome to InfraChat'}
            </CardTitle>
            <CardDescription className="text-base">
              {isFirstUser
                ? 'Create your admin account to get started'
                : 'Sign in to access your AI infrastructure assistant'
              }
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2">
            <form onSubmit={handleSignIn} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium">
                  Email
                </Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10"
                    required
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  Password
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10 pr-10"
                    required
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-2 top-2 h-6 w-6 p-0 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              </div>

              {error && (
                <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-12 text-base"
                size="lg"
              >
                {isLoading
                  ? (isFirstUser ? 'Creating account...' : 'Signing in...')
                  : (isFirstUser ? 'Create Admin Account' : 'Sign In')
                }
              </Button>
            </form>

          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}
