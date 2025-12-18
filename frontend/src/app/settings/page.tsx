'use client'

import { useState, useEffect, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Loader2, Save, Settings, Zap, Palette, MessageSquare, Home, Cpu, FileText, Database, BarChart3, Upload, Eye, EyeOff } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface UserSettings {
  aiProvider: 'zai' | 'ollama',
  ollamaUrl: string
  ollamaModel: string
  theme: 'light' | 'dark' | 'system'
  language: string
  fontSize: 'small' | 'medium' | 'large'
  maxTokens: number
  temperature: number
  autoSave: boolean
  sidebarCollapsed: boolean
  showTimestamps: boolean

  // Self-Healing Configuration
  selfHealingEnabled: boolean

  // LLM Configuration
  llmModel: string
  llmTemperature: number
  embeddingModel: string

  // Document Processing
  chunkSize: number
  chunkOverlap: number

  // Vector Database
  qdrantUrl: string
  qdrantApiKey: string
  qdrantUseCloud: boolean
  defaultCollection: string

  // Observability
  langfuseEnabled: boolean
  langfuseHost: string
  langfuseSecretKey: string
  langfusePublicKey: string
  langfuseSampleRate: number

  // File Upload
  maxUploadSize: number

  // Document Folder Monitoring
  documentFolderPath: string

  // Infrastructure Keywords
  infrastructureKeywords: string

  // Backend Configuration (new fields)
  prometheusUrl: string
  lokiUrl: string
  postgresUrl: string
  redisUrl: string
  embedModelName: string
  maxNewTokens: number
  scanCron: string
  scanIntervalMinutes: number
  networkCidr: string
  topKRetrieval: number
  useRedisQueue: boolean
  queueDir: string
  logLevel: string
}

interface OllamaTestResult {
  success: boolean
  models?: string[]
  error?: string
}

export default function ApplicationSettingsPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { toast } = useToast()

  const [settings, setSettings] = useState<UserSettings>({
    aiProvider: 'ollama',
    ollamaUrl: '',
    ollamaModel: '',
    theme: 'system',
    language: 'en',
    fontSize: 'medium',
    maxTokens: 1000,
    temperature: 0.7,
    autoSave: true,
    sidebarCollapsed: false,
    showTimestamps: true,

    // Self-Healing Configuration
    selfHealingEnabled: false,

    // LLM Configuration
    llmModel: 'microsoft/DialoGPT-medium',
    llmTemperature: 0.7,
    embeddingModel: 'all-MiniLM-L6-v2',

    // Document Processing
    chunkSize: 512,
    chunkOverlap: 50,

    // Vector Database
    qdrantUrl: 'http://localhost:6333',
    qdrantApiKey: '',
    qdrantUseCloud: false,
    defaultCollection: 'documents',

    // Observability
    langfuseEnabled: true,
    langfuseHost: 'http://localhost:3001',
    langfuseSecretKey: '',
    langfusePublicKey: '',
    langfuseSampleRate: 1.0,

    // File Upload
    maxUploadSize: 10485760, // 10MB

    // Document Folder Monitoring
    documentFolderPath: './documents',

    // Infrastructure Keywords
    infrastructureKeywords: 'docker,kubernetes,k8s,server,database,db,port,host,endpoint,api,aws,azure,gcp,cloud,infra,infrastructure,deploy,container,cluster,virtual machine,vm,network,load balancer,storage,backup,monitoring,logging,alert,scaling,auto-scal,firewall,security,ssl,certificate,domain,subdomain',

    // Backend Configuration (new fields)
    prometheusUrl: 'http://192.168.203.103:8080',
    lokiUrl: 'http://localhost:3100',
    postgresUrl: 'postgresql://user:pass@localhost:5432/infra_rag',
    redisUrl: '',
    embedModelName: 'sentence-transformers/all-MiniLM-L6-v2',
    maxNewTokens: 512,
    scanCron: '',
    scanIntervalMinutes: 60,
    networkCidr: '192.168.1.0/24',
    topKRetrieval: 6,
    useRedisQueue: false,
    queueDir: './queue',
    logLevel: 'INFO'
  })

  const [originalSettings, setOriginalSettings] = useState<UserSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [isTestingOllama, setIsTestingOllama] = useState(false)
  const [ollamaTestResult, setOllamaTestResult] = useState<OllamaTestResult | null>(null)
  const [showLangfuseSecretKey, setShowLangfuseSecretKey] = useState(false)



  useEffect(() => {
    if (status === 'loading') return
    if (!session) {
      router.push('/auth/signin')
      return
    }
    loadSettings()
  }, [session, status, router])

  const loadSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
        setOriginalSettings(data)
      }
    } catch (error) {
      console.error('Error loading settings:', error)
      toast({
        title: 'Error',
        description: 'Failed to load settings',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    if (!hasUnsavedChanges()) return

    setIsSaving(true)
    try {
      // Save frontend settings first
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })

      if (!response.ok) {
        toast({
          title: 'Error',
          description: 'Failed to save settings',
          variant: 'destructive',
        })
        return
      }

      const savedSettings = await response.json()
      setSettings(savedSettings)
      setOriginalSettings(savedSettings)

      // Check if any backend settings changed
      const backendFields = [
        'prometheusUrl', 'lokiUrl', 'postgresUrl', 'redisUrl',
        'embedModelName', 'maxNewTokens', 'scanCron', 'scanIntervalMinutes',
        'networkCidr', 'topKRetrieval', 'useRedisQueue', 'queueDir', 'logLevel'
      ]

      // Check for LLM model changes separately
      const llmModelChanged = originalSettings && settings.llmModel !== originalSettings.llmModel

      const backendSettingsChanged = backendFields.some(field =>
        originalSettings && settings[field as keyof UserSettings] !== originalSettings[field as keyof UserSettings]
      ) || llmModelChanged

      if (backendSettingsChanged) {
        // Apply backend settings
        const backendPayload = backendFields.reduce((acc, field) => {
          const value = settings[field as keyof UserSettings]
          if (value !== undefined && value !== null) {
            acc[field] = value
          }
          return acc
        }, {} as Record<string, any>)

        // Add LLM model mapping if it changed
        if (llmModelChanged && settings.llmModel) {
          backendPayload.llm_model_name = settings.llmModel
        }

        const applyResponse = await fetch('/api/v1/settings/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(backendPayload)
        })

        const applyResult = await applyResponse.json()

        if (applyResult.success) {
          toast({
            title: 'Success',
            description: applyResult.message,
          })
        } else {
          toast({
            title: 'Warning',
            description: `Settings saved but backend application failed: ${applyResult.message}`,
            variant: 'destructive',
          })
        }
      } else {
        toast({
          title: 'Success',
          description: 'Settings saved successfully',
        })
      }
    } catch (error) {
      console.error('Error saving settings:', error)
      toast({
        title: 'Error',
        description: 'Failed to save settings',
        variant: 'destructive',
      })
    } finally {
      setIsSaving(false)
    }
  }

  const testOllamaConnection = async () => {
    if (!settings.ollamaUrl.trim()) {
      setOllamaTestResult({
        success: false,
        error: 'Ollama URL is required'
      })
      return
    }

    setIsTestingOllama(true)
    setOllamaTestResult(null)

    try {
      const response = await fetch('/api/settings/test-ollama', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ollamaUrl: settings.ollamaUrl })
      })

      const result = await response.json()

      if (result.success) {
        setOllamaModels(result.models || [])
        // Auto-select first model if none selected
        if (!settings.ollamaModel && result.models?.length > 0) {
          setSettings(prev => ({ ...prev, ollamaModel: result.models[0] }))
        }
      }

      setOllamaTestResult({
        success: result.success,
        models: result.models,
        error: result.error
      })

      toast({
        title: result.success ? 'Success' : 'Connection Failed',
        description: result.success ? `Connected successfully. Found ${result.models?.length || 0} models.` : result.error,
        variant: result.success ? 'default' : 'destructive',
      })
    } catch (error) {
      console.error('Error testing Ollama:', error)
      setOllamaTestResult({
        success: false,
        error: 'Failed to test connection'
      })
      toast({
        title: 'Connection Failed',
        description: 'Failed to test Ollama connection',
        variant: 'destructive',
      })
    } finally {
      setIsTestingOllama(false)
    }
  }

  const hasUnsavedChanges = () => {
    if (!originalSettings) return false
    return JSON.stringify(settings) !== JSON.stringify(originalSettings)
  }

  const resetToDefaults = () => {
    setSettings({
      aiProvider: 'ollama',
      ollamaUrl: '',
      ollamaModel: '',
      theme: 'system',
      language: 'en',
      fontSize: 'medium',
      maxTokens: 1000,
      temperature: 0.7,
      autoSave: true,
      sidebarCollapsed: false,
      showTimestamps: true,

      // Self-Healing Configuration
      selfHealingEnabled: false,

      // LLM Configuration
      llmModel: 'microsoft/DialoGPT-medium',
      llmTemperature: 0.7,
      embeddingModel: 'all-MiniLM-L6-v2',

      // Document Processing
      chunkSize: 512,
      chunkOverlap: 50,

      // Vector Database
      qdrantUrl: 'http://localhost:6333',
      qdrantApiKey: '',
      qdrantUseCloud: false,
      defaultCollection: 'documents',

      // Observability
      langfuseEnabled: true,
      langfuseHost: 'http://localhost:3001',
      langfuseSecretKey: '',
      langfusePublicKey: '',
      langfuseSampleRate: 1.0,

      // File Upload
      maxUploadSize: 10485760, // 10MB

      // Document Folder Monitoring
      documentFolderPath: './documents',

      // Infrastructure Keywords
      infrastructureKeywords: 'docker,kubernetes,k8s,server,database,db,port,host,endpoint,api,aws,azure,gcp,cloud,infra,infrastructure,deploy,container,cluster,virtual machine,vm,network,load balancer,storage,backup,monitoring,logging,alert,scaling,auto-scal,firewall,security,ssl,certificate,domain,subdomain',

      // Backend Configuration (new fields)
      prometheusUrl: 'http://192.168.203.103:8080',
      lokiUrl: 'http://localhost:3100',
      postgresUrl: 'postgresql://user:pass@localhost:5432/infra_rag',
      redisUrl: '',
      embedModelName: 'sentence-transformers/all-MiniLM-L6-v2',
      maxNewTokens: 512,
      scanCron: '',
      scanIntervalMinutes: 60,
      networkCidr: '192.168.1.0/24',
      topKRetrieval: 6,
      useRedisQueue: false,
      queueDir: './queue',
      logLevel: 'INFO'
    })
  }

  const validateUrl = (url: string) => {
    try {
      new URL(url)
      return true
    } catch {
      return false
    }
  }

  if (status === 'loading' || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    )
  }

  if (!session) return null

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-background/95 backdrop-blur-sm border-b sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <Settings className="w-5 h-5 text-primary-foreground" />
              </div>
              <h1 className="text-xl font-bold">Application Settings</h1>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => router.push('/')}
                className="flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                Home
              </Button>
              <Button
                variant="outline"
                onClick={() => router.push('/settings/ai-engine')}
                className="flex items-center gap-2"
              >
                <Cpu className="w-4 h-4" />
                Backend AI Engine
              </Button>
              <Button
                variant="outline"
                onClick={resetToDefaults}
                disabled={isSaving}
              >
                Reset to Defaults
              </Button>
              <Button
                onClick={handleSave}
                disabled={isSaving || !hasUnsavedChanges()}
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                Save Changes
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-6">
        <Tabs defaultValue="rag" className="space-y-6">
          <div className="w-full overflow-x-auto">
            <TabsList className="inline-flex h-12 items-center justify-start rounded-lg bg-muted p-1 text-muted-foreground w-full">
              <TabsTrigger
                value="rag"
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm gap-2 flex-1 min-w-0"
              >
                <FileText className="w-4 h-4 text-cyan-500" />
                RAG
              </TabsTrigger>
              <TabsTrigger
                value="chat"
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm gap-2 flex-1 min-w-0"
              >
                <MessageSquare className="w-4 h-4 text-blue-500" />
                Chat Settings
              </TabsTrigger>

              <TabsTrigger
                value="observability"
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm gap-2 flex-1 min-w-0"
              >
                <BarChart3 className="w-4 h-4 text-indigo-500" />
                Analytics
              </TabsTrigger>




            </TabsList>
          </div>

          {/* RAG Settings */}
          <TabsContent value="rag" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5 text-emerald-500" />
                  File Upload Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Maximum Upload Size
                      <Badge variant="outline">{(settings.maxUploadSize / (1024 * 1024)).toFixed(1)} MB</Badge>
                    </Label>
                    <Input
                      type="number"
                      min="1"
                      max="100"
                      value={settings.maxUploadSize / (1024 * 1024)}
                      onChange={(e) => setSettings(prev => ({ ...prev, maxUploadSize: parseInt(e.target.value) * 1024 * 1024 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum file size allowed for uploads (1-100 MB)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  RAG Trigger Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="infrastructureKeywords" className="text-base font-medium">
                    Infrastructure Keywords
                  </Label>
                  <textarea
                    id="infrastructureKeywords"
                    value={settings.infrastructureKeywords}
                    onChange={(e) => setSettings(prev => ({ ...prev, infrastructureKeywords: e.target.value }))}
                    placeholder="Enter keywords that trigger infrastructure/RAG mode, separated by commas"
                    className="w-full min-h-[120px] p-3 text-sm rounded-md border border-input bg-background resize-vertical"
                    rows={4}
                  />
                  <p className="text-xs text-muted-foreground">
                    Comma-separated list of keywords that trigger RAG/Document processing mode instead of basic chat.
                    Messages containing these keywords will search your uploaded documents and use retrieved context.
                    Example: docker,kubernetes,server,database,aws,monitoring,network
                  </p>
                  <div className="text-xs text-muted-foreground bg-muted/30 p-2 rounded">
                    <strong>How it works:</strong> When you type messages containing any of these keywords,
                    the system automatically switches from basic chat to document-aware RAG mode,
                    searching your uploaded documents for relevant information before generating responses.
                  </div>
                </div>
              </CardContent>
            </Card>

            <Alert>
              <AlertDescription>
                <strong>Backend AI Configuration Moved:</strong> Document processing, vector database, network scanning,
                and other backend AI settings have been moved to the <strong>Backend AI Engine</strong> page for better organization.
                Click the "Backend AI Engine" button in the header to access these settings.
              </AlertDescription>
            </Alert>
          </TabsContent>

          {/* Chat Settings */}
          <TabsContent value="chat" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-blue-500" />
                  Chat Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="maxTokens" className="flex items-center justify-between">
                      Maximum Tokens
                      <Badge variant="outline">{settings.maxTokens}</Badge>
                    </Label>
                    <Input
                      id="maxTokens"
                      type="number"
                      min="100"
                      max="8000"
                      value={settings.maxTokens}
                      onChange={(e) => setSettings(prev => ({ ...prev, maxTokens: parseInt(e.target.value) || 1000 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Controls the maximum length of AI responses (100-8000)
                    </p>
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label htmlFor="autoSave">Auto-save conversations</Label>
                      <p className="text-sm text-muted-foreground">
                        Automatically save your chat sessions as you type
                      </p>
                    </div>
                    <Switch
                      id="autoSave"
                      checked={settings.autoSave}
                      onCheckedChange={(checked) => setSettings(prev => ({ ...prev, autoSave: checked }))}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="w-5 h-5 text-purple-500" />
                  Appearance & Interface
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="theme">Theme</Label>
                    <Select
                      value={settings.theme}
                      onValueChange={(value: 'light' | 'dark' | 'system') =>
                        setSettings(prev => ({ ...prev, theme: value }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="light">Light</SelectItem>
                        <SelectItem value="dark">Dark</SelectItem>
                        <SelectItem value="system">System</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="language">Language</Label>
                    <Select
                      value={settings.language}
                      onValueChange={(value) => setSettings(prev => ({ ...prev, language: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="es">Spanish</SelectItem>
                        <SelectItem value="fr">French</SelectItem>
                        <SelectItem value="de">German</SelectItem>
                        <SelectItem value="it">Italian</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="fontSize">Font Size</Label>
                    <Select
                      value={settings.fontSize}
                      onValueChange={(value: 'small' | 'medium' | 'large') =>
                        setSettings(prev => ({ ...prev, fontSize: value }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="small">Small</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="large">Large</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label htmlFor="sidebarCollapsed">Keep sidebar collapsed</Label>
                      <p className="text-sm text-muted-foreground">
                        Start with the sidebar in collapsed mode on page load
                      </p>
                    </div>
                    <Switch
                      id="sidebarCollapsed"
                      checked={settings.sidebarCollapsed}
                      onCheckedChange={(checked) => setSettings(prev => ({ ...prev, sidebarCollapsed: checked }))}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label htmlFor="showTimestamps">Show message timestamps</Label>
                      <p className="text-sm text-muted-foreground">
                        Display timestamps on chat messages
                      </p>
                    </div>
                    <Switch
                      id="showTimestamps"
                      checked={settings.showTimestamps}
                      onCheckedChange={(checked) => setSettings(prev => ({ ...prev, showTimestamps: checked }))}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>






          {/* Observability */}
          <TabsContent value="observability" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-indigo-500" />
                  Analytics & Observability
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label htmlFor="langfuseEnabled">Enable Langfuse Analytics</Label>
                      <p className="text-sm text-muted-foreground">
                        Track application usage and performance metrics
                      </p>
                    </div>
                    <Switch
                      id="langfuseEnabled"
                      checked={settings.langfuseEnabled}
                      onCheckedChange={(checked) => setSettings(prev => ({ ...prev, langfuseEnabled: checked }))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="langfuseHost">Langfuse Host</Label>
                    <Input
                      id="langfuseHost"
                      placeholder="http://localhost:3001"
                      value={settings.langfuseHost}
                      onChange={(e) => setSettings(prev => ({ ...prev, langfuseHost: e.target.value }))}
                      disabled={!settings.langfuseEnabled}
                    />
                    <p className="text-xs text-muted-foreground">
                      URL of your Langfuse observability server
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="langfusePublicKey">Public Key</Label>
                      <Input
                        id="langfusePublicKey"
                        placeholder="Enter public key"
                        value={settings.langfusePublicKey}
                        onChange={(e) => setSettings(prev => ({ ...prev, langfusePublicKey: e.target.value }))}
                        disabled={!settings.langfuseEnabled}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="langfuseSecretKey">Secret Key</Label>
                      <div className="relative">
                        <Input
                          id="langfuseSecretKey"
                          type={showLangfuseSecretKey ? "text" : "password"}
                          placeholder="Enter secret key"
                          value={settings.langfuseSecretKey}
                          onChange={(e) => setSettings(prev => ({ ...prev, langfuseSecretKey: e.target.value }))}
                          disabled={!settings.langfuseEnabled}
                          className="pr-10"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-2 top-2 h-6 w-6 p-0 hover:bg-transparent"
                          onClick={() => setShowLangfuseSecretKey(!showLangfuseSecretKey)}
                          disabled={!settings.langfuseEnabled}
                        >
                          {showLangfuseSecretKey ? (
                            <EyeOff className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <Eye className="h-4 w-4 text-muted-foreground" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Sample Rate
                      <Badge variant="outline">{settings.langfuseSampleRate}</Badge>
                    </Label>
                    <Slider
                      value={[settings.langfuseSampleRate]}
                      onValueChange={(value) => setSettings(prev => ({ ...prev, langfuseSampleRate: value[0] }))}
                      max={1}
                      min={0}
                      step={0.1}
                      className="w-full"
                      disabled={!settings.langfuseEnabled}
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>0% (None)</span>
                      <span>100% (All)</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Percentage of requests to track for analytics (0.0 to 1.0)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>











        </Tabs>

        {hasUnsavedChanges() && (
          <Alert>
            <AlertDescription>
              You have unsaved changes. Click "Save Changes" to apply them.
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  )
}
