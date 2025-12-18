#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  installHelmChart,
  installHelmChartSchema,
  upgradeHelmChart,
  upgradeHelmChartSchema,
  uninstallHelmChart,
  uninstallHelmChartSchema,
} from "./tools/helm-operations.js";



import {
  nodeManagement,
  nodeManagementSchema,
} from "./tools/node-management.js";
import {
  explainResource,
  explainResourceSchema,
  listApiResources,
  listApiResourcesSchema,
} from "./tools/kubectl-operations.js";
import { execInPod, execInPodSchema } from "./tools/exec_in_pod.js";
import { getResourceHandlers } from "./resources/handlers.js";
import {
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ErrorCode,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import { KubernetesManager } from "./types.js";
import { serverConfig } from "./config/server-config.js";
import { cleanupSchema } from "./config/cleanup-config.js";
import { kubectlScale, kubectlScaleSchema } from "./tools/kubectl-scale.js";
import {
  kubectlContext,
  kubectlContextSchema,
} from "./tools/kubectl-context.js";
import { kubectlGet, kubectlGetSchema } from "./tools/kubectl-get.js";
import {
  kubectlDescribe,
  kubectlDescribeSchema,
} from "./tools/kubectl-describe.js";
import { kubectlApply, kubectlApplySchema } from "./tools/kubectl-apply.js";
import { kubectlDelete, kubectlDeleteSchema } from "./tools/kubectl-delete.js";
import { kubectlCreate, kubectlCreateSchema } from "./tools/kubectl-create.js";
import { kubectlLogs, kubectlLogsSchema } from "./tools/kubectl-logs.js";
import {
  kubectlGeneric,
  kubectlGenericSchema,
} from "./tools/kubectl-generic.js";
import { kubectlPatch, kubectlPatchSchema } from "./tools/kubectl-patch.js";
import {
  kubectlRollout,
  kubectlRolloutSchema,
} from "./tools/kubectl-rollout.js";
import { registerPromptHandlers } from "./prompts/index.js";
import { ping, pingSchema } from "./tools/ping.js";
import { startSimpleHTTPJSONRPCServer } from "./utils/http-json-rpc.js";

// Start the server with HTTP JSON-RPC
startSimpleHTTPJSONRPCServer(new Server(
  {
    name: "kubernetes",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
      prompts: {},
    },
  }
)).then(() => {
  console.log("HTTP JSON-RPC server started successfully");
}).catch((error) => {
  console.error("Failed to start HTTP JSON-RPC server:", error);
  process.exit(1);
});
