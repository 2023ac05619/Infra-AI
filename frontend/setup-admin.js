#!/usr/bin/env node
/**
 * Setup script to create a default admin user for InfraChat
 */

const { PrismaClient } = require('@prisma/client')
const bcrypt = require('bcryptjs')

const prisma = new PrismaClient()

async function createAdminUser() {
  try {
    console.log('Setting up default admin user...')

    // Check if admin user already exists
    const existingUser = await prisma.user.findUnique({
      where: { email: 'admin@infraai.com' }
    })

    if (existingUser) {
      console.log('Admin user already exists!')
      console.log('Email: admin@infraai.com')
      console.log('Password: admin123')
      return
    }

    // Create admin user
    const hashedPassword = await bcrypt.hash('admin123', 10)

    const adminUser = await prisma.user.create({
      data: {
        email: 'admin@infraai.com',
        name: 'InfraAI Admin',
        password: hashedPassword
      }
    })

    console.log(' Admin user created successfully!')
    console.log('Email: admin@infraai.com')
    console.log('Password: admin123')
    console.log('')
    console.log('You can now sign in at http://localhost:3001')

  } catch (error) {
    console.error('Error creating admin user:', error)
  } finally {
    await prisma.$disconnect()
  }
}

createAdminUser()
