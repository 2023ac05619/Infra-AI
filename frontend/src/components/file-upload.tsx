'use client'

import { useState, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Upload,
  FileText,
  File,
  X,
  CheckCircle,
  AlertCircle,
  Trash2,
  Download,
  Eye,
  UploadCloud,
  FolderOpen
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface UploadedFile {
  id: string
  filename: string
  status: 'uploading' | 'completed' | 'failed'
  size: number
  error?: string
  progress?: number
}

interface DocumentInfo {
  id: string
  filename: string
  total_chunks: number
  status: string
  path?: string
}

export function FileUpload() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  // Load existing documents on component mount
  const loadDocuments = useCallback(async () => {
    try {
      const response = await fetch('/api/upload')
      if (response.ok) {
        const data = await response.json()
        setDocuments(data.documents || [])
      }
    } catch (error) {
      console.error('Error loading documents:', error)
    }
  }, [])

  // Load documents on mount
  useState(() => {
    loadDocuments()
  })

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-red-500" />
      case 'docx':
        return <FileText className="w-4 h-4 text-blue-500" />
      case 'txt':
        return <File className="w-4 h-4 text-gray-500" />
      default:
        return <File className="w-4 h-4 text-gray-400" />
    }
  }

  const uploadFile = async (file: File) => {
    const fileId = `${Date.now()}-${file.name}`
    const uploadFile: UploadedFile = {
      id: fileId,
      filename: file.name,
      status: 'uploading',
      size: file.size,
      progress: 0
    }

    setUploadedFiles(prev => [...prev, uploadFile])
    setIsUploading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('collection', 'user_docs')

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Upload failed')
      }

      const result = await response.json()

      // Update file status
      setUploadedFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'completed' as const, progress: 100 }
          : f
      ))

      toast({
        title: 'Upload Successful',
        description: `${file.name} has been uploaded and is being processed.`,
      })

      // Reload documents list
      setTimeout(() => {
        loadDocuments()
      }, 2000)

    } catch (error) {
      console.error('Upload error:', error)
      setUploadedFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'failed' as const, error: error instanceof Error ? error.message : 'Upload failed' }
          : f
      ))

      toast({
        title: 'Upload Failed',
        description: error instanceof Error ? error.message : 'Upload failed',
        variant: 'destructive',
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return

    const validFiles: File[] = []
    const invalidFiles: string[] = []

    Array.from(files).forEach(file => {
      // Validate file type
      const allowedTypes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
      ]

      if (!allowedTypes.includes(file.type)) {
        invalidFiles.push(`${file.name} (${file.type})`)
        return
      }

      // Validate file size (10MB)
      const maxSize = 10 * 1024 * 1024
      if (file.size > maxSize) {
        invalidFiles.push(`${file.name} (${formatFileSize(file.size)})`)
        return
      }

      validFiles.push(file)
    })

    // Show warnings for invalid files
    if (invalidFiles.length > 0) {
      toast({
        title: 'Invalid Files',
        description: `These files were skipped: ${invalidFiles.join(', ')}`,
        variant: 'destructive',
      })
    }

    // Upload valid files
    validFiles.forEach(uploadFile)
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    handleFileSelect(e.dataTransfer.files)
  }, [])

  const removeUploadedFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const deleteDocument = async (docId: string) => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
      const response = await fetch(`${backendUrl}/documents/${docId}?collection=user_docs`, {
        method: 'DELETE',
      })

      if (response.ok) {
        toast({
          title: 'Document Deleted',
          description: 'Document has been removed from the knowledge base.',
        })
        loadDocuments()
      } else {
        throw new Error('Delete failed')
      }
    } catch (error) {
      toast({
        title: 'Delete Failed',
        description: 'Failed to delete document.',
        variant: 'destructive',
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-blue-500" />
            Upload Documents
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Drag and Drop Area */}
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragOver
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-muted-foreground/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-medium mb-2">Drop files here or click to browse</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Supports PDF, DOCX, and TXT files up to 10MB each
            </p>
            <div className="flex gap-2 justify-center">
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
              >
                <FolderOpen className="w-4 h-4 mr-2" />
                Choose Files
              </Button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
            />
          </div>

          {/* Upload Progress */}
          {uploadedFiles.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-medium">Upload Progress</h4>
              {uploadedFiles.map((file) => (
                <div key={file.id} className="flex items-center gap-3 p-3 border rounded-lg">
                  {getFileIcon(file.filename)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium truncate">{file.filename}</span>
                      <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                    </div>
                    {file.status === 'uploading' && (
                      <Progress value={file.progress || 0} className="mt-2" />
                    )}
                    {file.status === 'failed' && file.error && (
                      <p className="text-xs text-destructive mt-1">{file.error}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {file.status === 'completed' && <CheckCircle className="w-4 h-4 text-green-500" />}
                    {file.status === 'failed' && <AlertCircle className="w-4 h-4 text-red-500" />}
                    {file.status === 'uploading' && <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeUploadedFile(file.id)}
                      className="h-8 w-8 p-0"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Documents List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-green-500" />
            Uploaded Documents ({documents.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No documents uploaded yet</p>
              <p className="text-sm">Upload documents above to populate your knowledge base</p>
            </div>
          ) : (
            <ScrollArea className="h-96">
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      {getFileIcon(doc.filename)}
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{doc.filename}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {doc.total_chunks} chunks
                          </Badge>
                          <Badge
                            variant={doc.status === 'completed' ? 'default' : 'secondary'}
                            className="text-xs"
                          >
                            {doc.status}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteDocument(doc.id)}
                        className="h-8 w-8 p-0 text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Info Alert */}
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <strong>How it works:</strong> Uploaded documents are automatically processed through the RAG pipeline:
          text extraction → chunking → embedding → vector storage. They become immediately searchable
          in your chat when you ask questions containing relevant keywords.
        </AlertDescription>
      </Alert>
    </div>
  )
}
