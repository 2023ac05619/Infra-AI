import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { command, workingDirectory } = await request.json()

    if (!command || typeof command !== 'string') {
      return NextResponse.json({ error: 'Command is required' }, { status: 400 })
    }

    // Basic security checks - prevent dangerous commands
    const dangerousCommands = [
      'rm -rf /',
      'sudo rm',
      'format',
      'del /s',
      'shutdown',
      'reboot',
      'halt',
      'poweroff',
      'mkfs',
      'fdisk',
      'dd if=/dev/zero'
    ]

    const isDangerous = dangerousCommands.some(dangerous => 
      command.toLowerCase().includes(dangerous.toLowerCase())
    )

    if (isDangerous) {
      return NextResponse.json({ 
        error: 'Command blocked for security reasons',
        output: '',
        exitCode: 1
      }, { status: 400 })
    }

    try {
      // Execute the command
      const { stdout, stderr } = await execAsync(command, {
        cwd: workingDirectory || process.cwd(),
        timeout: 30000, // 30 second timeout
        maxBuffer: 1024 * 1024 * 10 // 10MB buffer
      })

      return NextResponse.json({
        success: true,
        output: stdout,
        error: stderr,
        exitCode: 0,
        command
      })

    } catch (error: any) {
      return NextResponse.json({
        success: false,
        output: '',
        error: error.message || 'Command execution failed',
        exitCode: error.code || 1,
        command
      })
    }

  } catch (error) {
    console.error('Terminal API error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
