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
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Loader2, Cpu, Network, Database, Search, Activity, CheckCircle, XCircle, AlertTriangle, RefreshCw, Play, Pause, Settings, Home, Save, Zap, FileText, BarChart3, Eye, TestTube } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface ScanResult {
  scan_type: string
  timestamp: string
  documents_produced: number
  targets_discovered?: number
  errors: string[]
  status: 'running' | 'completed' | 'failed' | 'idle'
  progress?: number
  message?: string
}

interface SystemStatus {
  status: string
  qdrant?: {
    collection?: string
    vectors?: number
    status?: string
  }
  last_scan?: {
    type: string
    timestamp: string
    documents_produced: number
  }
  scheduled_jobs?: Array<{
    id: string
    name: string
    next_run: string
    status: string
  }>
}

interface BackendSettings {
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

export default function AIEnginePage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { toast } = useToast()

  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [isLoadingStatus, setIsLoadingStatus] = useState(true)
  const [currentScan, setCurrentScan] = useState<ScanResult | null>(null)
  const [scanHistory, setScanHistory] = useState<ScanResult[]>([])
  const [isScanning, setIsScanning] = useState(false)

  // Backend settings state
  const [settings, setSettings] = useState<BackendSettings>({
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

  const [originalSettings, setOriginalSettings] = useState<BackendSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [isTestingOllama, setIsTestingOllama] = useState(false)
  const [ollamaTestResult, setOllamaTestResult] = useState<OllamaTestResult | null>(null)

  useEffect(() => {
    if (status === 'loading') return
    if (!session) {
      router.push('/auth/signin')
      return
    }
    loadSystemStatus()
    loadScanHistory()
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
        originalSettings && settings[field as keyof BackendSettings] !== originalSettings[field as keyof BackendSettings]
      ) || llmModelChanged

      if (backendSettingsChanged) {
        // Apply backend settings
        const backendPayload = backendFields.reduce((acc, field) => {
          const value = settings[field as keyof BackendSettings]
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

  const validateUrl = (url: string) => {
    try {
      new URL(url)
      return true
    } catch {
      return false
    }
  }

  const loadSystemStatus = async () => {
    try {
      const response = await fetch('/api/v1/status')
      if (response.ok) {
        const data = await response.json()
        setSystemStatus(data)
      }
    } catch (error) {
      console.error('Error loading system status:', error)
    } finally {
      setIsLoadingStatus(false)
    }
  }

  const loadScanHistory = async () => {
    // Load recent scan history from local storage or API
    try {
      const history = localStorage.getItem('scanHistory')
      if (history) {
        setScanHistory(JSON.parse(history))
      }
    } catch (error) {
      console.error('Error loading scan history:', error)
    }
  }

  const saveScanHistory = (scan: ScanResult) => {
    const updatedHistory = [scan, ...scanHistory.slice(0, 9)] // Keep last 10 scans
    setScanHistory(updatedHistory)
    localStorage.setItem('scanHistory', JSON.stringify(updatedHistory))
  }

  const triggerScan = async (scanType: string) => {
    if (isScanning) return

    setIsScanning(true)
    const scanResult: ScanResult = {
      scan_type: scanType,
      timestamp: new Date().toISOString(),
      documents_produced: 0,
      status: 'running',
      progress: 0,
      errors: []
    }

    setCurrentScan(scanResult)

    try {
      const response = await fetch('/api/v1/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: scanType })
      })

      const result = await response.json()

      if (response.ok) {
        scanResult.status = 'completed'
        scanResult.documents_produced = result.documents_produced || 0
        scanResult.targets_discovered = result.targets_discovered || 0
        scanResult.message = result.message || 'Scan completed successfully'

        toast({
          title: 'Scan Completed',
          description: `${scanType.toUpperCase()} scan finished. ${scanResult.documents_produced} documents produced.`,
        })
      } else {
        scanResult.status = 'failed'
        scanResult.errors = [result.detail || 'Scan failed']
        scanResult.message = result.detail || 'Scan failed'

        toast({
          title: 'Scan Failed',
          description: result.detail || 'Scan failed',
          variant: 'destructive',
        })
      }
    } catch (error) {
      console.error('Scan error:', error)
      scanResult.status = 'failed'
      scanResult.errors = [error instanceof Error ? error.message : 'Unknown error']
      scanResult.message = 'Network error during scan'

      toast({
        title: 'Scan Failed',
        description: 'Network error during scan',
        variant: 'destructive',
      })
    } finally {
      scanResult.progress = 100
      setCurrentScan(scanResult)
      saveScanHistory(scanResult)
      setIsScanning(false)

      // Refresh system status after scan
      setTimeout(loadSystemStatus, 2000)
    }
  }

  const getScanDescription = (scanType: string) => {
    switch (scanType) {
      case 'full':
        return 'Complete infrastructure scan including network probing, Prometheus metrics, and Loki logs'
      case 'quick':
        return 'Fast scan of Prometheus and Loki data without network probing'
      case 'prom-only':
        return 'Prometheus-only scan for metrics and targets'
      default:
        return 'Unknown scan type'
    }
  }

  const getScanIcon = (scanType: string) => {
    switch (scanType) {
      case 'full':
        return <Network className="w-5 h-5" />
      case 'quick':
        return <Activity className="w-5 h-5" />
      case 'prom-only':
        return <Database className="w-5 h-5" />
      default:
        return <Search className="w-5 h-5" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-500'
      case 'completed':
        return 'bg-green-500'
      case 'failed':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  if (status === 'loading' || isLoadingStatus) {
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
                <Cpu className="w-5 h-5 text-primary-foreground" />
              </div>
              <h1 className="text-xl font-bold">Backend AI Engine</h1>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                onClick={() => router.push('/settings')}
                className="flex items-center gap-2"
              >
                <Settings className="w-4 h-4" />
                Settings
              </Button>
              <Button
                variant="outline"
                onClick={() => router.push('/')}
                className="flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                Home
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-6">
        <Tabs defaultValue="scanning" className="space-y-6">
          <div className="w-full overflow-x-auto">
            <TabsList className="inline-flex h-12 items-center justify-start rounded-lg bg-muted p-1 text-muted-foreground w-full">
              <TabsTrigger
                value="scanning"
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm gap-2 flex-1 min-w-0"
              >
                <Play className="w-4 h-4 text-blue-500" />
                Scanning
              </TabsTrigger>
              <TabsTrigger
                value="ai-config"
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm gap-2 flex-1 min-w-0"
              >
                <Cpu className="w-4 h-4 text-orange-500" />
                AI Config
              </TabsTrigger>
              <TabsTrigger
                value="monitoring"
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm gap-2 flex-1 min-w-0"
              >
                <Eye className="w-4 h-5 text-green-500" />
                Monitoring
              </TabsTrigger>
              <TabsTrigger
                value="server"
                className="inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm gap-2 flex-1 min-w-0"
              >
                <Settings className="w-4 h-4 text-gray-500" />
                Server
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Scanning Tab */}
          <TabsContent value="scanning" className="space-y-6">
            {/* System Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-green-500" />
                  System Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${systemStatus?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
                    <div>
                      <p className="font-medium">Backend Status</p>
                      <p className="text-sm text-muted-foreground capitalize">{systemStatus?.status || 'Unknown'}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Database className="w-5 h-5 text-blue-500" />
                    <div>
                      <p className="font-medium">Qdrant Database</p>
                      <p className="text-sm text-muted-foreground">
                        {systemStatus?.qdrant?.vectors || 0} vectors
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <RefreshCw className="w-5 h-5 text-orange-500" />
                    <div>
                      <p className="font-medium">Last Scan</p>
                      <p className="text-sm text-muted-foreground">
                        {systemStatus?.last_scan ?
                          `${systemStatus.last_scan.type} (${systemStatus.last_scan.documents_produced} docs)` :
                          'Never'
                        }
                      </p>
                    </div>
                  </div>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadSystemStatus}
                  className="w-fit"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh Status
                </Button>
              </CardContent>
            </Card>

            {/* Scan Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Play className="w-5 h-5 text-blue-500" />
                  Network Scanning Controls
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Full Scan */}
                  <Card className="border-2 hover:border-blue-500 transition-colors">
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-lg">
                        {getScanIcon('full')}
                        Full Infrastructure Scan
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground">
                        Complete scan including network probing, Prometheus metrics, and Loki logs
                      </p>
                      <Button
                        onClick={() => triggerScan('full')}
                        disabled={isScanning}
                        className="w-full"
                      >
                        {isScanning && currentScan?.scan_type === 'full' ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Network className="w-4 h-4 mr-2" />
                        )}
                        Start Full Scan
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Quick Scan */}
                  <Card className="border-2 hover:border-green-500 transition-colors">
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-lg">
                        {getScanIcon('quick')}
                        Quick Scan
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground">
                        Fast scan of Prometheus and Loki data without network probing
                      </p>
                      <Button
                        onClick={() => triggerScan('quick')}
                        disabled={isScanning}
                        variant="outline"
                        className="w-full"
                      >
                        {isScanning && currentScan?.scan_type === 'quick' ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Activity className="w-4 h-4 mr-2" />
                        )}
                        Start Quick Scan
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Prometheus Only */}
                  <Card className="border-2 hover:border-purple-500 transition-colors">
                    <CardHeader className="pb-3">
                      <CardTitle className="flex items-center gap-2 text-lg">
                        {getScanIcon('prom-only')}
                        Prometheus Only
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground">
                        Scan only Prometheus targets and metrics data
                      </p>
                      <Button
                        onClick={() => triggerScan('prom-only')}
                        disabled={isScanning}
                        variant="outline"
                        className="w-full"
                      >
                        {isScanning && currentScan?.scan_type === 'prom-only' ? (
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Database className="w-4 h-4 mr-2" />
                        )}
                        Start Metrics Scan
                      </Button>
                    </CardContent>
                  </Card>
                </div>

                {/* Current Scan Progress */}
                {currentScan && (
                  <div className="space-y-3">
                    <Separator />
                    <div className="flex items-center justify-between">
                      <h3 className="font-medium">Current Scan Progress</h3>
                      <Badge className={getStatusColor(currentScan.status)}>
                        {currentScan.status.toUpperCase()}
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>{currentScan.scan_type.toUpperCase()} Scan</span>
                        <span>{currentScan.progress || 0}%</span>
                      </div>
                      <Progress value={currentScan.progress || 0} className="w-full" />
                    </div>

                    {currentScan.message && (
                      <Alert>
                        <AlertDescription>{currentScan.message}</AlertDescription>
                      </Alert>
                    )}

                    {currentScan.errors.length > 0 && (
                      <Alert variant="destructive">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>
                          {currentScan.errors.join(', ')}
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Scan History */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="w-5 h-5 text-indigo-500" />
                  Scan History
                </CardTitle>
              </CardHeader>
              <CardContent>
                {scanHistory.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">
                    No scans performed yet. Start your first scan above.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {scanHistory.map((scan, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          {getScanIcon(scan.scan_type)}
                          <div>
                            <p className="font-medium capitalize">{scan.scan_type} Scan</p>
                            <p className="text-sm text-muted-foreground">
                              {new Date(scan.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <p className="text-sm font-medium">
                              {scan.documents_produced} documents
                            </p>
                            {scan.targets_discovered && (
                              <p className="text-xs text-muted-foreground">
                                {scan.targets_discovered} targets found
                              </p>
                            )}
                          </div>

                          <Badge className={getStatusColor(scan.status)}>
                            {scan.status === 'completed' ? (
                              <CheckCircle className="w-3 h-3 mr-1" />
                            ) : scan.status === 'failed' ? (
                              <XCircle className="w-3 h-3 mr-1" />
                            ) : null}
                            {scan.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* AI Engine Info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-purple-500" />
                  AI Engine Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-medium mb-2">Available Scan Types</h4>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                      <li><strong>Full Scan:</strong> Network probing + Prometheus + Loki</li>
                      <li><strong>Quick Scan:</strong> Prometheus + Loki only (no network)</li>
                      <li><strong>Prometheus Only:</strong> Metrics and targets only</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-medium mb-2">AI Components</h4>
                    <ul className="space-y-1 text-sm text-muted-foreground">
                      <li><strong>RAG Pipeline:</strong> Retrieval-augmented generation</li>
                      <li><strong>Embedding Model:</strong> Sentence transformers</li>
                      <li><strong>LLM:</strong> Ollama-powered text generation</li>
                      <li><strong>Vector DB:</strong> Qdrant for document storage</li>
                    </ul>
                  </div>
                </div>

                <Alert>
                  <AlertDescription>
                    Scans automatically process and index infrastructure data for AI-powered queries.
                    Use the chat interface to ask questions about your infrastructure after scanning.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI Configuration Tab */}
          <TabsContent value="ai-config" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  AI Provider Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-base font-medium">AI Provider</Label>
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 bg-primary rounded-full"></div>
                      <Label className="text-sm font-medium">Ollama (Local)</Label>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="ollamaUrl">Ollama Server URL</Label>
                      <div className="flex gap-2">
                        <Input
                          id="ollamaUrl"
                          placeholder="http://192.168.200.201:11434"
                          value={settings.ollamaUrl}
                          onChange={(e) => setSettings(prev => ({ ...prev, ollamaUrl: e.target.value }))}
                          className={settings.ollamaUrl && !validateUrl(settings.ollamaUrl) ? 'border-destructive' : ''}
                        />
                        <Button
                          type="button"
                          variant="outline"
                          onClick={testOllamaConnection}
                          disabled={isTestingOllama || !settings.ollamaUrl?.trim()}
                        >
                          {isTestingOllama ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <TestTube className="w-4 h-4" />
                          )}
                          Test
                        </Button>
                      </div>
                      {settings.ollamaUrl && !validateUrl(settings.ollamaUrl) && (
                        <p className="text-sm text-destructive">Please enter a valid URL</p>
                      )}
                    </div>

                    {ollamaTestResult && (
                      <Alert className={ollamaTestResult.success ? 'border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950' : 'border-destructive bg-red-50 dark:bg-red-950'}>
                        {ollamaTestResult.success ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <AlertDescription className={ollamaTestResult.success ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'}>
                          {ollamaTestResult.success
                            ? `Connection successful! Found ${ollamaTestResult.models?.length || 0} models.`
                            : `Connection failed: ${ollamaTestResult.error}`
                          }
                        </AlertDescription>
                      </Alert>
                    )}

                    {ollamaModels.length > 0 && (
                      <div className="space-y-2">
                        <Label htmlFor="ollamaModel">Model</Label>
                        <Select
                          value={settings.ollamaModel}
                          onValueChange={(value) => setSettings(prev => ({ ...prev, ollamaModel: value }))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select a model" />
                          </SelectTrigger>
                          <SelectContent>
                            {ollamaModels.map((model: any) => (
                              <SelectItem key={model.name} value={model.name}>
                                {model.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-orange-500" />
                  LLM Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="llmModel">LLM Model</Label>
                    <Select
                      value={settings.llmModel}
                      onValueChange={(value) => setSettings(prev => ({ ...prev, llmModel: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select LLM model" />
                      </SelectTrigger>
                      <SelectContent>
                        {ollamaModels.length > 0 ? ollamaModels.map((model: any) => (
                          <SelectItem key={model.name} value={model.name}>
                            {model.name}
                          </SelectItem>
                        )) : (
                          <SelectItem disabled value="placeholder">
                            Configure and test Ollama server first
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Primary language model from your configured Ollama server
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      LLM Temperature
                      <Badge variant="outline">{settings.llmTemperature}</Badge>
                    </Label>
                    <Slider
                      value={[settings.llmTemperature]}
                      onValueChange={(value) => setSettings(prev => ({ ...prev, llmTemperature: value[0] }))}
                      max={2}
                      min={0}
                      step={0.1}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Backend LLM temperature (0-2 scale)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="embeddingModel">Embedding Model</Label>
                    <Select
                      value={settings.embeddingModel}
                      onValueChange={(value) => setSettings(prev => ({ ...prev, embeddingModel: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select embedding model" />
                      </SelectTrigger>
                      <SelectContent>
                        {ollamaModels.length > 0 ? ollamaModels.map((model: any) => (
                          <SelectItem key={model.name} value={model.name}>
                            {model.name}
                          </SelectItem>
                        )) : (
                          <SelectItem disabled value="placeholder">
                            Configure and test Ollama server first
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Embedding model from your configured Ollama server
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Chat Temperature
                      <Badge variant="outline">{settings.temperature}</Badge>
                    </Label>
                    <Slider
                      value={[settings.temperature]}
                      onValueChange={(value) => setSettings(prev => ({ ...prev, temperature: value[0] }))}
                      max={2}
                      min={0}
                      step={0.1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Precise</span>
                      <span>Creative</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Controls creativity of AI responses (0-2 scale)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-blue-500" />
                  Backend AI Model Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="embedModelName">Embedding Model Name</Label>
                    <Input
                      id="embedModelName"
                      placeholder="sentence-transformers/all-MiniLM-L6-v2"
                      value={settings.embedModelName}
                      onChange={(e) => setSettings(prev => ({ ...prev, embedModelName: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Model used for generating text embeddings
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Max New Tokens
                      <Badge variant="outline">{settings.maxNewTokens}</Badge>
                    </Label>
                    <Input
                      type="number"
                      min="50"
                      max="2048"
                      value={settings.maxNewTokens}
                      onChange={(e) => setSettings(prev => ({ ...prev, maxNewTokens: parseInt(e.target.value) || 512 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum tokens to generate in LLM responses (50-2048)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-cyan-500" />
                  Document Processing
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Chunk Size
                      <Badge variant="outline">{settings.chunkSize}</Badge>
                    </Label>
                    <Input
                      type="number"
                      min="100"
                      max="2000"
                      value={settings.chunkSize}
                      onChange={(e) => setSettings(prev => ({ ...prev, chunkSize: parseInt(e.target.value) || 512 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Size of text chunks for processing (100-2000 tokens)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Chunk Overlap
                      <Badge variant="outline">{settings.chunkOverlap}</Badge>
                    </Label>
                    <Input
                      type="number"
                      min="0"
                      max="200"
                      value={settings.chunkOverlap}
                      onChange={(e) => setSettings(prev => ({ ...prev, chunkOverlap: parseInt(e.target.value) || 50 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Overlap between chunks for better context (0-200 tokens)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-pink-500" />
                  Vector Database Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="qdrantUrl">Qdrant URL</Label>
                    <Input
                      id="qdrantUrl"
                      placeholder="http://localhost:6333"
                      value={settings.qdrantUrl}
                      onChange={(e) => setSettings(prev => ({ ...prev, qdrantUrl: e.target.value }))}
                      className={settings.qdrantUrl && !validateUrl(settings.qdrantUrl) ? 'border-destructive' : ''}
                    />
                    <p className="text-xs text-muted-foreground">
                      Vector database endpoint for document storage and retrieval
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="qdrantApiKey">Qdrant API Key</Label>
                    <Input
                      id="qdrantApiKey"
                      type="password"
                      placeholder="Enter API key for cloud instance"
                      value={settings.qdrantApiKey}
                      onChange={(e) => setSettings(prev => ({ ...prev, qdrantApiKey: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Required for cloud Qdrant instances (optional for local)
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-1">
                        <Label htmlFor="qdrantUseCloud">Use Qdrant Cloud</Label>
                        <p className="text-sm text-muted-foreground">
                          Enable for cloud-hosted Qdrant instance
                        </p>
                      </div>
                      <Switch
                        id="qdrantUseCloud"
                        checked={settings.qdrantUseCloud}
                        onCheckedChange={(checked) => setSettings(prev => ({ ...prev, qdrantUseCloud: checked }))}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="defaultCollection">Default Collection</Label>
                      <Input
                        id="defaultCollection"
                        placeholder="documents"
                        value={settings.defaultCollection}
                        onChange={(e) => setSettings(prev => ({ ...prev, defaultCollection: e.target.value }))}
                      />
                      <p className="text-xs text-muted-foreground">
                        Name of the collection to store document vectors
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  Network Scanning Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="networkCidr">Network CIDR Range</Label>
                    <Input
                      id="networkCidr"
                      placeholder="192.168.1.0/24"
                      value={settings.networkCidr}
                      onChange={(e) => setSettings(prev => ({ ...prev, networkCidr: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      CIDR notation for network range to scan (e.g., 192.168.1.0/24)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="scanCron">Scan Cron Schedule</Label>
                    <Input
                      id="scanCron"
                      placeholder="0 */1 * * *"
                      value={settings.scanCron}
                      onChange={(e) => setSettings(prev => ({ ...prev, scanCron: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Cron expression for scheduled network scans (leave empty to disable cron)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Scan Interval (Minutes)
                      <Badge variant="outline">{settings.scanIntervalMinutes}</Badge>
                    </Label>
                    <Input
                      type="number"
                      min="5"
                      max="1440"
                      value={settings.scanIntervalMinutes}
                      onChange={(e) => setSettings(prev => ({ ...prev, scanIntervalMinutes: parseInt(e.target.value) || 60 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Interval between automatic scans in minutes (5-1440)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-cyan-500" />
                  Backend RAG Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label className="flex items-center justify-between">
                      Top K Retrieval
                      <Badge variant="outline">{settings.topKRetrieval}</Badge>
                    </Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={settings.topKRetrieval}
                      onChange={(e) => setSettings(prev => ({ ...prev, topKRetrieval: parseInt(e.target.value) || 6 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Number of top documents to retrieve for RAG (1-20)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="chunkSize">Backend Chunk Size</Label>
                    <Input
                      type="number"
                      min="100"
                      max="2000"
                      value={settings.chunkSize}
                      onChange={(e) => setSettings(prev => ({ ...prev, chunkSize: parseInt(e.target.value) || 512 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Size of text chunks for backend document processing
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="chunkOverlap">Backend Chunk Overlap</Label>
                    <Input
                      type="number"
                      min="0"
                      max="200"
                      value={settings.chunkOverlap}
                      onChange={(e) => setSettings(prev => ({ ...prev, chunkOverlap: parseInt(e.target.value) || 50 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Overlap between chunks for backend processing
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {hasUnsavedChanges() && (
              <Alert>
                <AlertDescription>
                  You have unsaved changes. Click "Save Changes" to apply them.
                </AlertDescription>
              </Alert>
            )}

            <div className="flex justify-end gap-2">
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
          </TabsContent>

          {/* Monitoring Tab */}
          <TabsContent value="monitoring" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="w-5 h-5 text-green-500" />
                  External Monitoring Services
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="prometheusUrl">Prometheus URL</Label>
                    <Input
                      id="prometheusUrl"
                      placeholder="http://192.168.203.103:8080"
                      value={settings.prometheusUrl}
                      onChange={(e) => setSettings(prev => ({ ...prev, prometheusUrl: e.target.value }))}
                      className={settings.prometheusUrl && !validateUrl(settings.prometheusUrl) ? 'border-destructive' : ''}
                    />
                    <p className="text-xs text-muted-foreground">
                      URL of your Prometheus monitoring server for metrics collection
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="lokiUrl">Loki URL</Label>
                    <Input
                      id="lokiUrl"
                      placeholder="http://localhost:3100"
                      value={settings.lokiUrl}
                      onChange={(e) => setSettings(prev => ({ ...prev, lokiUrl: e.target.value }))}
                      className={settings.lokiUrl && !validateUrl(settings.lokiUrl) ? 'border-destructive' : ''}
                    />
                    <p className="text-xs text-muted-foreground">
                      URL of your Loki logging server for log aggregation
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Server Tab */}
          <TabsContent value="server" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5 text-gray-500" />
                  Backend Server Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="postgresUrl">PostgreSQL Database URL</Label>
                    <Input
                      id="postgresUrl"
                      type="password"
                      placeholder="postgresql://user:pass@localhost:5432/infra_rag"
                      value={settings.postgresUrl}
                      onChange={(e) => setSettings(prev => ({ ...prev, postgresUrl: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      PostgreSQL connection string for backend database
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="redisUrl">Redis URL</Label>
                    <Input
                      id="redisUrl"
                      placeholder="redis://localhost:6379"
                      value={settings.redisUrl}
                      onChange={(e) => setSettings(prev => ({ ...prev, redisUrl: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Redis connection URL for queue management (optional)
                    </p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label htmlFor="useRedisQueue">Use Redis Queue</Label>
                      <p className="text-sm text-muted-foreground">
                        Enable Redis for document processing queue (requires Redis URL)
                      </p>
                    </div>
                    <Switch
                      id="useRedisQueue"
                      checked={settings.useRedisQueue}
                      onCheckedChange={(checked) => setSettings(prev => ({ ...prev, useRedisQueue: checked }))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="queueDir">Local Queue Directory</Label>
                    <Input
                      id="queueDir"
                      placeholder="./queue"
                      value={settings.queueDir}
                      onChange={(e) => setSettings(prev => ({ ...prev, queueDir: e.target.value }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Directory for local document queue when Redis is disabled
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="logLevel">Log Level</Label>
                    <Select
                      value={settings.logLevel}
                      onValueChange={(value) => setSettings(prev => ({ ...prev, logLevel: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="DEBUG">DEBUG</SelectItem>
                        <SelectItem value="INFO">INFO</SelectItem>
                        <SelectItem value="WARNING">WARNING</SelectItem>
                        <SelectItem value="ERROR">ERROR</SelectItem>
                        <SelectItem value="CRITICAL">CRITICAL</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Backend logging level (changes require server restart)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
