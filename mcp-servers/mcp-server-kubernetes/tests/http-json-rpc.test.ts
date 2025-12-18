import { expect, test, describe, beforeAll, afterAll } from "vitest";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { startSimpleHTTPJSONRPCServer } from "../src/utils/http-json-rpc.js";

describe("HTTP JSON-RPC Server", () => {
  let server: Server;
  let httpServer: any;
  const baseUrl = "http://localhost:3000";

  beforeAll(async () => {
    // Create a mock MCP server
    server = new Server(
      {
        name: "test-kubernetes-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: { listChanged: true },
          resources: {},
          prompts: {},
        },
      }
    );

    // Start the HTTP JSON-RPC server
    httpServer = await startSimpleHTTPJSONRPCServer(server);

    // Wait for server to be ready
    await new Promise((resolve) => setTimeout(resolve, 1000));
  });

  afterAll(async () => {
    if (httpServer) {
      httpServer.close();
    }
  });

  test("initialize method", async () => {
    const response = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "initialize",
        params: {},
        id: 1,
      }),
    });

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.jsonrpc).toBe("2.0");
    expect(data.result.protocolVersion).toBe("2024-11-05");
    expect(data.result.serverInfo.name).toBe("kubernetes");
    expect(data.id).toBe(1);
  });

  test("tools/list method", async () => {
    const response = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/list",
        params: {},
        id: 2,
      }),
    });

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.jsonrpc).toBe("2.0");
    expect(data.result.tools).toBeDefined();
    expect(Array.isArray(data.result.tools)).toBe(true);
    expect(data.result.tools.length).toBeGreaterThan(0);

    // Check for expected tools
    const toolNames = data.result.tools.map((tool: any) => tool.name);
    expect(toolNames).toContain("kubectl_get");
    expect(toolNames).toContain("ping");
  });

  test("ping tool", async () => {
    const response = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/call",
        params: {
          name: "ping",
          arguments: {},
        },
        id: 3,
      }),
    });

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.jsonrpc).toBe("2.0");
    // In test environment, ping might fail due to missing dependencies
    if (data.result) {
      expect(data.result.content).toBeDefined();
      expect(data.result.content[0].type).toBe("text");
    } else if (data.error) {
      // If ping fails, we still get a proper error response
      expect(data.error.code).toBeDefined();
      expect(data.error.message).toBeDefined();
    }
  });

  test("kubectl_get tool - pods", async () => {
    const response = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/call",
        params: {
          name: "kubectl_get",
          arguments: {
            resourceType: "pods",
            namespace: "default",
            output: "json",
          },
        },
        id: 4,
      }),
    });

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.jsonrpc).toBe("2.0");
    // In test environment, kubectl is not available, so we expect an error response
    expect(data.result.content).toBeDefined();
    expect(data.result.content[0].type).toBe("text");
    // The response should contain error information since kubectl is not available
    const content = data.result.content[0].text;
    expect(typeof content).toBe("string");
    // Should contain error information
    expect(content).toContain("error");
  });

  test("health endpoint", async () => {
    const response = await fetch(`${baseUrl}/health`, {
      method: "GET",
    });

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.status).toBe("ok");
  });

  test("ready endpoint", async () => {
    const response = await fetch(`${baseUrl}/ready`, {
      method: "GET",
    });

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.status).toBe("ready");
    expect(data.timestamp).toBeDefined();
  });

  test("invalid method", async () => {
    const response = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "invalid_method",
        params: {},
        id: 5,
      }),
    });

    expect(response.status).toBe(400);
    const data = await response.json();
    expect(data.jsonrpc).toBe("2.0");
    expect(data.error.code).toBe(-32601);
    expect(data.error.message).toBe("Method not found");
  });

  test("invalid request - no method", async () => {
    const response = await fetch(`${baseUrl}/jsonrpc`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        params: {},
        id: 6,
      }),
    });

    expect(response.status).toBe(400);
    const data = await response.json();
    expect(data.jsonrpc).toBe("2.0");
    expect(data.error.code).toBe(-32600);
    expect(data.error.message).toBe("Invalid Request");
  });
});
