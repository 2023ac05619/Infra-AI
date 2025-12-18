import express from "express";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import http from "http";
import { kubectlGet } from "../tools/kubectl-get.js";
import { ping } from "../tools/ping.js";
import { KubernetesManager } from "../types.js";



// Simple HTTP JSON-RPC server for MCP
// This provides a basic stateless HTTP endpoint for JSON-RPC requests
export async function startSimpleHTTPJSONRPCServer(server: Server): Promise<http.Server> {
  const app = express();
  app.use(express.json());

  app.post("/jsonrpc", async (req: express.Request, res: express.Response) => {
    try {
      const request = req.body;

      if (!request || !request.method) {
        return res.status(400).json({
          jsonrpc: "2.0",
          error: {
            code: -32600,
            message: "Invalid Request",
          },
          id: request?.id || null,
        });
      }

      let result;

      // Handle MCP methods with basic responses
      switch (request.method) {
        case "initialize":
          result = {
            protocolVersion: "2024-11-05",
            capabilities: {
              tools: { listChanged: true },
              resources: {},
              prompts: {},
            },
            serverInfo: {
              name: "kubernetes",
              version: "0.1.0",
            },
          };
          break;

        case "tools/list":
          result = {
            tools: [
              {
                name: "kubectl_get",
                description: "Get Kubernetes resources",
                inputSchema: {
                  type: "object",
                  properties: {
                    resourceType: { type: "string" },
                    namespace: { type: "string" },
                    output: { type: "string", enum: ["json", "yaml"] }
                  }
                }
              },
              {
                name: "ping",
                description: "Test server connectivity",
                inputSchema: { type: "object", properties: {} }
              }
            ]
          };
          break;

        case "tools/call":
          result = await handleToolCall(request.params);
          break;

        case "resources/list":
          result = {
            resources: [
              {
                uri: "k8s://default/pods",
                name: "Kubernetes Pods",
                description: "List of pods in the default namespace"
              }
            ]
          };
          break;

        case "resources/read":
          result = {
            contents: [{
              uri: request.params?.uri || "k8s://default/pods",
              mimeType: "application/json",
              text: JSON.stringify({ message: "Resource reading not fully implemented yet" })
            }]
          };
          break;

        default:
          return res.status(400).json({
            jsonrpc: "2.0",
            error: {
              code: -32601,
              message: "Method not found",
            },
            id: request.id,
          });
      }

      res.json({
        jsonrpc: "2.0",
        result,
        id: request.id,
      });
    } catch (error) {
      console.error("Error handling JSON-RPC request:", error);
      if (!res.headersSent) {
        res.status(500).json({
          jsonrpc: "2.0",
          error: {
            code: -32603,
            message: "Internal server error",
          },
          id: req.body?.id || null,
        });
      }
    }
  });

  // Helper function to handle basic tool calls
  async function handleToolCall(params: any) {
    const { name, arguments: input = {} } = params;

    // Create a Kubernetes manager instance for tool calls
    const k8sManager = {} as KubernetesManager; // Mock manager - real implementation would initialize properly

    switch (name) {
      case "ping":
        try {
          const result = await ping();
          return result;
        } catch (error: any) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                error: `Ping failed: ${error.message}`,
                timestamp: new Date().toISOString()
              })
            }],
            isError: true
          };
        }

      case "kubectl_get":
        try {
          // Call the real kubectlGet function
          const result = await kubectlGet(k8sManager, input);
          return result;
        } catch (error: any) {
          console.error("kubectl_get error:", error);
          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                error: `kubectl get failed: ${error.message}`,
                command: "kubectl",
                input: input
              })
            }],
            isError: true
          };
        }

      default:
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              error: `Tool '${name}' not fully implemented yet`,
              requestedTool: name,
              input: input
            })
          }]
        };
    }
  }

  app.get("/health", async (req: express.Request, res: express.Response) => {
    res.json({ status: "ok" });
  });

  app.get("/ready", async (req: express.Request, res: express.Response) => {
    try {
      res.json({
        status: "ready",
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      console.error("Readiness check failed:", error);
      res.status(503).json({
        status: "not ready",
        reason: "Server initialization incomplete",
        timestamp: new Date().toISOString()
      });
    }
  });

  let port = 3000;
  try {
    port = parseInt(process.env.PORT || "3000", 10);
  } catch (e) {
    console.error(
      "Invalid PORT environment variable, using default port 3000."
    );
  }

  const host = process.env.HOST || "localhost";
  const httpServer = app.listen(port, host, () => {
    console.log(
      `mcp-kubernetes-server is listening on port ${port}\nUse the following url to connect to the server:\nhttp://${host}:${port}/jsonrpc`
    );
  });
  return httpServer;
}
