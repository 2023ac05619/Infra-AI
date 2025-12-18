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

    let settings = await db.userSettings.findUnique({
      where: { userId: session.user.id }
    })

    // Create default settings if none exist
    if (!settings) {
      settings = await db.userSettings.create({
        data: {
          userId: session.user.id,
          aiProvider: 'ollama',
          ollamaUrl: 'http://192.168.200.201:12434',
          ollamaModel: 'llama3.3:latest',
          theme: 'system',
          language: 'en',
          fontSize: 'medium',
          maxTokens: 1000,
          temperature: 0.7,
          autoSave: true,
          sidebarCollapsed: true,
          showTimestamps: true
        }
      })
    }

    return NextResponse.json(settings)
  } catch (error) {
    console.error('Error fetching settings:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
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

    const body = await request.json()
    const {
      aiProvider,
      ollamaUrl,
      ollamaModel,
      theme,
      language,
      fontSize,
      maxTokens,
      temperature,
      autoSave,
      sidebarCollapsed,
      showTimestamps,
      chatMode,
      // LLM Configuration
      llmModel,
      llmTemperature,
      embeddingModel,
      // Document Processing
      chunkSize,
      chunkOverlap,
      // Vector Database
      qdrantUrl,
      qdrantApiKey,
      qdrantUseCloud,
      defaultCollection,
      // Observability
      langfuseEnabled,
      langfuseHost,
      langfuseSecretKey,
      langfusePublicKey,
      langfuseSampleRate,
      // File Upload
      maxUploadSize,
      // Document Folder Monitoring
      documentFolderPath,
    // Infrastructure Keywords
    infrastructureKeywords,

    // Backend Configuration (new fields)
    prometheusUrl,
    lokiUrl,
    postgresUrl,
    redisUrl,
    embedModelName,
    maxNewTokens,
    scanCron,
    networkCidr,
    topKRetrieval,
    useRedisQueue,
    queueDir,
    logLevel
    } = body

    const settings = await db.userSettings.upsert({
      where: { userId: session.user.id },
      update: {
        aiProvider,
        ollamaUrl,
        ollamaModel,
        theme,
        language,
        fontSize,
        maxTokens,
        temperature,
        autoSave,
        sidebarCollapsed,
        showTimestamps,
        chatMode,
        llmModel,
        llmTemperature,
        embeddingModel,
        chunkSize,
        chunkOverlap,
        qdrantUrl,
        qdrantApiKey,
        qdrantUseCloud,
        defaultCollection,
        langfuseEnabled,
        langfuseHost,
        langfuseSecretKey,
        langfusePublicKey,
        langfuseSampleRate,
        maxUploadSize,
        documentFolderPath,
        infrastructureKeywords,
        prometheusUrl,
        lokiUrl,
        postgresUrl,
        redisUrl,
        embedModelName,
        maxNewTokens,
        scanCron,
        networkCidr,
        topKRetrieval,
        useRedisQueue,
        queueDir,
        logLevel
      },
      create: {
        userId: session.user.id,
        aiProvider,
        ollamaUrl,
        ollamaModel,
        theme: theme || 'system',
        language: language || 'en',
        fontSize: fontSize || 'medium',
        maxTokens: maxTokens || 1000,
        temperature: temperature || 0.7,
        autoSave: autoSave !== undefined ? autoSave : true,
        sidebarCollapsed: sidebarCollapsed !== undefined ? sidebarCollapsed : false,
        showTimestamps: showTimestamps !== undefined ? showTimestamps : true,
        chatMode: chatMode || 'chat',
        llmModel: llmModel || 'microsoft/DialoGPT-medium',
        llmTemperature: llmTemperature || 0.7,
        embeddingModel: embeddingModel || 'all-MiniLM-L6-v2',
        chunkSize: chunkSize || 512,
        chunkOverlap: chunkOverlap || 50,
        qdrantUrl: qdrantUrl || 'http://localhost:6333',
        qdrantApiKey,
        qdrantUseCloud: qdrantUseCloud !== undefined ? qdrantUseCloud : false,
        defaultCollection: defaultCollection || 'documents',
        langfuseEnabled: langfuseEnabled !== undefined ? langfuseEnabled : true,
        langfuseHost: langfuseHost || 'http://localhost:3001',
        langfuseSecretKey,
        langfusePublicKey,
        langfuseSampleRate: langfuseSampleRate || 1.0,
        maxUploadSize: maxUploadSize || 10485760, // 10MB
        documentFolderPath: documentFolderPath || "./documents",
        infrastructureKeywords: infrastructureKeywords || "docker,kubernetes,k8s,server,database,db,port,host,endpoint,api,aws,azure,gcp,cloud,infra,infrastructure,deploy,container,cluster,virtual machine,vm,network,load balancer,storage,backup,monitoring,logging,alert,scaling,auto-scal,firewall,security,ssl,certificate,domain,subdomain"
      }
    })

    return NextResponse.json(settings)
  } catch (error) {
    console.error('Error updating settings:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
