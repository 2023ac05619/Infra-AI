export async function PATCH(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Ensure user exists in database
    let user = await db.user.findUnique({
      where: { id: session.user.id }
    })
    if (!user) {
      user = await db.user.create({
        data: {
          id: session.user.id,
          email: session.user.email || 'user@demo.com',
          name: session.user.name || 'User',
        }
      })
    }

    const { searchParams } = new URL(request.url)
    const sessionId = searchParams.get('sessionId')
    const { title } = await request.json()

    if (!sessionId) {
      return NextResponse.json({ error: 'Session ID is required' }, { status: 400 })
    }

    if (!title || typeof title !== 'string') {
      return NextResponse.json({ error: 'Title is required and must be a string' }, { status: 400 })
    }

    // First verify the session belongs to the user
    const chatSession = await db.chatSession.findFirst({
      where: {
        id: sessionId,
        userId: session.user.id
      }
    })

    if (!chatSession) {
      return NextResponse.json({ error: 'Chat session not found' }, { status: 404 })
    }

    // Update the session title
    const updatedSession = await db.chatSession.update({
      where: { id: sessionId },
      data: { title }
    })

    return NextResponse.json(updatedSession)
  } catch (error) {
    console.error('Error updating chat session:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { db } from '@/lib/db'

export async function GET() {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const chatSessions = await db.chatSession.findMany({
      where: { userId: session.user.id },
      orderBy: { updatedAt: 'desc' },
      include: {
        _count: {
          select: { messages: true }
        }
      }
    })

    return NextResponse.json(chatSessions)
  } catch (error) {
    console.error('Error fetching chat sessions:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Ensure user exists in database
    let user = await db.user.findUnique({
      where: { id: session.user.id }
    })
    if (!user) {
      user = await db.user.create({
        data: {
          id: session.user.id,
          email: session.user.email || 'user@demo.com',
          name: session.user.name || 'User',
        }
      })
    }

    const { title } = await request.json()

    const chatSession = await db.chatSession.create({
      data: {
        title: title || 'New Chat',
        userId: session.user.id,
      }
    })

    return NextResponse.json(chatSession)
  } catch (error) {
    console.error('Error creating chat session:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Ensure user exists in database
    let user = await db.user.findUnique({
      where: { id: session.user.id }
    })
    if (!user) {
      user = await db.user.create({
        data: {
          id: session.user.id,
          email: session.user.email || 'user@demo.com',
          name: session.user.name || 'User',
        }
      })
    }

    const { searchParams } = new URL(request.url)
    const sessionId = searchParams.get('sessionId')

    if (!sessionId) {
      return NextResponse.json({ error: 'Session ID is required' }, { status: 400 })
    }

    // First verify the session belongs to the user
    const chatSession = await db.chatSession.findFirst({
      where: {
        id: sessionId,
        userId: session.user.id
      }
    })

    if (!chatSession) {
      return NextResponse.json({ error: 'Chat session not found' }, { status: 404 })
    }

    // Delete all messages in the session first
    await db.message.deleteMany({
      where: { sessionId }
    })

    // Delete the session
    await db.chatSession.delete({
      where: { id: sessionId }
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting chat session:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
