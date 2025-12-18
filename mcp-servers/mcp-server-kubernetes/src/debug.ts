(async () => {
  try {
    console.log("Starting dynamic import...");
    const k8s = await import("@kubernetes/client-node");
    console.log("Import successful!");
    const kc = new k8s.KubeConfig();
    console.log("KubeConfig object created.");
    kc.loadFromDefault();
    console.log("loadFromDefault successful!");
  } catch (e) {
    console.error("Caught exception:", e);
  }
})();