// Demo script to test InfraChat functionality
// This can be used to test the app with sample infrastructure queries

const demoQueries = [
  "Give me the URL of the web app and admin login",
  "SSH into redis cluster node 02", 
  "Show me the database configuration",
  "What's the status of the production servers?",
  "Get me the API credentials for the monitoring service"
]

console.log("InfraChat Demo Queries:")
console.log("=======================")
demoQueries.forEach((query, index) => {
  console.log(`${index + 1}. ${query}`)
})

console.log("\nExpected behaviors:")
console.log("- Queries 1 & 3 should trigger bottom pane with key-value data")
console.log("- Query 2 should trigger right pane with terminal command")
console.log("- Query 4 should trigger right pane with logs")
console.log("- Query 5 should trigger bottom pane with credentials")