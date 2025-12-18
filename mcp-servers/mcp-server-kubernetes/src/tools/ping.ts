export const pingSchema = {
  name: "ping",
  description:
    "Verify that the counterpart is still responsive and the connection is alive.",
  inputSchema: {
    type: "object",
    properties: {},
    required: [],
  },
  annotations: {
    readOnlyHint: true,
  },
};

export async function ping() {
  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        status: "ok",
        timestamp: new Date().toISOString()
      })
    }]
  };
}
