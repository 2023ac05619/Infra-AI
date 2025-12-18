import { NextResponse } from 'next/server'
import { db } from '@/lib/db'

export async function GET() {
  try {
    console.log('DATABASE_URL:', process.env.DATABASE_URL)
    const userCount = await db.user.count()
    console.log('User count from API:', userCount)

    return NextResponse.json({
      isFirstUser: userCount === 0
    })
  } catch (error) {
    console.error('Error checking first user status:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
