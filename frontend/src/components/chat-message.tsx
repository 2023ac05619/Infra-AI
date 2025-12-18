'use client'

import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Copy, Play, ExternalLink } from 'lucide-react'
import { InlineMath, BlockMath } from 'react-katex'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

// Smart format detection and rendering
function detectContentFormat(content: string): 'json' | 'yaml' | 'csv' | 'tsv' | 'xml' | 'html-table' | 'markdown-table' | 'mermaid' | 'latex' | 'plaintext' {
  // JSON detection
  const trimmed = content.trim()
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    try {
      JSON.parse(trimmed)
      return 'json'
    } catch {}
  }

  // YAML detection (simple heuristic)
  if (trimmed.includes(': ') || trimmed.includes(': \n') ||
      /^\w+:\s*\w+/m.test(trimmed)) {
    return 'yaml'
  }

  // HTML table detection
  if (trimmed.includes('<table') && trimmed.includes('</table>')) {
    return 'html-table'
  }

  // XML detection
  if (trimmed.startsWith('<?xml') || trimmed.startsWith('<') && trimmed.includes('</')) {
    return 'xml'
  }

  // Mermaid diagram detection
  if (content.includes('graph') || content.includes('flowchart') ||
      content.includes('sequenceDiagram') || content.includes('gantt')) {
    return 'mermaid'
  }

  // LaTeX detection
  if (content.includes('\\begin{') || content.includes('\\end{') ||
      content.includes('\\int') || content.includes('\\sum') ||
      content.includes('\\frac{') || content.includes('\\sqrt{')) {
    return 'latex'
  }

  // CSV/TSV detection
  const lines = content.split('\n').filter(line => line.trim())
  if (lines.length >= 2) {
    // Check if first line looks like headers and others look like data
    const firstLine = lines[0]
    const hasConsistentDelimiter = firstLine.includes(',') || firstLine.includes('\t') || firstLine.includes(';')

    if (hasConsistentDelimiter) {
      // Check if we have similar number of delimiters in each line
      const delimiter = firstLine.includes(',') ? ',' : firstLine.includes('\t') ? '\t' : ';'
      const fieldCounts = lines.map(line => line.split(delimiter).length)
      const uniqueCounts = new Set(fieldCounts)

      if (uniqueCounts.size === 1 && fieldCounts[0] >= 2) {
        // Likely CSV or TSV
        return delimiter === '\t' ? 'tsv' : 'csv'
      }
    }
  }

  return 'plaintext'
}

// Render detected format beautifully
function renderDetectedFormat(content: string, format: string, onCopyToClipboard?: (text: string) => void) {
  const trimmedContent = content.trim()

  switch (format) {
    case 'json': {
      try {
        const parsed = JSON.parse(trimmedContent)
        const pretty = JSON.stringify(parsed, null, 2)
        return (
          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-600 dark:text-blue-400">JSON</span>
              {onCopyToClipboard && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onCopyToClipboard(pretty)}
                  className="h-6 w-6 p-0"
                >
                  <Copy className="w-3 h-3" />
                </Button>
              )}
            </div>
            <SyntaxHighlighter
              style={oneDark}
              language="json"
              className="!text-sm !bg-transparent"
            >
              {pretty}
            </SyntaxHighlighter>
          </div>
        )
      } catch (e) {
        return content // Fall back to plain text
      }
    }

    case 'yaml': {
      return (
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-purple-600 dark:text-purple-400">YAML</span>
            {onCopyToClipboard && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onCopyToClipboard(trimmedContent)}
                className="h-6 w-6 p-0"
              >
                <Copy className="w-3 h-3" />
              </Button>
            )}
          </div>
          <SyntaxHighlighter
            style={oneDark as any}
            language="yaml"
            className="!text-sm !bg-transparent"
          >
            {trimmedContent}
          </SyntaxHighlighter>
        </div>
      )
    }

    case 'csv':
    case 'tsv': {
      try {
        const delimiter = format === 'tsv' ? '\t' : ','
        const lines = trimmedContent.split('\n').filter(line => line.trim())
        const headers = lines[0].split(delimiter).map(h => h.trim().replace(/"/g, ''))
        const rows = lines.slice(1).map(line =>
          line.split(delimiter).map(cell => cell.trim().replace(/"/g, ''))
        ).filter(row => row.length > 0)

        return (
          <div className="overflow-x-auto my-4 border border-slate-200 dark:border-slate-700 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  {headers.map((header, index) => (
                    <th key={index} className="py-3 px-4 text-left font-semibold text-slate-900 dark:text-slate-100 uppercase text-xs tracking-wider">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700 bg-white dark:bg-slate-950">
                {rows.slice(0, 20).map((row, index) => (
                  <tr key={index}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex} className="py-3 px-4 text-slate-700 dark:text-slate-300">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 20 && (
              <div className="p-2 text-xs text-slate-500 bg-slate-50 dark:bg-slate-800 border-t">
                Showing 20 of {rows.length} rows
              </div>
            )}
          </div>
        )
      } catch (e) {
        return content
      }
    }

    case 'xml': {
      return (
        <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-green-600 dark:text-green-400">XML</span>
            {onCopyToClipboard && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onCopyToClipboard(trimmedContent)}
                className="h-6 w-6 p-0"
              >
                <Copy className="w-3 h-3" />
              </Button>
            )}
          </div>
          <SyntaxHighlighter
            style={oneDark}
            language="xml"
            className="!text-sm !bg-transparent"
          >
            {trimmedContent}
          </SyntaxHighlighter>
        </div>
      )
    }

    // Add more format handlers here...
    default:
      return null // Fall back to markdown rendering
  }
}

interface ChatMessageProps {
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  onRunCommand?: (command: string) => void
  onCopyToClipboard?: (text: string) => void
}

export function ChatMessage({
  content,
  role,
  timestamp,
  onRunCommand,
  onCopyToClipboard
}: ChatMessageProps) {

  // Pre-process malformed Markdown tables
  const fixMalformedMarkdownTable = (text: string): string => {
    // Check if this looks like a potential table
    const lines = text.split('\n').filter(line => line.trim())

    if (lines.length < 3) return text // Need at least header, separator, and one data row

    // Check for table-like pattern
    const firstLine = lines[0].trim()
    const secondLine = lines[1].trim()

    // Must start and end with | to be a table
    if (!firstLine.startsWith('|') || !firstLine.endsWith('|')) return text
    if (!secondLine.startsWith('|') || !secondLine.endsWith('|')) return text

    // Check if separator line has dashes (common in markdown tables)
    if (!secondLine.includes('---')) return text

    try {
      // Split into cells to analyze structure
      const headerCells = firstLine.split('|').filter((_, index, arr) =>
        index === 0 || index === arr.length - 1 ? false : true // Remove first and last empty elements
      )

      const separatorCells = secondLine.split('|').filter((_, index, arr) =>
        index === 0 || index === arr.length - 1 ? false : true
      )

      // If we have more header cells than separators, or vice versa, try to fix
      if (Math.abs(headerCells.length - separatorCells.length) <= 1) {
        // Create balanced table
        const maxColumns = Math.max(headerCells.length, separatorCells.length)

        // Balance header: remove extra empty cells
        const balancedHeader = headerCells.filter(cell => cell.trim() !== '').slice(0, maxColumns)
        const balancedHeaderLine = '| ' + balancedHeader.join(' | ') + ' |'

        // Balance separator
        const balancedSeparatorCells = new Array(maxColumns).fill('---')
        const balancedSeparator = '| ' + balancedSeparatorCells.join(' | ') + ' |'

        // Fix data rows to match the determined column count
        const fixedDataLines = lines.slice(2).map(line => {
          if (!line.trim().startsWith('|')) return line
          const dataCells = line.split('|').filter((_, index, arr) =>
            index === 0 || index === arr.length - 1 ? false : true
          ).filter(cell => cell.trim() !== '').slice(0, maxColumns)

          while (dataCells.length < maxColumns) {
            dataCells.push('')
          }

          return '| ' + dataCells.join(' | ') + ' |'
        }).filter(line => line !== '| ' + new Array(maxColumns).fill('').join(' | ') + ' |') // Remove empty rows

        // Return the fixed table
        return [balancedHeaderLine, balancedSeparator, ...fixedDataLines].join('\n')
      }

      return text // Table looks fine, return as-is
    } catch (e) {
      console.error('Table repair failed:', e)
      return text
    }
  }

  // Apply table repair to content
  const repairedContent = fixMalformedMarkdownTable(content)

  // Detect format for intelligent rendering
  const detectedFormat = detectContentFormat(repairedContent)

  // If it's a known structured format, render accordingly
  if (['json', 'yaml', 'csv', 'tsv', 'xml', 'html-table'].includes(detectedFormat)) {
    const rendered = renderDetectedFormat(content, detectedFormat, onCopyToClipboard)
    if (rendered) {
      return (
        <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}>
          <Card className={`w-fit max-w-prose py-0.5 ${role === 'user' ? 'bg-primary text-primary-foreground' : ''}`}>
            <CardContent className="p-4">
              <div className="markdown-content">
                {rendered}
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }
  }

  // Otherwise, default to markdown rendering
  return (
    <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'} w-full`}>
      <Card className={`w-fit max-w-prose py-0.5 ${role === 'user' ? 'bg-primary text-primary-foreground shadow-md' : ''}`}>
        <CardContent className="p-4">
          <div className="markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                h2({ children, ...props }) {
                  const content = String(children)
                  const emojiMatch = content.match(/^\s*(\d+️⃣|#️⃣||||)\s*(.+)$/)
                  if (emojiMatch) {
                    const [, emoji, title] = emojiMatch
                    return (
                      <h2 className="text-xl font-bold text-primary mt-6 mb-4 flex items-center gap-3" {...props}>
                        <span className="text-2xl">{emoji}</span>
                        <span>{title}</span>
                      </h2>
                    )
                  }
                  return (
                    <h2 className="text-xl font-bold text-primary mt-6 mb-4" {...props}>
                      {children}
                    </h2>
                  )
                },

                h3({ children, ...props }) {
                  return (
                    <h3 className="text-lg font-semibold text-foreground mt-4 mb-3" {...props}>
                      {children}
                    </h3>
                  )
                },

                p({ children, ...props }) {
                  return (
                    <p className="text-sm leading-relaxed text-muted-foreground mb-0 text-center text-justify" {...props}>
                      {children}
                    </p>
                  )
                },

                code({ node, className, children, ...props }: any) {
                  const inline = !node
                  const match = /language-(\w+)/.exec(className || '')
                  const codeContent = String(children).replace(/\n$/, '')

                  if (match && !inline) {
                    const language = match[1]

                    if (['bash', 'sh', 'shell', 'terminal', 'zsh', 'fish'].includes(language)) {
                      return (
                        <div className="relative bg-gradient-to-r from-slate-900 to-slate-800 rounded-lg p-4 font-mono text-sm overflow-x-auto border border-slate-700 shadow-md">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                              <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">{language}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              {onRunCommand && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => onRunCommand(codeContent.replace(/^\$?\s*/gm, '').trim())}
                                  className="h-6 w-6 p-0 hover:bg-green-700 hover:text-white text-slate-400"
                                  title="Run command"
                                >
                                  <Play className="w-3 h-3" />
                                </Button>
                              )}
                              {onCopyToClipboard && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => onCopyToClipboard(codeContent.replace(/^\$?\s*/gm, '').trim())}
                                  className="h-6 w-6 p-0 hover:bg-slate-600 hover:text-white text-slate-400"
                                  title="Copy command"
                                >
                                  <Copy className="w-3 h-3" />
                                </Button>
                              )}
                            </div>
                          </div>
                          <SyntaxHighlighter
                            style={oneDark}
                            language={language}
                            PreTag="div"
                            customStyle={{ background: 'transparent', margin: 0, padding: 0 }}
                            className="!bg-transparent !m-0 !p-0"
                          >
                            {codeContent}
                          </SyntaxHighlighter>
                        </div>
                      )
                    }

                    return (
                      <div className="relative">
                        <div className="absolute top-3 right-3 text-xs font-medium uppercase tracking-wider bg-slate-800 text-slate-400 px-2 py-1 rounded z-10">
                          {language}
                        </div>
                        <SyntaxHighlighter
                          style={oneDark}
                          language={language}
                          PreTag="div"
                          className="rounded-lg !bg-slate-900 !border !border-slate-700"
                        >
                          {codeContent}
                        </SyntaxHighlighter>
                      </div>
                    )
                  }

                  const codeText = String(children)
                  if (/^\$[^$]+\$$/.test(codeText)) {
                    return <InlineMath math={codeText.slice(1, -1)} />
                  }
                  if (/^\$\$[^$]+\$\$/.test(codeText)) {
                    return <div className="my-4 flex justify-center"><BlockMath math={codeText.slice(2, -2)} /></div>
                  }

                  return (
                    <code className="bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>
                      {children}
                    </code>
                  )
                },

                // MARKDOWN TABLES - Beautiful rendering for proper GFM tables
                table({ children, ...props }) {
                  console.log(' Markdown table rendered:', children)
                  return (
                    <div className="overflow-x-auto my-4 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-950">
                      <table className="w-full text-sm border-collapse" {...props}>
                        {children}
                      </table>
                    </div>
                  )
                },

                thead({ children, ...props }) {
                  return (
                    <thead className="bg-orange-50 dark:bg-orange-950 border-b-2 border-orange-200 dark:border-orange-800" {...props}>
                      {children}
                    </thead>
                  )
                },

                th({ children, ...props }) {
                  return (
                    <th className="py-3 px-4 text-left font-semibold text-orange-900 dark:text-orange-100 uppercase text-xs tracking-wider" {...props}>
                      {children}
                    </th>
                  )
                },

                tbody({ children, ...props }) {
                  return (
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700" {...props}>
                      {children}
                    </tbody>
                  )
                },

                td({ children, ...props }) {
                  return (
                    <td className="py-3 px-4 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800" {...props}>
                      {children}
                    </td>
                  )
                },
              }}
            >
              {repairedContent}
            </ReactMarkdown>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export function DataRenderer({ data, type }: { data: any, type: string }) {
  return renderDetectedFormat(typeof data === 'string' ? data : JSON.stringify(data), type)
}
